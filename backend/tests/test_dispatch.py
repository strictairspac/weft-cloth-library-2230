"""Sync feed contract tests against a real PostgreSQL 16 instance.

Run from the backend directory:
    python -m pytest tests/test_dispatch.py -q
Requires PostgreSQL reachable at 127.0.0.1:17800 (user app, trust auth) with a
maintenance database named `workflow`; the suite creates and drops
`workflow_test` itself.
"""

import hashlib
import os
import threading
import time
from uuid import uuid4

os.environ.setdefault('AUTH_KEY', 'test-auth-key')
os.environ['DB_HOST'] = '127.0.0.1'
os.environ['DB_PORT'] = '17800'
os.environ['DB_NAME'] = 'workflow_test'
os.environ['DB_PASSWORD'] = 'test'
os.environ['SEED_DEMO'] = 'false'

import psycopg
import pytest
from fastapi import HTTPException

from src.config.settings import engine
from src.models.tables import (audit, cases, dispatch_orders, dispatch_state,
                               evidence, runs, schema, users)
from src.services import dispatch, workflow
from src.services.security import hash_password
from src.utils.encoding import canonical
from src.utils.time import utc_time

PASSWORD = 'Test-Pass-2026'
ISSUABLE = {
    'summary': '库存全量对账一致，建议转裁 1 批。',
    'metrics': {'建议转裁批次数': 1},
    'sections': [
        {'title': '分级仓位配额单', 'rows': [{'等级': 'A级', '判定': '建议整批转入裁切区'}]},
        {'title': '建议转裁批次', 'rows': [{'批次': 'BL-102', '修订号': 1}]},
    ],
}
PAUSED = {
    'summary': '1 个等级库存存在差异，暂停本次仓位与转裁发单。',
    'metrics': {'库存差异等级数': 1},
    'sections': [{'title': 'PostgreSQL 全量对账', 'rows': []}],
}


@pytest.fixture(scope='session', autouse=True)
def test_database():
    admin = psycopg.connect(host='127.0.0.1', port=17800, user='app',
                            dbname='workflow', autocommit=True)
    admin.execute('DROP DATABASE IF EXISTS workflow_test WITH (FORCE)')
    admin.execute('CREATE DATABASE workflow_test')
    admin.close()
    yield
    admin = psycopg.connect(host='127.0.0.1', port=17800, user='app',
                            dbname='workflow', autocommit=True)
    admin.execute('DROP DATABASE IF EXISTS workflow_test WITH (FORCE)')
    admin.close()


@pytest.fixture(autouse=True)
def clean_tables(test_database):
    schema.create_all(engine)
    with engine.begin() as conn:
        for table in (dispatch_orders, dispatch_state, audit, evidence, runs, cases, users):
            conn.execute(table.delete())


@pytest.fixture
def client():
    from src.main import app
    from fastapi.testclient import TestClient
    with TestClient(app) as test_client:
        yield test_client


def make_users():
    with engine.begin() as conn:
        for role in ('operator', 'reviewer', 'viewer'):
            conn.execute(users.insert().values(username=role, role=role,
                                               password_hash=hash_password(PASSWORD)))


def auth(client, username):
    token = client.post('/login', json={'username': username, 'password': PASSWORD}).json()['token']
    return {'Authorization': f'Bearer {token}'}


def make_evidence(report=None):
    report = report or ISSUABLE
    digest = hashlib.sha256(canonical(report)).hexdigest()
    with engine.begin() as conn:
        case_id = conn.execute(cases.insert().values(
            slug=uuid4().hex, title='配额单档案', payload={}, author='operator',
            created_at=utc_time())).inserted_primary_key[0]
        run_id = conn.execute(runs.insert().values(
            case_id=case_id, status='complete', owner='operator',
            created_at=utc_time())).inserted_primary_key[0]
        return conn.execute(evidence.insert().values(
            run_id=run_id, report=report, digest=digest)).inserted_primary_key[0]


def drain(cursor=0, limit=2):
    """Pull every page from cursor; return the flattened order list."""
    orders = []
    while True:
        page = dispatch.pull(cursor, limit)
        orders.extend(page['orders'])
        if page['next_cursor'] == cursor:
            return orders
        cursor = page['next_cursor']


def test_sign_publishes_issuable_order():
    identity = make_evidence()
    workflow.review(identity, '同意发单', 'reviewer')
    page = dispatch.pull(0, 10)
    assert page['horizon'] == 1 and page['next_cursor'] == 1
    (order,) = page['orders']
    assert order['sync_seq'] == 1 and order['evidence_id'] == identity
    assert order['signed_by'] == 'reviewer' and order['report'] == ISSUABLE
    assert order['digest'] == hashlib.sha256(canonical(ISSUABLE)).hexdigest()
    with engine.connect() as conn:
        row = conn.execute(evidence.select().where(evidence.c.id == identity)).mappings().one()
    assert row['reviewed_at'] == order['signed_at']


def test_paused_report_not_published():
    identity = make_evidence(PAUSED)
    workflow.review(identity, '同意', 'reviewer')
    page = dispatch.pull(0, 10)
    assert page['orders'] == [] and page['horizon'] == 0
    with engine.connect() as conn:
        row = conn.execute(evidence.select().where(evidence.c.id == identity)).mappings().one()
    assert row['reviewed_at'] is not None


def test_sign_retry_never_duplicates():
    identity = make_evidence()
    workflow.review(identity, '同意', 'reviewer')
    with pytest.raises(HTTPException) as failure:
        workflow.review(identity, '重试重复签署', 'reviewer')
    assert failure.value.status_code == 409
    assert len(drain()) == 1
    assert len(dispatch.rebuild()['orders']) == 1


def test_sign_and_publish_roll_back_together(monkeypatch):
    identity = make_evidence()

    def crash(*args):
        raise RuntimeError('数据库写入异常')

    monkeypatch.setattr(dispatch, 'publish', crash)
    with pytest.raises(RuntimeError):
        workflow.review(identity, '同意', 'reviewer')
    with engine.connect() as conn:
        row = conn.execute(evidence.select().where(evidence.c.id == identity)).mappings().one()
    assert row['reviewed_at'] is None
    assert dispatch.pull(0, 10)['orders'] == []


def test_concurrent_signing_pull_misses_nothing():
    identities = [make_evidence() for _ in range(12)]
    barrier = threading.Barrier(len(identities))
    failures = []

    def sign(target):
        try:
            barrier.wait(timeout=15)
            workflow.review(target, '同意', 'reviewer')
        except Exception as exc:  # noqa: BLE001 - collected and asserted below
            failures.append(exc)

    threads = [threading.Thread(target=sign, args=(identity,)) for identity in identities]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert failures == []
    orders = drain(limit=3)
    assert [order['sync_seq'] for order in orders] == list(range(1, len(identities) + 1))
    assert sorted(order['evidence_id'] for order in orders) == sorted(identities)


def test_pull_interleaved_with_signing_loses_nothing():
    identities = [make_evidence() for _ in range(6)]
    workflow.review(identities[0], '同意', 'reviewer')
    cursor = dispatch.pull(0, 10)['next_cursor']
    for identity in identities[1:]:
        workflow.review(identity, '同意', 'reviewer')
    rest = drain(cursor=cursor, limit=2)
    assert sorted(order['evidence_id'] for order in rest) == sorted(identities[1:])


def test_rebuild_snapshot_and_resume_share_one_point_in_time():
    identities = [make_evidence() for _ in range(5)]
    for identity in identities[:3]:
        workflow.review(identity, '同意', 'reviewer')
    snapshot = dispatch.rebuild()
    assert snapshot['cursor'] == 3
    assert [order['sync_seq'] for order in snapshot['orders']] == [1, 2, 3]
    # Signing continues while the cutting group rebuilds.
    for identity in identities[3:]:
        workflow.review(identity, '同意', 'reviewer')
    resumed = dispatch.pull(snapshot['cursor'], 10)
    assert [order['evidence_id'] for order in resumed['orders']] == identities[3:]
    assert resumed['next_cursor'] == 5


def test_rebuild_stays_consistent_under_concurrent_signing():
    identities = [make_evidence() for _ in range(20)]
    done = threading.Event()

    def signer():
        for identity in identities:
            workflow.review(identity, '同意', 'reviewer')
            time.sleep(0.001)
        done.set()

    thread = threading.Thread(target=signer)
    thread.start()
    while not done.is_set():
        snapshot = dispatch.rebuild()
        seqs = [order['sync_seq'] for order in snapshot['orders']]
        assert seqs == list(range(1, snapshot['cursor'] + 1))
    thread.join()


def test_cleanup_expires_old_positions():
    identities = [make_evidence() for _ in range(5)]
    for identity in identities:
        workflow.review(identity, '同意', 'reviewer')
    result = dispatch.cleanup(3, 'reviewer')
    assert result == {'removed': 3, 'cleaned_upto': 3, 'horizon': 5}
    with pytest.raises(HTTPException) as failure:
        dispatch.pull(2, 10)
    assert failure.value.status_code == 410
    page = dispatch.pull(3, 10)
    assert [order['sync_seq'] for order in page['orders']] == [4, 5]
    snapshot = dispatch.rebuild()
    assert snapshot['cursor'] == 5
    assert [order['sync_seq'] for order in snapshot['orders']] == [4, 5]


def test_cleanup_beyond_horizon_rejected():
    identity = make_evidence()
    workflow.review(identity, '同意', 'reviewer')
    with pytest.raises(HTTPException) as failure:
        dispatch.cleanup(9, 'reviewer')
    assert failure.value.status_code == 422
    assert len(drain()) == 1


def test_cursor_beyond_horizon_rejected():
    with pytest.raises(HTTPException) as failure:
        dispatch.pull(7, 10)
    assert failure.value.status_code == 409


def test_api_pull_paginates_for_cutting_group(client):
    make_users()
    for _ in range(3):
        workflow.review(make_evidence(), '同意', 'reviewer')
    assert client.get('/dispatch/pull').status_code == 401
    headers = auth(client, 'viewer')
    first = client.get('/dispatch/pull', params={'limit': 2}, headers=headers).json()
    assert [order['sync_seq'] for order in first['orders']] == [1, 2]
    assert first['next_cursor'] == 2 and first['horizon'] == 3
    rest = client.get('/dispatch/pull', params={'cursor': first['next_cursor']}, headers=headers).json()
    assert [order['sync_seq'] for order in rest['orders']] == [3]
    assert rest['next_cursor'] == 3


def test_api_reports_expired_cursor_and_rebuilds(client):
    make_users()
    for _ in range(4):
        workflow.review(make_evidence(), '同意', 'reviewer')
    reviewer = auth(client, 'reviewer')
    assert client.post('/dispatch/cleanup', json={'upto': 2}, headers=reviewer).status_code == 200
    viewer = auth(client, 'viewer')
    expired = client.get('/dispatch/pull', params={'cursor': 1}, headers=viewer)
    assert expired.status_code == 410
    assert '重建' in expired.json()['detail']
    snapshot = client.get('/dispatch/rebuild', headers=viewer).json()
    assert snapshot['cursor'] == 4
    assert [order['sync_seq'] for order in snapshot['orders']] == [3, 4]


def test_api_cleanup_requires_reviewer(client):
    make_users()
    workflow.review(make_evidence(), '同意', 'reviewer')
    for role in ('operator', 'viewer'):
        response = client.post('/dispatch/cleanup', json={'upto': 1}, headers=auth(client, role))
        assert response.status_code == 403
    response = client.post('/dispatch/cleanup', json={'upto': 1}, headers=auth(client, 'reviewer'))
    assert response.status_code == 200
    assert response.json()['removed'] == 1
