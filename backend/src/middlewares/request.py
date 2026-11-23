import uuid

from fastapi import Request
from starlette.responses import JSONResponse


async def request_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers['X-Request-Id'] = uuid.uuid4().hex
    response.headers['X-Content-Type-Options'] = 'nosniff'
    return response


async def limit_body(request: Request, call_next):
    size = request.headers.get('content-length')
    if size and (not size.isdecimal() or int(size) > 768 * 1024):
        return JSONResponse({'detail': '请求超过 768 KiB'}, status_code=413)
    return await call_next(request)
