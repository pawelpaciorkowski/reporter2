import traceback
from typing import Optional
from fastapi import FastAPI, Query, Depends, HTTPException, status
import jwt
from fastapi.security import OAuth2, OpenIdConnect, HTTPBearer  # TODO podklasę zrobić do weryfikiacji w aas
from fastapi.security.http import HTTPAuthorizationCredentials
from .common import ApiAccessTokenData

_HTTP_BEARER = HTTPBearer(auto_error=False)
JWT_PUBLIC_KEY = None
DEBUG = False


# KNALSOK

class FastAPI_ApiAccessToken:
    @classmethod
    def set_jwt_public_key(cls, public_key: str):
        global JWT_PUBLIC_KEY
        JWT_PUBLIC_KEY = public_key

    @classmethod
    def set_debug(cls, debug=True):
        global DEBUG
        DEBUG = debug

    def __init__(self, public_key: Optional[str] = None, check_endpoint: Optional[str] = None):
        self.public_key = public_key
        if self.public_key is None:
            self.public_key = JWT_PUBLIC_KEY
        if self.public_key is None:
            raise RuntimeError("JWT public key not set")
        self.check_endpoint = check_endpoint

    async def __call__(self,
                       credentials: Optional[HTTPAuthorizationCredentials] = Depends(_HTTP_BEARER)
                       ) -> ApiAccessTokenData:
        def raise_error(msg):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials: %s" % msg,
                headers={"WWW-Authenticate": "Bearer"},
            )

        if credentials is None:
            raise_error("no authorization header")
        try:
            token = jwt.decode(credentials.credentials, key=self.public_key, algorithms='RS256')
        except Exception as e:
            if DEBUG:
                traceback.print_exc()
            raise_error("invalid token")
        res = ApiAccessTokenData(
            sub=token['sub'],
            endpoints=token.get('endpoints') or [],
            settings=token.get('settings') or {}
        )
        if self.check_endpoint is not None:
            endpoint = self.check_endpoint
            if not endpoint.startswith('/'):
                endpoint = '/' + endpoint
            available_endpoints = res.endpoints or []
            if endpoint not in available_endpoints and '*' not in available_endpoints:
                raise_error("no access to this endpoint")
        return res
