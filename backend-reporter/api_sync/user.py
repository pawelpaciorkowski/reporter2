import traceback
from config import Config
from dataclasses import dataclass
from typing import Optional, List, Dict, Any, Tuple
from fastapi import FastAPI, Query, Depends, HTTPException, status
import jwt
from fastapi.security import OAuth2, OpenIdConnect, HTTPBearer
from fastapi.security.http import HTTPAuthorizationCredentials

_HTTP_BEARER = HTTPBearer(auto_error=False)
JWT_PUBLIC_KEY = None
DEBUG = True


@dataclass(frozen=True)
class ReporterUserTokenData:
    sub: str
    user: int
    rights: List[Tuple[str, Optional[str]]]


class FastAPI_ReporterUserToken:
    def __init__(self):
        self.secret_key = Config.SECRET_KEY

    async def __call__(self,
                       credentials: Optional[HTTPAuthorizationCredentials] = Depends(_HTTP_BEARER)
                       ) -> ReporterUserTokenData:
        def raise_error(msg):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials: %s" % msg,
                headers={"WWW-Authenticate": "Bearer"},
            )
        if credentials is None:
            raise_error("no authorization header")
        try:
            token = jwt.decode(credentials.credentials, key=self.secret_key, algorithms=['HS512'])
        except Exception as e:
            if DEBUG:
                traceback.print_exc()
            raise_error("invalid token")
        rights = []
        for right in token['rights'].split(';'):
            if ':' in right:
                rights.append(right.split(':'))
            else:
                rights.append([right, None])
        res = ReporterUserTokenData(
            sub=token['sub'],
            user=token['user'],
            rights=rights
        )
        return res
