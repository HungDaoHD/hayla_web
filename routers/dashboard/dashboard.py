from fastapi import APIRouter, Depends, status, Request, Form, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from routers.auth.oauth2 import require_role
from mvc.users import UserPublic
from mvc.dashboard import Dashboard


lst_role = ['Admin']
router = APIRouter(prefix='/dashboard', tags=['dashboard'], dependencies=[Depends(require_role(role=lst_role))])
router.mount('/static', StaticFiles(directory='static'), name='static')
templates = Jinja2Templates(directory='templates')




@router.get('/index', response_class=HTMLResponse)
async def dashboard(request: Request, current_user: UserPublic = Depends(require_role(role=lst_role))):
    
    # dict_filter = {
    #     'Location': ['SGN', 'NTR'],
    # }
    
    
    # dashboard = Dashboard()
    # dict_dashboard = await dashboard.dashboard_analyze(dict_filter=dict_filter, current_user=current_user)
    
    
    return templates.TemplateResponse('dashboard/index.html', {
        'request': request,
        'user': current_user.model_dump(),
        # 'dict_dashboard': dict_dashboard
    })