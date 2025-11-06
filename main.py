from fastapi import FastAPI, Request, Depends, status
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.exception_handlers import http_exception_handler as fastapi_http_exception_handler
from starlette.exceptions import HTTPException as StarletteHTTPException
from urllib.parse import quote



from routers.auth import authentication
from routers.auth.oauth2 import UserPublic, get_current_user_cookie, validate_current_user_cookie, require_role
from routers.administration import users
from routers.operation import operation
from routers.dashboard import dashboard
from routers.calendar import reservation 









app = FastAPI()

app.include_router(authentication.router)
app.include_router(users.router)
app.include_router(operation.router)
app.include_router(dashboard.router)
app.include_router(reservation.router)


app.mount('/static', StaticFiles(directory='static'), name='static')
templates = Jinja2Templates(directory='templates')




@app.get('/', response_class=HTMLResponse)
async def home(request: Request):

    current_user: UserPublic = await validate_current_user_cookie(request)

    return templates.TemplateResponse('home.html', {
        'request': request,
        'user': current_user.model_dump(),
    })





# EXCEPTION_HANDLER-----------------------------------------------------------------------------------------------------



@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):
    # If it’s a 401 (Unauthorized) or 403 (Forbidden), redirect to /login
    if exc.status_code in (401, 403):
        return RedirectResponse(url=f"/login?error={quote(exc.detail)}")

    # 404 (Not Found)
    if exc.status_code == 404:
        return templates.TemplateResponse('pages/error-404.html', {'request': request}, status_code=404)

    # 500 (Internal Server Error)
    if exc.status_code == 500:
        return templates.TemplateResponse('pages/error-500.html', {'request': request}, status_code=500)
    
    
    # Otherwise, fall back to FastAPI’s default HTTP‐exception handler
    return await fastapi_http_exception_handler(request, exc)




if __name__ == '__main__':
    import uvicorn

    uvicorn.run(
        app='main:app',
        host="0.0.0.0",
        port=8080,
        reload=True,
    )
