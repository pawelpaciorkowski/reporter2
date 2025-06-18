from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from fastapi.middleware.cors import CORSMiddleware
import config
from plugins import PluginManager
from api_access_server.fastapi_helper import FastAPI_ApiAccessToken

cfg = config.Config()
FastAPI_ApiAccessToken.set_jwt_public_key(cfg.API_ACCESS_SERVER_PUBLIC_KEY)

if cfg.SENTRY_URL is not None:
    import sentry_sdk

    sentry_sdk.init(cfg.SENTRY_URL)

from api_sync.report import router as report_router
from api_sync.search import router as search_router


def custom_generate_unique_id(route: APIRoute):
    return f"{route.tags[0]}-{route.name}"  # TODO: rozkminić co zrobić jak będzie get i post


def create_app():
    app = FastAPI(
        title="Alab Reporter sync API",
        generate_unique_id_function=custom_generate_unique_id
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000"
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(report_router, prefix='/report', tags=['report'])
    app.include_router(search_router, prefix='/search', tags=['search'])
    return app


app = create_app()
