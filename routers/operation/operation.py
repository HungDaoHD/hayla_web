from fastapi import APIRouter, Depends, status, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from routers.auth.oauth2 import require_role
from mvc.users import CrudUser, UserPublic
from mvc.operation import Operation


lst_role = ['Admin', 'Staff']
router = APIRouter(prefix='/operation', tags=['operation'], dependencies=[Depends(require_role(role=lst_role))])
router.mount('/static', StaticFiles(directory='static'), name='static')
templates = Jinja2Templates(directory='templates')



@router.get('/raw_ingredient', response_class=HTMLResponse)
async def retrieve_raw_ingredient(request: Request, current_user: UserPublic = Depends(require_role(role=lst_role))):

    opt = Operation()

    lst_raw_ingredient = await opt.retrieve_raw_ingredient()


    return templates.TemplateResponse('operation/raw_ingredient.html', {
        'request': request,
        'user': current_user.model_dump(),
        'lst_raw_ingredient': lst_raw_ingredient
    })


@router.get('/processed_ingredient', response_class=HTMLResponse)
async def retrieve_processed_ingredient(request: Request, current_user: UserPublic = Depends(require_role(role=lst_role))):

    opt = Operation()

    lst_processed_ingredient = await opt.retrieve_processed_ingredient()


    return templates.TemplateResponse('operation/processed_ingredient.html', {
        'request': request,
        'user': current_user.model_dump(),
        'lst_processed_ingredient': lst_processed_ingredient
    })




# @router.post('/user/{user_id}/toggle_status', response_class=JSONResponse)
# async def toggle_status(user_id: str, payload: UserUpdate, current_user: UserPublic = Depends(require_admin)):
#
#     is_active = True if not payload.active else False
#     payload.active = is_active
#
#     updated_user: UserPublic = await CrudUser().update_user(user_id=user_id, payload=payload)
#
#     return JSONResponse(content=updated_user.model_dump())
#
#
#
#
# @router.get('/users/me')
# async def read_users_me(current_user: UserPublic = Depends(require_admin)):
#     return current_user





