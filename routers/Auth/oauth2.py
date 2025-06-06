from fastapi.security import OAuth2PasswordBearer, APIKeyCookie
from fastapi import Depends
from routers.Auth.auth_token import AuthToken, UserPublic



oauth2_scheme = OAuth2PasswordBearer(tokenUrl='token')
api_key_cookie = APIKeyCookie(name='access_token', auto_error=False)



async def get_current_user_bearer(token: str = Depends(oauth2_scheme)) -> UserPublic:
    return AuthToken().verify_token(token)



async def get_current_user_cookie(token: str = Depends(api_key_cookie)) -> UserPublic:

    if not token:
        return UserPublic(id='-1', email='Guest.NONE', name='Guest', role='NONE', active=False)

    return AuthToken().verify_token(token)
