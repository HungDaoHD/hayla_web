import datetime
import os
from dotenv import load_dotenv
from jose import JWTError, jwt
from fastapi import HTTPException, status

from mvc.users import UserPublic


# import secrets
#
# # Generate a 32-byte (256-bit) URL-safe token
# print(secrets.token_urlsafe(32))


load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY is not set in .env or environment")


ALGORITHM = 'HS256'
ACCESS_TOKEN_EXPIRE_MINUTES = 30



class AuthToken:

    @staticmethod
    def create_access_token(data: dict, expires_minutes: int = None) -> str:

        if not expires_minutes:
            expire = datetime.datetime.now(datetime.UTC) + datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        else:
            expire = datetime.datetime.now(datetime.UTC) + datetime.timedelta(minutes=expires_minutes)

        to_encode = data.copy()
        to_encode.update({"exp": expire})

        return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)



    @staticmethod
    def decode_access_token(token: str) -> dict:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])



    def verify_token(self, token: str) -> UserPublic:

        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Could not validate credentials',
            headers={'WWW-Authenticate': 'Bearer'},
        )

        try:
            payload = self.decode_access_token(token)


            return UserPublic(**{
                'id': payload.get('id'),
                'email': payload.get('email'),
                'firstname': payload.get('firstname'),
                'lastname': payload.get('lastname'),
                'role': payload.get('role'),
                'active': payload.get('active'),
                'location': payload.get('location'),
                'last_login': datetime.datetime.strptime(payload.get('last_login'), "%d/%m/%Y %H:%M"),
            })


        except JWTError:
            raise credentials_exception







