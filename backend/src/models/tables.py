from sqlalchemy import (JSON, BigInteger, Column, ForeignKey, Integer,
                        MetaData, String, Table, Text)

schema = MetaData()
users = Table('accounts', schema,
    Column('id', Integer, primary_key=True),
    Column('username', String(40), nullable=False, unique=True),
    Column('password_hash', String(200), nullable=False),
    Column('role', String(20), nullable=False))
cases = Table('business_cases', schema,
    Column('id', Integer, primary_key=True),
    Column('slug', String(64), nullable=False, unique=True),
    Column('title', String(120), nullable=False),
    Column('payload', JSON, nullable=False),
    Column('author', String(40), nullable=False),
    Column('created_at', String(32), nullable=False))
runs = Table('business_runs', schema,
    Column('id', Integer, primary_key=True),
    Column('case_id', ForeignKey('business_cases.id'), nullable=False, index=True),
    Column('status', String(20), nullable=False, index=True),
    Column('owner', String(40), nullable=False),
    Column('attempt_token', String(36)),
    Column('started_at', String(32)),
    Column('finished_at', String(32)),
    Column('created_at', String(32), nullable=False),
    Column('error', Text))
evidence = Table('business_evidence', schema,
    Column('id', Integer, primary_key=True),
    Column('run_id', ForeignKey('business_runs.id'), nullable=False, unique=True),
    Column('report', JSON, nullable=False),
    Column('digest', String(64), nullable=False),
    Column('reviewer', String(40)),
    Column('review_note', String(500)),
    Column('reviewed_at', String(32)))
audit = Table('audit_events', schema,
    Column('id', Integer, primary_key=True),
    Column('actor', String(40), nullable=False),
    Column('action', String(32), nullable=False),
    Column('reference', String(50), nullable=False),
    Column('created_at', String(32), nullable=False))
# Singleton row (id = 1): seq is the commit-ordered sync position shared by all
# signed quota orders; cleaned_upto is the retention watermark for pull cursors.
dispatch_state = Table('dispatch_sync_state', schema,
    Column('id', Integer, primary_key=True),
    Column('seq', BigInteger, nullable=False),
    Column('cleaned_upto', BigInteger, nullable=False))
dispatch_orders = Table('dispatch_orders', schema,
    Column('sync_seq', BigInteger, primary_key=True),
    Column('evidence_id', ForeignKey('business_evidence.id'), nullable=False, unique=True),
    Column('run_id', Integer, nullable=False),
    Column('digest', String(64), nullable=False),
    Column('signed_by', String(40), nullable=False),
    Column('signed_at', String(32), nullable=False),
    Column('report', JSON, nullable=False))
