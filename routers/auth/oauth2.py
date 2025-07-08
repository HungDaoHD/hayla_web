from datetime import datetime
from fastapi.security import OAuth2PasswordBearer, APIKeyCookie
from fastapi import Depends, Request, HTTPException, status

from routers.auth.auth_token import AuthToken, UserPublic



oauth2_scheme = OAuth2PasswordBearer(tokenUrl='token')
api_key_cookie = APIKeyCookie(name='access_token')



async def get_current_user_bearer(token: str = Depends(oauth2_scheme)) -> UserPublic:
    return AuthToken().verify_token(token)



async def get_current_user_cookie(token: str = Depends(api_key_cookie)) -> UserPublic:
    return AuthToken().verify_token(token)



async def validate_current_user_cookie(request: Request) -> UserPublic:

    if request.cookies.get("access_token"):
        return await get_current_user_cookie(request.cookies.get("access_token"))

    else:
        return UserPublic(
            id='-1',
            email='Guest.NONE',
            firstname='Guest',
            lastname='None',
            role='NONE',
            active=False,
            location='SGN',
            last_login=datetime.now()
        )



def require_role(role: list):

    lst_role = [i.lower() for i in role]

    async def _require(current_user: UserPublic = Depends(get_current_user_cookie)) -> UserPublic:

        if current_user.role.lower() not in lst_role:

            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"You must have the '{', '.join(role)}' role to access this endpoint",
            )

        return current_user

    return _require


