"""Signed quota order sync feed for the cutting group.

Positions come from a singleton counter row updated inside the signing
transaction. The row lock makes concurrent signings commit in position order,
so a reader resuming from `sync_seq > cursor` can never miss a committed
order: seeing position N implies every position below N is already visible.
The same invariant makes rebuild snapshots consistent: all orders with
`sync_seq <= horizon` are committed exactly when the counter reads horizon.
"""

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy.dialects.postgresql import insert as postgres_insert

from src.config.settings import IS_MYSQL, engine
from src.models.tables import audit, dispatch_orders, dispatch_state
from src.utils.time import utc_time

STATE_ID = 1
QUOTA_SECTION = '分级仓位配额单'


def dispatchable(report):
    """Only signed quota orders may reach the cutting group; paused runs may not."""
    sections = report.get('sections') if isinstance(report, dict) else None
    return any(isinstance(section, dict) and section.get('title') == QUOTA_SECTION
               for section in sections or [])


def ensure_state(conn):
    values = {'id': STATE_ID, 'seq': 0, 'cleaned_upto': 0}
    if IS_MYSQL:
        conn.execute(mysql_insert(dispatch_state).values(**values).on_duplicate_key_update(id=STATE_ID))
    else:
        conn.execute(postgres_insert(dispatch_state).values(**values).on_conflict_do_nothing(index_elements=['id']))


def read_state(conn):
    row = conn.execute(select(dispatch_state.c.seq, dispatch_state.c.cleaned_upto)
                       .where(dispatch_state.c.id == STATE_ID)).first()
    return (row.seq, row.cleaned_upto) if row else (0, 0)


def publish(conn, evidence_row, actor, signed_at):
    """Append the order to the feed inside the signing transaction."""
    ensure_state(conn)
    conn.execute(dispatch_state.update().where(dispatch_state.c.id == STATE_ID)
                 .values(seq=dispatch_state.c.seq + 1))
    seq = conn.execute(select(dispatch_state.c.seq).where(dispatch_state.c.id == STATE_ID)).scalar_one()
    conn.execute(dispatch_orders.insert().values(
        sync_seq=seq, evidence_id=evidence_row['id'], run_id=evidence_row['run_id'],
        digest=evidence_row['digest'], signed_by=actor, signed_at=signed_at,
        report=evidence_row['report']))


def _order(row):
    return dict(row)


def pull(cursor, limit):
    with engine.begin() as conn:
        horizon, cleaned_upto = read_state(conn)
        if cursor < cleaned_upto:
            raise HTTPException(410, '同步位置已过期，较早的同步记录已清理，请调用 /dispatch/rebuild 重建全量后从新位置续拉')
        if cursor > horizon:
            raise HTTPException(409, '同步位置超出当前已签发水位，请核对位置来源')
        rows = conn.execute(select(dispatch_orders).where(dispatch_orders.c.sync_seq > cursor)
                            .order_by(dispatch_orders.c.sync_seq).limit(limit)).mappings().all()
        return {'orders': [_order(row) for row in rows],
                'next_cursor': rows[-1]['sync_seq'] if rows else cursor,
                'horizon': horizon}


def rebuild():
    """Full snapshot plus the position to resume from, taken at one point in time."""
    with engine.begin() as conn:
        horizon, _ = read_state(conn)
        rows = conn.execute(select(dispatch_orders).where(dispatch_orders.c.sync_seq <= horizon)
                            .order_by(dispatch_orders.c.sync_seq)).mappings().all()
        return {'cursor': horizon, 'orders': [_order(row) for row in rows]}


def cleanup(upto, actor):
    with engine.begin() as conn:
        ensure_state(conn)
        horizon, cleaned_upto = read_state(conn)
        if upto > horizon:
            raise HTTPException(422, '清理位置不能超过当前已签发水位')
        removed = conn.execute(dispatch_orders.delete()
                               .where(dispatch_orders.c.sync_seq <= upto)).rowcount
        if upto > cleaned_upto:
            conn.execute(dispatch_state.update().where(dispatch_state.c.id == STATE_ID)
                         .values(cleaned_upto=upto))
        conn.execute(audit.insert().values(actor=actor, action='cleanup_dispatch',
                                           reference=f'upto:{upto}', created_at=utc_time()))
        return {'removed': removed, 'cleaned_upto': max(upto, cleaned_upto), 'horizon': horizon}
