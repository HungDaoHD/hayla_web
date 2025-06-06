from fastapi import FastAPI, Request, Depends, status
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse



from routers.Auth import authentication
from routers.Auth.oauth2 import get_current_user_cookie
from routers.Auth.auth_token import UserPublic


app = FastAPI()
app.include_router(authentication.router)


app.mount('/static', StaticFiles(directory='static'), name='static')
templates = Jinja2Templates(directory='templates')




@app.get('/', response_class=HTMLResponse)
async def home(request: Request, current_user: UserPublic = Depends(get_current_user_cookie)):
    return templates.TemplateResponse('/home.html', {
        'request': request,
        'user': current_user.model_dump(),
    })



@app.get('/dashboard', response_class=HTMLResponse)
async def home(request: Request, current_user: UserPublic = Depends(get_current_user_cookie)):
    return templates.TemplateResponse('/dashboard/index.html', {
        'request': request,
        'user': current_user.model_dump(),
    })



@app.get('/calendar', response_class=HTMLResponse)
async def home(request: Request, current_user: UserPublic = Depends(get_current_user_cookie)):
    return templates.TemplateResponse('/application/calendar.html', {
        'request': request,
        'user': current_user.model_dump(),
    })





# EXCEPTION_HANDLER-----------------------------------------------------------------------------------------------------



@app.exception_handler(status.HTTP_404_NOT_FOUND)
async def custom_404_handler(request: Request, _):
    # print('HTTP_404_NOT_FOUND')
    return templates.TemplateResponse('pages/error-404.html', {'request': request}, status_code=404)



@app.exception_handler(status.HTTP_403_FORBIDDEN)
async def custom_403_handler(_, __):
    # print('HTTP_403_FORBIDDEN')
    return RedirectResponse('/login', status_code=status.HTTP_403_FORBIDDEN)



@app.exception_handler(status.HTTP_401_UNAUTHORIZED)
async def custom_401_handler(_, __):
    # print('HTTP_401_UNAUTHORIZED')
    return RedirectResponse('/login', status_code=status.HTTP_401_UNAUTHORIZED)






if __name__ == '__main__':
    import uvicorn

    uvicorn.run(
        app='main:app',  # <module>:<app instance>
        # host="127.0.0.1",  # or "0.0.0.0" to listen on all interfaces
        # port=8000,
        reload=True,  # watch for code changes
    )
