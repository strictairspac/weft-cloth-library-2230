from starlette.responses import Response

from src.config.settings import engine
from src.models.tables import evidence
from src.services.workflow import found
from src.utils.encoding import canonical


def download(identity):
    with engine.connect() as conn:
        data = found(conn, evidence, identity)
    return Response(canonical(data), media_type='application/json', headers={
        'Content-Disposition': f'attachment; filename="evidence-{identity}.json"'})
