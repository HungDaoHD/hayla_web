from fastapi import APIRouter, Depends, status, Request, Form, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from routers.auth.oauth2 import require_role
from mvc.users import UserPublic
from mvc.reservation import Reservation

from datetime import datetime
import json


lst_role = ['Admin', 'Staff']
router = APIRouter(prefix='/calendar', tags=['calendar'], dependencies=[Depends(require_role(role=lst_role))])
router.mount('/static', StaticFiles(directory='static'), name='static')
templates = Jinja2Templates(directory='templates')



@router.get('/reservation', response_class=HTMLResponse)
async def retrieve_reservation(request: Request, current_user: UserPublic = Depends(require_role(role=lst_role))):
    
    res = Reservation()
    lst_reservation = await res.retrieve_reservation(current_user, json_dumps=True)
    
    
    return templates.TemplateResponse('calendar/reservation.html', {
        'request': request,
        'user': current_user.model_dump(),
        'lst_reservation': lst_reservation,
    })
    

