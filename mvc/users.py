from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from bson import ObjectId
from pymongo import ReturnDocument

from fastapi import HTTPException
from fastapi.encoders import jsonable_encoder

from routers.auth.password_hashing import PasswordHashing
from mvc.database import mongo_db



class UserInDB(BaseModel):
    id: str = Field(default_factory=ObjectId, alias='_id')
    email: EmailStr
    firstname: str
    lastname: str
    hashed_password: str
    role: str = 'Guest'
    active: bool = False

    model_config = {
        'populate_by_name': True,
        'arbitrary_types_allowed': True,
        'json_encoders': {ObjectId: lambda oid: str(oid)},
    }



class UserPublic(BaseModel):
    id: str
    email: str
    firstname: str
    lastname: str
    role: str = 'Guest'
    active: bool = False

    model_config = {
        'from_attributes': True,
        'json_encoders': {ObjectId: lambda oid: str(oid)},
    }


    # @classmethod
    # def convert(cls, data: dict) -> 'UserPublic':
    #
    #     user = UserPublic(
    #         id=str(data['_id']),
    #         email=data['email'],
    #         firstname=data['firstname'],
    #         lastname=data['lastname'],
    #         role=data['role'],
    #         active=data['active'],
    #     )
    #
    #     return user



class UserUpdate(BaseModel):
    firstname: str | None = None
    lastname: str | None = None
    role: str | None = None
    active: bool | None = None



class CrudUser:

    def __init__(self):
        self.mongo_db = mongo_db
        self.user: UserInDB | None = None
        self.pub_user: UserPublic | None = None



    async def get_user_by_email(self, email: str) -> Optional[UserInDB]:

        user = await self.mongo_db.clt_user.find_one({'email': email})

        if not user:
            return None

        data_user = jsonable_encoder(user, custom_encoder={ObjectId: str})

        self.user = UserInDB(**data_user)

        if self.user:
            return self.user

        return None



    async def authenticate_user(self, email: str, password: str) -> Optional[UserInDB] | tuple:
        await self.get_user_by_email(email)

        if not self.user:
            return False, 'Email is not found'

        if not PasswordHashing().verify_password(hashed_pwd=self.user.hashed_password, plain_pwd=password):
            return False, 'Incorrect username or password'

        if not self.user.active:
            return False, 'Email is not active, please contact admin to activate it'

        return self.user


    
    def get_public_user(self) -> Optional[UserPublic]:

        if self.user:
            user = self.user.model_dump()
            user.pop('hashed_password')
            data_user = jsonable_encoder(user, custom_encoder={ObjectId: str})
            return UserPublic(**data_user)


        return None



    async def retrieve_normal_users(self) -> list[UserPublic]:

        lst_normal_user = list()

        async for user in self.mongo_db.clt_user.find({
            'role': {'$exists': True, '$ne': 'Admin'}
        }, {'hashed_password': 0}):

            data = jsonable_encoder(user, custom_encoder={ObjectId: str})
            data['id'] = data['_id']
            lst_normal_user.append(UserPublic(**data))

        return lst_normal_user



    async def update_user(self, user_id: str, payload: UserUpdate) -> UserPublic:

        try:
            oid = ObjectId(user_id)

        except Exception:
            raise HTTPException(status_code=400, detail='Invalid user_id')


        update_data = {k: v for k, v in payload.model_dump().items() if v is not None}


        if not update_data:
            raise HTTPException(status_code=400, detail='No fields to update')

        updated_user = await self.mongo_db.clt_user.find_one_and_update(
            {'_id': oid},
            {'$set': update_data},
            return_document=ReturnDocument.AFTER,
            projection={'hashed_password': 0}  # exclude password if desired
        )

        if not updated_user:
            raise HTTPException(status_code=404, detail='User not found')

        updated_user = jsonable_encoder(updated_user, custom_encoder={ObjectId: str})
        updated_user['id'] = updated_user['_id']
        updated_user = UserPublic(**updated_user)

        return updated_user
