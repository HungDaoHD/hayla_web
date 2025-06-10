from pydantic import BaseModel, Field, constr, conint, conlist
from typing import Optional, Literal
from bson import ObjectId
from pymongo import ReturnDocument

from fastapi import HTTPException
from fastapi.encoders import jsonable_encoder

from mvc.database import mongo_db



class RawIngredient(BaseModel):
    id: str = Field(default_factory=ObjectId, alias='_id')
    Raw_Ingredient_ID: constr(pattern=r"^RIG\d+$")
    Raw_Ingredient_Name: constr(min_length=2)
    Cost: conint(ge=1000)
    Quanty: conint(ge=1)
    Unit: Literal["gram", "ml", "ly", "trái", "gói"]
    Cost_Per_Unit: conint(ge=1)

    model_config = {
        'populate_by_name': True,
        'arbitrary_types_allowed': True,
        'json_encoders': {ObjectId: lambda oid: str(oid)},
    }



class RawIngredientItem(BaseModel):
    Raw_Ingredient_ID: constr(pattern=r"^RIG\d+$")
    Raw_Ingredient_Quanty: conint(gt=1)

    Raw_Ingredient_Name: Optional[constr(min_length=2)] = None
    Unit: Optional[Literal["gram", "ml", "ly", "trái", "gói"]] = None
    Cost_Per_Unit: Optional[conint(ge=1)] = None







class ProcessedIngredient(BaseModel):
    id: str = Field(default_factory=ObjectId, alias='_id')
    Processed_Ingredient_ID: constr(pattern=r"^PIG\d+$")
    Processed_Ingredient_Name: constr(min_length=3)
    Used_Quanty: conint(ge=1)
    Raw_Ingredients: conlist(RawIngredientItem, min_length=2)

    model_config = {
        'populate_by_name': True,
        'arbitrary_types_allowed': True,
        'json_encoders': {ObjectId: lambda oid: str(oid)},
    }









class Operation:

    def __init__(self):
        self.mongo_db = mongo_db
        self.clt_raw_ingredient = mongo_db.hayladb['raw_ingredient']
        self.clt_processed_ingredient = mongo_db.hayladb['processed_ingredient']
        self.clt_recipes = mongo_db.hayladb['recipes']



    async def retrieve_raw_ingredient(self) -> list[RawIngredient]:

        lst_raw_ingredient = list()

        async for rig in self.clt_raw_ingredient.find({'Raw_Ingredient_ID': {'$exists': True, '$ne': None}}):

            rig_data = jsonable_encoder(rig, custom_encoder={ObjectId: str})
            lst_raw_ingredient.append(RawIngredient(**rig_data))

        return lst_raw_ingredient




    async def convert_processed_ingredient(self, pig: dict) -> ProcessedIngredient:

        pig_data = jsonable_encoder(pig, custom_encoder={ObjectId: str})
        pig_data = ProcessedIngredient(**pig_data)

        for item in pig_data.Raw_Ingredients:
            rig = await self.clt_raw_ingredient.find_one({'Raw_Ingredient_ID': {'$exists': True, '$eq': item.Raw_Ingredient_ID}})
            rig_data = jsonable_encoder(rig, custom_encoder={ObjectId: str})
            rig_data = RawIngredient(**rig_data)

            item.Raw_Ingredient_Name = rig_data.Raw_Ingredient_Name
            item.Unit = rig_data.Unit
            item.Cost_Per_Unit = rig_data.Cost_Per_Unit

        return pig_data



    async def retrieve_processed_ingredient(self) -> list[RawIngredient]:

        lst_processed_ingredient = list()

        async for pig in self.clt_processed_ingredient.find({'Processed_Ingredient_ID': {'$exists': True, '$ne': None}}):
            pig_data = await self.convert_processed_ingredient(pig)

            lst_processed_ingredient.append(pig_data)




        return lst_processed_ingredient





