from .common import ApiAccessTokenData
try:
    from .fastapi_helper import FastAPI_ApiAccessToken
except ImportError as e:
    def FastAPI_ApiAccessToken(*args, **kwargs):
        raise RuntimeError("No requirements found for FastAPI_ApiAccessToken: %s" % str(e))
