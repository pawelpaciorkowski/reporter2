import datetime
import asyncio
import inspect
import json
from typing import Any, Optional, List, Dict, Tuple
from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from pydantic import BaseModel

from api.common import get_db
from plugins import PluginManager
from api_sync.user import ReporterUserTokenData, FastAPI_ReporterUserToken
from .report_search import search_in_menu, recent_reports
from .podmiot_search import search_pl, search_zl, search_pp, search_lab, search_bad
from .rpwdl_search import search_pm

router = APIRouter()


class SearchRequest(BaseModel):
    query: str


class SearchResult(BaseModel):
    title: str
    helper: Optional[str]
    url: str


class SearchBeaconRequest(BaseModel):
    query: str
    result: Optional[SearchResult]
    result_idx: Optional[int]


SEARCHERS = {
    'pl': {
        'title': 'płatnicy', 'instrumental': 'płatnikach',
        'fn': search_pl,
    },
    'zl': {
        'title': 'zleceniodawcy', 'instrumental': 'zleceniodawcach',
        'fn': search_zl,
    },
    'lab': {
        'title': 'laboratoria', 'instrumental': 'laboratoriach',
        'fn': search_lab,
    },
    'pp': {
        'title': 'punkt pobrań', 'instrumental': 'punktach pobrań',
        'fn': search_pp,
    },
    'bad': {
        'title': 'badania i pakiety', 'instrumental': 'badaniach i pakietach',
        'fn': search_bad,
    },
    'pm': {
        'title': 'podmioty medyczne', 'instrumental': 'podmiotach medycznych',
        'fn': search_pm,
    },
}


@router.post('/')
async def search(
        request: SearchRequest,
        api_access_token: ReporterUserTokenData = Depends(FastAPI_ReporterUserToken())
):
    query = request.query
    results = []

    status = 'ok'
    searching = False
    prefixes = None
    msg = 'Szukaj raportu lub wprowadź prefiks aby szukać gdzie indziej'


    if len(query.strip()) == 0:
        results = recent_reports(api_access_token.sub, api_access_token.rights)
        # domyślne raporty
    else:
        pref_cand = query.strip().split(' ')[0]
        if pref_cand in SEARCHERS:
            searcher = SEARCHERS[pref_cand]
            msg = 'Szukam w %s' % searcher['instrumental']
            subquery = query[len(pref_cand) + 1:].strip()
            if len(subquery) > 2:
                searching = True
                try:
                    results = await SEARCHERS[pref_cand]['fn'](subquery)
                except Exception as e:
                    status = 'error'
                    msg = str(e)
                    # TODO: sentry

        elif len(query.strip()) > 2:
            msg = 'Szukam w raportach'
            searching = True
            results = search_in_menu(api_access_token.sub, api_access_token.rights, query.strip())

    if not searching:
        prefixes = [(p, op['title']) for p, op in SEARCHERS.items()]
    elif len(results) == 0:
        status = 'warning'
        msg += ' - nic nie znaleziono'

    return {
        'results': results,
        'msg': msg,
        'status': status,
        'prefixes': prefixes
    }


@router.post('/beacon')
async def post_search_beacon(
        request: SearchBeaconRequest,
        api_access_token: ReporterUserTokenData = Depends(FastAPI_ReporterUserToken())
):
    with get_db() as rep_db:
        rep_db.execute("""
            insert into log_search(ts, login, query, result)
            values('NOW', %s, %s, %s)
        """, [
            api_access_token.sub, request.query, json.dumps({
                'result': request.result.dict(), 'result_idx': request.result_idx
            })
        ])

