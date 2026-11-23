from sqlalchemy import func, select
from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy.dialects.postgresql import insert as postgres_insert

from src.config.settings import IS_MYSQL, engine
from src.constants.workflow import Role
from src.models.tables import audit, cases, evidence, runs, schema, users
from src.services.domain import SPEC
from src.services.security import hash_password
from src.utils.time import utc_time


def keep_existing(conn, table, key, values):
    if IS_MYSQL:
        statement = mysql_insert(table).values(**values).on_duplicate_key_update(id=table.c.id)
    else:
        statement = postgres_insert(table).values(**values).on_conflict_do_nothing(index_elements=[key])
    conn.execute(statement)


def seed():
    with engine.begin() as conn:
        for role in Role:
            keep_existing(conn, users, 'username', {'username': role.value, 'role': role.value,
                'password_hash': hash_password('Demo-Walkthrough-2026')})
        keep_existing(conn, cases, 'slug', {'slug': 'demo', 'title': SPEC['name'],
            'payload': SPEC['sample'], 'author': 'demo', 'created_at': utc_time()})
        return {table.name: conn.execute(select(func.count()).select_from(table)).scalar_one()
                for table in (users, cases, runs, evidence, audit)}


if __name__ == '__main__':
    schema.create_all(engine)
    print(seed())
