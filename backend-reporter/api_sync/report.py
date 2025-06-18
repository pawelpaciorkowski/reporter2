import datetime
import asyncio
import inspect
from typing import Any, Optional, List, Dict, Tuple
from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from pydantic import BaseModel
from plugins import PluginManager
from api_access_server import ApiAccessTokenData, FastAPI_ApiAccessToken
from raporty.common import generic_start_report, get_report_result
from tasks import TaskGroup

router = APIRouter()


class GenerateReportRequest(BaseModel):
    plugin: str
    params: Dict[str, Any]
    format: Optional[str]


def error(msg, code=400):
    return JSONResponse(status_code=code, content={
        'status': 'error',
        'message': msg,
    })


def ok(resp):
    return JSONResponse(status_code=200, content=resp)


@router.post('/generate')
async def generate_report(
        request: GenerateReportRequest,
        api_access_token: ApiAccessTokenData = Depends(FastAPI_ApiAccessToken())
    ):
    pm = PluginManager(lazy=True)
    try:
        plugin = pm.find_plugin_by_path(request.plugin)
    except:
        return error('Brak plugina o podanej ścieżce')
    if api_access_token.settings is None:
        return error("Brak settings w tokenie")
    if 'user_rights' not in api_access_token.settings:
        return error("Brak user_rights w settings w tokenie")
    has_access = False
    for perm_name, perm_range in api_access_token.settings['user_rights']:
        if pm.can_access(perm_name, plugin.__PLUGIN__):
            has_access = True
            break
    if not has_access:
        return error("Brak uprawnień", code=401)
    params = request.params
    if hasattr(plugin, 'start_report'):
        start_report_fn = plugin.start_report
        fn_params = []
        for arg in inspect.getargs(start_report_fn.__code__).args:
            if arg == 'params':
                fn_params.append(params)
            # TODO: poniższe ogarnąć jak będziemy mieli uprawnienia
            # elif arg == 'user_login':
            #     fn_params.append(user_login)
            # elif arg == 'user_permissions':
            #     fn_params.append(user_permissions)
            # elif arg == 'user_labs_available':
            #     fn_params.append(user_labs_available)
            else:
                fn_params.append(None)
    else:
        start_report_fn = generic_start_report
        fn_params = [plugin, params]
    task_group = start_report_fn(*fn_params)
    task_group.log_event(-1, 'REPGEN')
    for check_round in range(200):
        delay = min(check_round, 30)
        await asyncio.sleep(delay)
        result = get_report_result(plugin, task_group.ident)
        if result.get('progress', 0) == 1:
            task_group.log_event(-1, 'REPVIEW')
            if 'actions' in result:
                result['actions'] = result['actions'].get_augmented_actions()
            return ok(result)
    return error('timeout')
