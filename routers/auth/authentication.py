from fastapi import APIRouter, Depends, status, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from routers.auth.oauth2 import get_current_user_cookie
from routers.auth.auth_token import AuthToken

from mvc.users import CrudUser, UserInDB, UserPublic


router = APIRouter(tags=['authentication'])
router.mount('/static', StaticFiles(directory='static'), name='static')
templates = Jinja2Templates(directory='templates')




@router.get('/login', response_class=HTMLResponse)
async def login(request: Request, error: str = None):
    return templates.TemplateResponse('pages/login.html', {'request': request, "error": error})



@router.post("/login", response_class=HTMLResponse)
async def login_post(request: Request, email: str = Form(...), password: str = Form(...)):

    crud_user = CrudUser()
    user = await crud_user.authenticate_user(email=email, password=password)


    if not isinstance(user, UserInDB):
        return templates.TemplateResponse(
            "pages/login.html",
            {
                "request": request,
                "error": user[-1],
            },
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    access_token = AuthToken().create_access_token(
        data=crud_user.get_public_user().model_dump(mode='json'),
        expires_minutes=60 * 2
    )

    response = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    response.delete_cookie(key="access_token")
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=True,  # set to True under HTTPS
        # samesite="lax",
        max_age=60 * 60 * 2,
    )

    return response




@router.get("/logout", response_class=RedirectResponse)
async def logout(current_user: UserPublic = Depends(get_current_user_cookie)):
    response = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    response.delete_cookie(key='access_token')
    return response


