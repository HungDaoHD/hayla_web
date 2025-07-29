from fastapi import APIRouter, Depends, status, Request, Form, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from routers.auth.oauth2 import require_role
from mvc.users import UserPublic
from mvc.dashboard import Dashboard, DashboardFilterInput


lst_role = ['Admin']
router = APIRouter(prefix='/dashboard', tags=['dashboard'], dependencies=[Depends(require_role(role=lst_role))])
router.mount('/static', StaticFiles(directory='static'), name='static')
templates = Jinja2Templates(directory='templates')




@router.get('/index', response_class=HTMLResponse)
async def dashboard(request: Request, current_user: UserPublic = Depends(require_role(role=lst_role))):
    
    return templates.TemplateResponse('dashboard/index.html', {
        'request': request,
        'user': current_user.model_dump(),
        # 'dict_dashboard': dict_dashboard
    })
    


@router.post('/filter', response_class=JSONResponse)
async def dashboard_filter(dboard_filter_input: DashboardFilterInput, current_user: UserPublic = Depends(require_role(role=lst_role))):

    dashboard = Dashboard()
    obj_dashboard_analyze = await dashboard.dashboard_analyze(dboard_filter_input=dboard_filter_input, current_user=current_user)
    
    return JSONResponse(content=obj_dashboard_analyze.model_dump())