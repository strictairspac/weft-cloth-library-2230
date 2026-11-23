import os
from sqlalchemy import URL, create_engine
from redis import Redis

DRIVER = os.getenv('DB_DRIVER', 'postgresql+psycopg')
IS_MYSQL = DRIVER.startswith('mysql')
URL = URL.create(DRIVER, username=os.getenv('DB_USER', 'app'),
                 password=os.getenv('DB_PASSWORD', 'local-db-demo'),
                 host=os.getenv('DB_HOST', 'db'), database=os.getenv('DB_NAME', 'workflow'),
                 query={'charset': 'utf8mb4'} if IS_MYSQL else {})
engine = create_engine(URL, pool_pre_ping=True)
cache = Redis.from_url(os.getenv('REDIS_URL', 'redis://redis:6379/0'), socket_timeout=3)
AUTH_KEY = os.environ['AUTH_KEY']
ARTIFACTS = os.getenv('ARTIFACTS_DIR', '/work')
