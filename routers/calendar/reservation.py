from fastapi import APIRouter, Depends, status, Request, Form, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from routers.auth.oauth2 import require_role
from mvc.users import UserPublic

from datetime import datetime
import json


lst_role = ['Admin', 'Staff']
router = APIRouter(prefix='/calendar', tags=['calendar'], dependencies=[Depends(require_role(role=lst_role))])
router.mount('/static', StaticFiles(directory='static'), name='static')
templates = Jinja2Templates(directory='templates')



@router.get('/reservation', response_class=HTMLResponse)
async def retrieve_reservation(request: Request, current_user: UserPublic = Depends(require_role(role=lst_role))):
    
    y = 2025
    m = 10
    
        
    events = [
        {
            'title': 'Hung',
            'start': datetime(year=y, month=m, day=14, hour=11, minute=30).isoformat(),
            'end': datetime(year=y, month=m, day=14, hour=18, minute=30).isoformat(),
            'allDay': False,
            'description': 'aaaa bbb cccc',
            'venue': 'sgn',
            'className': 'event-warning'
        },
        {
            'title': 'Hung v2',
            'start': datetime(year=y, month=m, day=14, hour=11, minute=0).isoformat(),
            'end': datetime(year=y, month=m, day=14, hour=19, minute=0).isoformat(),
            'allDay': False,
            'description': 'ddd eee fff',
            'venue': 'sgn',
            'className': 'event-warning'
        },
        {
            'title': 'Hung v3',
            'start': datetime(year=y, month=m, day=14, hour=15, minute=0).isoformat(),
            'end': datetime(year=y, month=m, day=14, hour=20, minute=0).isoformat(),
            'allDay': False,
            'description': 'gggg hhhh iii',
            'venue': 'sgn',
            'className': 'event-warning'
        },
        {
            'title': 'Hung v4',
            'start': datetime(year=y, month=m, day=14, hour=14, minute=0).isoformat(),
            'end': datetime(year=y, month=m, day=14, hour=21, minute=0).isoformat(),
            'allDay': False,
            'description': 'gggg hhhh iii',
            'venue': 'sgn',
            'className': 'event-warning'
        },
        {
            'title': 'All Day Event',
            'start': datetime(year=y, month=m, day=15).isoformat(),
            'allDay': True,
            'description': 'This is simply dummy text.',
            'venue': 'City Town',
            'className': 'event-warning'
        },
    ]
    
    
    return templates.TemplateResponse('calendar/reservation.html', {
        'request': request,
        'user': current_user.model_dump(),
        'json_data': json.dumps({'events': events}),
    })


