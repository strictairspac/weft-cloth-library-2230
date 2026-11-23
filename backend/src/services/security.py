import hashlib
import hmac
import secrets
import time

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select

from src.config.settings import AUTH_KEY, engine
from src.constants.workflow import Role
from src.models.tables import users

bearer = OAuth2PasswordBearer(tokenUrl='login')


def hash_password(password, salt=None):
    salt = salt or secrets.token_bytes(16)
    derived = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 200_000)
    return f'{salt.hex()}:{derived.hex()}'


def login(username, password):
    with engine.connect() as conn:
        user = conn.execute(select(users).where(users.c.username == username)).mappings().first()
    expected = user['password_hash'] if user else '0' * 32 + ':' + '0' * 64
    valid = hmac.compare_digest(expected, hash_password(password, bytes.fromhex(expected.split(':')[0])))
    if not user or not valid:
        raise HTTPException(401, '账号或密码有误')
    claims = {'sub': user['username'], 'role': user['role'], 'exp': int(time.time()) + 3600 * 8}
    return {'token': jwt.encode(claims, AUTH_KEY, algorithm='HS256'),
            'username': user['username'], 'role': user['role']}


def current_user(token: str = Depends(bearer)):
    try:
        return jwt.decode(token, AUTH_KEY, algorithms=['HS256'], options={'require': ['sub', 'role', 'exp']})
    except jwt.InvalidTokenError:
        raise HTTPException(401, '登录已失效，请重新登录') from None


def operator(user=Depends(current_user)):
    if user['role'] != Role.OPERATOR:
        raise HTTPException(403, '需要经办员权限')
    return user['sub']


def reviewer(user=Depends(current_user)):
    if user['role'] != Role.REVIEWER:
        raise HTTPException(403, '需要复核员权限')
    return user['sub']
