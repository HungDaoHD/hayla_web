from fastapi import APIRouter, Depends, status, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from routers.auth.oauth2 import require_role

from mvc.users import CrudUser, UserInDB, UserPublic, UserUpdate


router = APIRouter(prefix='/administration', tags=['administration'], dependencies=[Depends(require_role(role=['Admin']))])
router.mount('/static', StaticFiles(directory='static'), name='static')
templates = Jinja2Templates(directory='templates')




@router.get('/users', response_class=HTMLResponse)
async def retrieve_normal_users(request: Request, current_user: UserPublic = Depends(require_role(role=['Admin']))):

    lst_normal_user = await CrudUser().retrieve_normal_users()

    return templates.TemplateResponse('administration/users.html', {
        'request': request,
        'user': current_user.model_dump(mode='json'),
        'normal_users': lst_normal_user,
    })



@router.post('/user/{user_id}/toggle_status', response_class=JSONResponse)
async def toggle_status(user_id: str, payload: UserUpdate, current_user: UserPublic = Depends(require_role(role=['Admin']))):

    is_active = True if not payload.active else False
    payload.active = is_active

    updated_user: UserPublic = await CrudUser().update_user(user_id=user_id, payload=payload)

    return JSONResponse(content=updated_user.model_dump(mode='json'))




# @router.get('/users/me')
# async def read_users_me(current_user: UserPublic = Depends(require_role(role=['Admin']))):
#     return current_user





