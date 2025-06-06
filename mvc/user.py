from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from bson import ObjectId

from routers.Auth.password_hashing import PasswordHashing
from mvc.database import mongo_db



class UserInDB(BaseModel):
    id: ObjectId = Field(default_factory=ObjectId, alias="_id")
    email: EmailStr
    firstname: str
    lastname: str
    hashed_password: str
    role: str = 'Guest'
    active: bool = False

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {ObjectId: lambda oid: str(oid)},
    }



class UserPublic(BaseModel):
    id: str
    email: str
    name: str
    role: str = 'Guest'
    active: bool = False

    model_config = {
        "from_attributes": True
    }



class CrudUser:

    def __init__(self):
        self.mongo_db = mongo_db
        self.user: UserInDB | None = None
        self.pub_user: UserPublic | None = None


    async def get_user_by_email(self, email: str) -> Optional[UserInDB]:

        self.user = UserInDB(** await self.mongo_db.clt_user.find_one({'email': email}))

        if self.user:
            return self.user

        return None



    async def authenticate_user(self, email: str, password: str) -> Optional[UserInDB]:
        await self.get_user_by_email(email)

        if not self.user:
            return None

        if not PasswordHashing().verify_password(hashed_pwd=self.user.hashed_password, plain_pwd=password):
            return None

        return self.user



    def get_public_user(self) -> Optional[UserPublic]:

        if self.user:
            return UserPublic(
                id=str(self.user.id),
                email=str(self.user.email),
                name=f"{self.user.firstname} {self.user.lastname}",
                role=self.user.role,
                active=self.user.active
            )

        return None











