from fastapi import APIRouter, Depends, status, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from routers.Auth.oauth2 import get_current_user_cookie
from routers.Auth.auth_token import AuthToken

from mvc.user import CrudUser, UserPublic


router = APIRouter(tags=['authentication'])
router.mount('/static', StaticFiles(directory='static'), name='static')
templates = Jinja2Templates(directory='templates')




@router.get('/login', response_class=HTMLResponse)
async def login(request: Request):
    return templates.TemplateResponse('pages/login.html', {'request': request, "error": None})




@router.post("/login", response_class=HTMLResponse)
async def login_post(request: Request, email: str = Form(...), password: str = Form(...)):

    crud_user = CrudUser()
    await crud_user.authenticate_user(email=email, password=password)
    user = crud_user.user

    if not user:
        return templates.TemplateResponse(
            "pages/login.html",
            {
                "request": request,
                "error": "Incorrect username or password",
            },
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    access_token = AuthToken().create_access_token(
        data=crud_user.get_public_user().model_dump(),
        expires_minutes=5
    )

    response = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    response.delete_cookie(key="access_token")
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=True,  # set to True under HTTPS
        # samesite="lax",
        max_age=60 * 30,
    )
    return response



@router.get("/user/me")
async def read_users_me(current_user: UserPublic = Depends(get_current_user_cookie)):
    return current_user



@router.get("/logout", response_class=RedirectResponse)
async def logout():
    response = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    response.delete_cookie(key='access_token')
    return response















































