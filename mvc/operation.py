import pandas as pd
import numpy as np
from pydantic import BaseModel, Field, field_validator, model_validator, computed_field, EmailStr
from typing import Optional, Literal, Union, Dict, List, Annotated
from bson import ObjectId
from pymongo import ReturnDocument, UpdateOne
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from fastapi import HTTPException, UploadFile
from fastapi.encoders import jsonable_encoder

from mvc.database import mongo_db
from mvc.users import UserPublic
from mvc.mailer import mailer






class LocationFixedCost(BaseModel):
    SGN: Union[int, float] = Field(..., ge=10000)
    NTR: Union[int, float] = Field(..., ge=0)



class FixedCost(BaseModel):
    id: str = Field(default_factory=ObjectId, alias="_id")
    Fixed_Cost_ID: str = Field(pattern=r"^FIX\d+$")
    Fixed_Cost_Name: str = Field(min_length=3)
    Cost: LocationFixedCost

    model_config = {
        'populate_by_name': True,
        'arbitrary_types_allowed': True,
        'json_encoders': {ObjectId: lambda oid: str(oid)},
    }
    


class RawIngredient(BaseModel):
    id: str = Field(default_factory=ObjectId, alias='_id')
    Raw_Ingredient_ID: str = Field(pattern=r"^RIG\d+$")
    Raw_Ingredient_Name: str = Field(min_length=2)
    Group: Literal[
        '1. Cà phê, Trà & Bột', 
        '2. Sữa, Kem & Nguyên liệu khác', 
        '3. Syrup, Sốt, Mứt & Topping', 
        '4. Bao bì & Phụ kiện', 
        '5. Vệ sinh & Hỗ trợ', 
        '99. Undefine'
    ] = Field(min_length=3)
    Location: List[Literal["SGN", "NTR"]] = Field(min_length=1)
    Cost: int = Field(ge=1000)
    Quanty: int = Field(ge=1)
    Unit: Literal["gram", "ml", "ly", "trái", "gói"]
    Enable: bool = Field(...)

    # Calculated fields
    Cost_Per_Unit: Annotated[float, Field(ge=1, default=None)]

    model_config = {
        'populate_by_name': True,
        'arbitrary_types_allowed': True,
        'json_encoders': {ObjectId: lambda oid: str(oid)},
    }


    @model_validator(mode='after')
    @classmethod
    def compute_unit_cost(cls, values):
        values.Cost_Per_Unit = values.Cost / values.Quanty
        return values



class RawIngredientItem(BaseModel):
    Raw_Ingredient_ID: str = Field(pattern=r"^RIG\d+$")
    Raw_Ingredient_Quanty: int = Field(gt=1)

    # Reference fields
    Raw_Ingredient_Name: Annotated[str, Field(min_length=2, default=None)]
    Unit: Annotated[Literal["gram", "ml", "ly", "trái", "gói"], Field(description="Must be in ['gram', 'ml', 'ly', 'trái', 'gói']", default=None)]
    Cost_Per_Unit: Annotated[float, Field(ge=1, default=None)]
    Enable: Annotated[bool, Field(default=None)]

    # Calculated fields
    Total_Cost: Annotated[float, Field(ge=1, default=None)]
    Cost_Per_Proc_Unit: Annotated[float, Field(ge=1, default=None)]



    def add_data_ref_cal_fields(self, rig: RawIngredient, pig_qty: float):
        self.Raw_Ingredient_Name = rig.Raw_Ingredient_Name
        self.Unit = rig.Unit
        self.Cost_Per_Unit = rig.Cost_Per_Unit
        self.Enable = rig.Enable

        self.Total_Cost = self.Raw_Ingredient_Quanty * self.Cost_Per_Unit
        self.Cost_Per_Proc_Unit = self.Total_Cost / pig_qty



class ProcessedIngredient(BaseModel):
    id: str = Field(default_factory=ObjectId, alias='_id')
    Processed_Ingredient_ID: str = Field(pattern=r"^PIG\d+$")
    Processed_Ingredient_Name: str = Field(min_length=3)
    Used_Quanty: int = Field(ge=1)
    Raw_Ingredients: List[RawIngredientItem] = Field(min_length=1)
    Quanty: int = Field(ge=1)
    Unit: Literal["ml", "gram"]

    
    # Calculated fields
    Total_Cost: Annotated[float, Field(ge=1000, default=0)]
    Cost_Per_Unit: Annotated[float, Field(ge=1, default=None)]


    model_config = {
        'populate_by_name': True,
        'arbitrary_types_allowed': True,
        'json_encoders': {ObjectId: lambda oid: str(oid)},
    }



class IngredientForFil(BaseModel):
    ID: str = Field(pattern=r"^(R|P)IG\d+$")
    Name: str = Field(min_length=3)
    Unit: Literal["gram", "ml", "ly", "trái", "gói"]
    Type: Literal["Raw", "Processed"] = Field(default=None)
    Cost_Per_Unit: Annotated[float, Field(ge=1, default=0)]
    

    @model_validator(mode='after')
    @classmethod
    def compute_ingredient_type(cls, values):
        values.Type = 'Raw' if values.ID[:3] == 'RIG' else 'Processed'
        return values



class DrinkIngredientItem(BaseModel):
    Ingredient_ID: str = Field(pattern=r"^(RIG|PIG)\d+$")
    Ingredient_Quanty: float = Field(ge=0.1)

    # Reference fields
    Ingredient_Name: Annotated[str, Field(min_length=2, default=None)]
    Unit: Optional[str] = None
    Cost_Per_Unit: Annotated[float, Field(ge=1, default=None)]

    # Calculated fields
    Total_Cost: Annotated[float, Field(ge=1, default=0)]



    def add_data_ref_cal_fields(self, igr: RawIngredient | ProcessedIngredient):

        if isinstance(igr, RawIngredient):

            self.Ingredient_Name = igr.Raw_Ingredient_Name
            self.Unit = igr.Unit
            self.Cost_Per_Unit = igr.Cost_Per_Unit

            self.Total_Cost = self.Ingredient_Quanty * self.Cost_Per_Unit

        else:

            self.Ingredient_Name = igr.Processed_Ingredient_Name
            self.Unit = igr.Unit
            self.Cost_Per_Unit = igr.Cost_Per_Unit

            self.Total_Cost = self.Ingredient_Quanty * self.Cost_Per_Unit




class DrinkPrice(BaseModel):
    Size_S: Annotated[Union[float, int], Field(ge=10000)] | Literal[0] = 0
    Size_M: Annotated[Union[float, int], Field(ge=10000)] | Literal[0] = 0
    Size_L: Annotated[Union[float, int], Field(ge=10000)] | Literal[0] = 0



class LocationDrinkPrice(BaseModel):
    SGN: DrinkPrice
    NTR: DrinkPrice



class Drink(BaseModel):
    id: str = Field(default_factory=ObjectId, alias='_id')
    Group: str = Field(min_length=3)
    Location: List[Literal["SGN", "NTR"]] = Field(min_length=1)
    Drink_ID: str = Field(pattern=r"^DRK\d+$")
    Drink_Name: str = Field(min_length=3)
    Ingredients: List[DrinkIngredientItem] = Field(min_length=1)
    Price: LocationDrinkPrice
    Enable: bool = Field(...)

    # Calculated fields
    Total_Cost: Annotated[float, Field(ge=1, default=0)]
    Weighting: Annotated[dict, Field(default={'SGN': {'Size_S': 0, 'Size_M': 1, 'Size_L': 0}, 'NTR': {'Size_S': 0, 'Size_M': 0, 'Size_L': 0}})]
    Extra_Cost: Annotated[dict, Field(description="Ly nhựa, ống hút, trà đá", default={'SGN': 0, 'NTR': 2000})]


    model_config = {
        'populate_by_name': True,
        'arbitrary_types_allowed': True,
        'json_encoders': {ObjectId: lambda oid: str(oid)},
    }
    
    

class DrinkIngredientItemUpdate(BaseModel):
    Ingredient_ID: str = Field(pattern=r"^(RIG|PIG)\d+$")
    Ingredient_Quanty: float = Field(ge=0.1)



class DrinkUpdate(BaseModel):
    Drink_ID: str = Field(pattern=r"^DRK\d+$")
    Drink_Name: str = Field(min_length=3, default=None)
    Group: str = Field(min_length=3, default=None)
    Location: List[Literal["SGN", "NTR"]] = Field(min_length=1, default=None)
    Price: LocationDrinkPrice = Field(default=None)
    Ingredients: List[DrinkIngredientItemUpdate] = Field(min_length=1, default=None)




# HERE
class DrinkIngredientEntry(BaseModel):
    Ingredient_ID: Annotated[str, Field(pattern=r'^(?:RIG|PIG)\d+$')]
    Ingredient_Quanty: Annotated[int | float, Field(gt=.01, description='Lượng dùng để pha chế')]

    # Reference fields
    Ingredient_Name: Annotated[str, Field(min_length=2, default=None)]
    Unit: Annotated[Literal['gram', 'ml', 'ly', 'trái', 'gói'], Field(description="Must be in ['gram', 'ml', 'ly', 'trái', 'gói']", default=None)]
    Cost_Per_Unit: Annotated[float, Field(ge=1, default=None)]

    # Calculated fields
    Ingredient_Driect_Cost: Annotated[float, Field(ge=1, default=0)]


    def add_data_ref_cal_fields(self, igr):
        self.Ingredient_Name = igr.Name
        self.Unit = igr.Unit
        self.Cost_Per_Unit = igr.Cost_Per_Unit
        self.Ingredient_Driect_Cost = self.Ingredient_Quanty * self.Cost_Per_Unit

        



class DrinkRecipeSize(BaseModel):
    Ingredients: Dict[str, DrinkIngredientEntry]
    Price: Annotated[int, Field(ge=0)]

    # Calculated fields
    Drink_Driect_Cost: Annotated[float, Field(ge=1, default=0)]
    Drink_Margin: Annotated[float, Field(ge=-1, default=0)]
    
    
    @field_validator("Ingredients", mode="before")
    @classmethod
    def ingridients_list_to_dict(cls, value: Union[list, dict]):
        
        if isinstance(value, dict):
            return value
        
        dict_out = {}
        
        for item in value:
            if isinstance(item, DrinkIngredientEntry):
                key = item.Ingredient_ID
                val = item
            
            else:
                key = item["Ingredient_ID"]
                val = item
            dict_out[key] = val
        
        return dict_out
    
    
    
    def recipe_update(self, dict_full_igr: dict):
        
        for key, val in self.Ingredients.items():
            val.add_data_ref_cal_fields(dict_full_igr[key])
            self.Drink_Driect_Cost += val.Ingredient_Driect_Cost
        
        self.Drink_Margin = (self.Price - self.Drink_Driect_Cost) / self.Price 
        
        
    
    
    
    
    
    
    

class DrinkRecipeMonth(BaseModel):
    S: Optional[DrinkRecipeSize] = Field(None, alias="_S")
    M: DrinkRecipeSize = Field(..., alias="_M")
    L: Optional[DrinkRecipeSize] = Field(None, alias="_L")
    
    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True
    }
    
     
    def recipe_update(self, dict_full_igr: dict):
        for fname in self.model_fields_set:
            getattr(self, fname).recipe_update(dict_full_igr)

        
    
    


class DrinkV2(BaseModel):
    
    # Mandatory fields
    id: str = Field(default_factory=ObjectId, alias='_id')
    Drink_ID: str = Field(pattern=r"^DRK\d{3}[a-z]?+$")
    Drink_Name: str = Field(min_length=3)
    Group: str = Field(min_length=3)
    Location: str = Literal['SGN', 'NTR']
    Enable: bool = Field(...)
    Recipe: Dict[Annotated[str, Field(pattern=r'^(?:2025_(?:0[7-9]|1[0-2])|20(?:2[6-9]|[3-9]\d)_(?:0[1-9]|1[0-2]))$')], DrinkRecipeMonth]
    
    # Calculated fields
    Extra_Cost: Annotated[int | float, Field(description="Ly nhựa, ống hút, trà đá", default=0)]

    model_config = {
        'populate_by_name': True,
        'arbitrary_types_allowed': True,
        'json_encoders': {ObjectId: lambda oid: str(oid)},
    }

    
    @model_validator(mode='after')
    @classmethod
    def compute_unit_cost(cls, values):
        if values.Location in ['SGN']:
            return values
        
        values.Extra_Cost = 2000
        
        if values.Drink_ID in ['DRK031', 'DRK032']:
            values.Extra_Cost = 4000
        
        return values

    
    def recipe_update(self, dict_full_igr: dict):
        for val in self.Recipe.values():
            val.recipe_update(dict_full_igr)
        
        



# STOCK HERE START
class StockItemInsert(BaseModel):
    Raw_Ingredient_ID: str = Field(pattern=r"^RIG\d+$")
    Location: Literal['SGN', 'NTR']
    email: str = Field(default=None)
    Method: Literal['add', 'get', 'check'] = Field(default=None)
    DateTime: datetime = Field(default=None)
    Qty_Instock: float = Field(ge=0, le=100)
    Qty_Outstock: float = Field(ge=0, le=100)
    


class StockItem(BaseModel):
    id: str = Field(default_factory=ObjectId, alias='_id')
    Raw_Ingredient_ID: str = Field(pattern=r"^RIG\d+$")
    Location: Literal['SGN', 'NTR']
    email: EmailStr
    Method: Literal['add', 'get', 'check']
    DateTime: datetime
    Qty_Instock: float = Field(ge=0, le=100)
    Qty_Outstock: float = Field(ge=0, le=100)


    # Reference fields
    Raw_Ingredient_Name: Annotated[str, Field(min_length=2, default=None)]
    Quanty: Annotated[int, Field(ge=1, default=None)]
    Unit: Annotated[Literal["gram", "ml", "ly", "trái", "gói"], Field(description="Must be in ['gram', 'ml', 'ly', 'trái', 'gói']", default=None)]


    model_config = {
        'populate_by_name': True,
        'arbitrary_types_allowed': True,
        'json_encoders': {
            ObjectId: lambda oid: str(oid),
            datetime: lambda dt: dt.strftime("%d/%m/%y %H:%M"),
        },
    }


class DeleteStockItems(BaseModel):
    ids: list[str]



class SummaryStockFilter(BaseModel):
    Location: Literal['SGN', 'NTR']



# class SummaryStockResult:
#     check_date_start: datetime
#     check_date_end: datetime
    

#     model_config = {
#         'populate_by_name': True,
#         'arbitrary_types_allowed': True,
#         'json_encoders': {
#             ObjectId: lambda oid: str(oid),
#             datetime: lambda dt: dt.strftime("%d/%m/%y %H:%M"),
#         },
#     }
    


# STOCK HERE END






















class InventoryItem(BaseModel):
    id: str = Field(default_factory=ObjectId, alias='_id')
    Raw_Ingredient_ID: str = Field(pattern=r"^RIG\d+$")
    Location: Literal["SGN", "NTR"]
    email: EmailStr
    Action: Literal["add", "get"]
    DateTime: datetime
    Qty: float = Field(ge=1, le=50)


    # Reference fields
    Raw_Ingredient_Name: Annotated[str, Field(min_length=2, default=None)]
    Quanty: Annotated[int, Field(ge=1, default=None)]
    Unit: Annotated[Literal["gram", "ml", "ly", "trái", "gói"], Field(description="Must be in ['gram', 'ml', 'ly', 'trái', 'gói']", default=None)]


    model_config = {
        'populate_by_name': True,
        'arbitrary_types_allowed': True,
        'json_encoders': {
            ObjectId: lambda oid: str(oid),
            datetime: lambda dt: dt.strftime("%d/%m/%Y %H:%M"),
        },
    }


    @field_validator('Qty')
    @classmethod
    def value_not_zero(cls, qty: float) -> float:
        if qty == 0:
            raise ValueError('value must not be zero')
        return qty



class InventoryItemInsert(BaseModel):
    Raw_Ingredient_ID: str = Field(pattern=r"^RIG\d+$")
    Location: Literal["SGN", "NTR"]
    email: str = Field(default=None)
    Action: Literal["add", "get"] = Field(default=None)
    DateTime: datetime = Field(default=None)
    Qty: float = Field(ge=1, le=50)



class ReceiptItemUpload(BaseModel):
    Product_Code: str = Field(pattern=r"^DRK\d+$")
    Quantity: int = Field(ge=1)
    Size: Literal["Size_S", "Size_M", "Size_L"]
    Topping: Annotated[Optional[str], Field(min_length=2)] = None



class ReceiptUpload(BaseModel):
    Location: Literal["SGN", "NTR"]
    Order_Day: str = Field(pattern=r"^(?:\d{4})-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12]\d|3[01])$")
    Order_Code: str = Field(pattern=r"^BH\d+$")
    Payment_Time: datetime
    Payment_Method: Literal["Cash", "Tranfer", "Shopee"]
    Amount: float = Field(ge=0)
    Items: List[ReceiptItemUpload] = Field(min_length=1)



class ReceiptItem(BaseModel):
    Product_Code: str = Field(pattern=r"^DRK\d+$")
    Quantity: int = Field(ge=1)
    Size: Literal["Size_S", "Size_M", "Size_L"]
    Topping: Annotated[Optional[str], Field(min_length=2)] = None
    
    # Reference fields from Drink
    Group: Annotated[str, Field(min_length=3, default=None)]
    Drink_Name: Annotated[str, Field(min_length=3, default=None)]

    # Calculated fields based on Size (Unit)
    Price_By_Size: Annotated[Union[float, int], Field(ge=10000)] | Literal[0] = 0
    Total_Cost_By_Size: Annotated[float, Field(ge=1, default=0)]
    Ingredients_By_Size: Annotated[List[DrinkIngredientItem], Field(min_length=1, default=[])]
    Margin_By_Size: Annotated[float, Field(ge=0, default=0)] = 0



class Receipt(BaseModel):
    id: str = Field(default_factory=ObjectId, alias='_id')
    Location: Literal["SGN", "NTR"]
    Order_Day: str = Field(pattern=r"^(?:\d{4})-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12]\d|3[01])$")
    Order_Code: str = Field(pattern=r"^BH\d+$")
    Payment_Time: datetime
    Payment_Method: Literal["Cash", "Tranfer", "Shopee"]
    Amount: float = Field(ge=0)
    Items: List[ReceiptItem] = Field(min_length=1)
    
    
    model_config = {
        'populate_by_name': True,
        'arbitrary_types_allowed': True,
        'json_encoders': {ObjectId: lambda oid: str(oid)},
    }





class Operation:

    def __init__(self):
        self.clt_raw_ingredient = mongo_db.hayladb['raw_ingredient']
        self.clt_processed_ingredient = mongo_db.hayladb['processed_ingredient']
        self.clt_drink = mongo_db.hayladb['drink']
        self.clt_drink_v2 = mongo_db.hayladb['drink_v2']
        self.clt_fixed_cost = mongo_db.hayladb['fixed_cost']
        self.clt_inventory = mongo_db.hayladb['inventory']
        self.clt_stock = mongo_db.hayladb['stock']
        self.clt_receipt = mongo_db.hayladb['receipt']


    
    @staticmethod
    async def convert_raw_ingredient(rig: dict, current_user: UserPublic) -> RawIngredient:
        rig_data = RawIngredient(**(jsonable_encoder(rig, custom_encoder={ObjectId: str})))

        if current_user.role.upper() not in ['ADMIN']:
            rig_data.Cost_Per_Unit = 0

        return rig_data



    async def retrieve_raw_ingredient(self, current_user: UserPublic, is_group: bool = False, is_show_disable: bool = False) -> list[RawIngredient] | Dict[str, RawIngredient]:
        
        dict_db_filter = {'Raw_Ingredient_ID': {'$exists': True, '$ne': None}}
        
        if not is_show_disable:
            dict_db_filter |= {'Enable': True}
        
        if current_user.role.lower() not in ['admin']:
            dict_db_filter |= {'Location': {'$in': [current_user.location]}}
        
        obj_raw_ingredient = list() if not is_group else dict()

        async for rig in self.clt_raw_ingredient.find(dict_db_filter).sort({'Enable': -1, 'Group': 1, 'Raw_Ingredient_Name': 1}):
            
            rig_data = await self.convert_raw_ingredient(rig, current_user)
                
            if isinstance(obj_raw_ingredient, dict):
                obj_raw_ingredient.setdefault(rig_data.Group, []).append(rig_data)
            
            else:
                obj_raw_ingredient.append(rig_data)
            

        return obj_raw_ingredient




    async def convert_processed_ingredient(self, pig: dict, current_user: UserPublic) -> ProcessedIngredient:
        
        pig_data = ProcessedIngredient(**(jsonable_encoder(pig, custom_encoder={ObjectId: str})))

        for item in pig_data.Raw_Ingredients:
            rig = await self.clt_raw_ingredient.find_one({'Raw_Ingredient_ID': {'$exists': True, '$eq': item.Raw_Ingredient_ID}})
            rig_data = await self.convert_raw_ingredient(jsonable_encoder(rig, custom_encoder={ObjectId: str}), current_user)
            item.add_data_ref_cal_fields(rig_data, pig_qty=pig_data.Quanty)  # item = RawIngredientItem

            # Calculated fields - pro igr
            pig_data.Total_Cost += item.Total_Cost
            pig_data.Cost_Per_Unit = pig_data.Total_Cost / pig_data.Quanty

        return pig_data



    async def retrieve_processed_ingredient(self, current_user: UserPublic) -> list[ProcessedIngredient]:

        lst_processed_ingredient = list()

        async for pig in self.clt_processed_ingredient.find({'Processed_Ingredient_ID': {'$exists': True, '$ne': None}}):
            pig_data = await self.convert_processed_ingredient(pig, current_user)
            lst_processed_ingredient.append(pig_data)

        return lst_processed_ingredient



    async def convert_drink(self, drk: dict, current_user: UserPublic) -> Drink:

        drk_data = Drink(**(jsonable_encoder(drk, custom_encoder={ObjectId: str})))
        
        for item in drk_data.Ingredients:

            if str(item.Ingredient_ID)[:3].upper() == 'RIG':

                drk_igr = await self.clt_raw_ingredient.find_one({'Raw_Ingredient_ID': {'$exists': True, '$eq': item.Ingredient_ID}})
                drk_igr_data = await self.convert_raw_ingredient(jsonable_encoder(drk_igr, custom_encoder={ObjectId: str}), current_user)

                item.add_data_ref_cal_fields(drk_igr_data)

            else:

                drk_igr = await self.clt_processed_ingredient.find_one({'Processed_Ingredient_ID': {'$exists': True, '$eq': item.Ingredient_ID}})
                drk_igr_data = await self.convert_processed_ingredient(drk_igr, current_user)

                item.add_data_ref_cal_fields(drk_igr_data)


            drk_data.Total_Cost += item.Total_Cost
            
            for loc in drk_data.Location:
                
                if loc == 'SGN':
                    continue

                obj_price_loc = getattr(drk_data.Price, loc)
                dict_weighting: dict = drk_data.Weighting.get(loc)
                
                if drk_data.Drink_ID in ['DRK31', 'DRK32']:
                    drk_data.Extra_Cost[loc] = 4000
                
                if obj_price_loc.Size_S > 0:
                    dict_weighting['Size_S'] = 1
                    dict_weighting['Size_M'] = 1.5
                    dict_weighting['Size_L'] = 1.5 * 1.5
                
                elif obj_price_loc.Size_S == 0 and obj_price_loc.Size_M > 0:
                    dict_weighting['Size_S'] = 0
                    dict_weighting['Size_M'] = 1
                    dict_weighting['Size_L'] = 1.5


        return drk_data



    async def retrieve_drink(self, groupby: Literal['GROUP', 'ID', None], dict_filter_mongodb: dict, current_user: UserPublic) -> Dict[str, list[Drink] | Drink] | list[Drink]:

        if groupby is None:
            drinks = list()
        else:
            drinks = dict()

        async for drk in self.clt_drink.find({
            'Drink_ID': {'$exists': True, '$ne': None},
            'Enable': True
        } | dict_filter_mongodb).sort({'Group': 1, 'Location': -1, 'Drink_Name': 1}):

            drk_data = await self.convert_drink(drk, current_user)

            if groupby.upper() == 'GROUP':
                group_key = drk_data.Group
                drinks.setdefault(group_key, []).append(drk_data)
            
            elif groupby.upper() == 'ID':
                group_key = drk_data.Drink_ID
                drinks.update({group_key: drk_data})
            
            else:
                drinks.append(drk_data)
                
        
        return drinks



    async def update_drink(self, oid: str, obj_drink: DrinkUpdate) -> DrinkUpdate:

        try:
            oid = ObjectId(oid)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f'Invalid drink_oid: {e}')

        update_data = {k: v for k, v in obj_drink.model_dump().items() if v is not None}

        if not update_data:
            raise HTTPException(status_code=400, detail='No fields to update')

        updated_drink = await self.clt_drink.find_one_and_update(
            {'_id': oid},
            {'$set': update_data},
            return_document=ReturnDocument.AFTER,
            # projection={'hashed_password': 0}
        )

        if not updated_drink:
            raise HTTPException(status_code=404, detail='Drink not found')

        updated_drink = DrinkUpdate(**updated_drink)

        return updated_drink


    
    # Here
    async def retrieve_drink_v2(self, groupby: Literal['GROUP', 'ID', None], dict_filter_mongodb: dict, current_user: UserPublic) -> Dict[str, list[DrinkV2] | DrinkV2] | list[DrinkV2]:
        
        drinks = list() if (groupby is None) else dict()
        
        dict_full_igr = await self.get_full_ingredients(output_type='DICT', current_user=current_user)
        
        async for drk in self.clt_drink_v2.find({
            'Drink_ID': {'$exists': True, '$ne': None},
            'Enable': True
        } | dict_filter_mongodb).sort({'Group': 1, 'Location': -1, 'Drink_ID': 1}):
            
            drk_data = DrinkV2(**(jsonable_encoder(drk, custom_encoder={ObjectId: str})))
            drk_data.recipe_update(dict_full_igr)
            
            if groupby.upper() == 'GROUP':
                group_key = drk_data.Group
                drinks.setdefault(group_key, []).append(drk_data)
            
            elif groupby.upper() == 'ID':
                group_key = drk_data.Drink_ID
                drinks.update({group_key: drk_data})
            
            else:
                drinks.append(drk_data)
                
        
        return drinks

    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    

    async def retrieve_fixed_cost(self) -> list[FixedCost]:

        lst_fixed_cost = list()

        async for fix in self.clt_fixed_cost.find({'Fixed_Cost_ID': {'$exists': True, '$ne': None}}):
            lst_fixed_cost.append(FixedCost(**(jsonable_encoder(fix, custom_encoder={ObjectId: str}))))

        return lst_fixed_cost




    async def convert_inventory(self, inv: dict) -> InventoryItem:
        inv_data = InventoryItem(**(jsonable_encoder(inv, custom_encoder={ObjectId: str})))

        rig = await self.clt_raw_ingredient.find_one({'Raw_Ingredient_ID': {'$exists': True, '$eq': inv_data.Raw_Ingredient_ID}})
        rig_data = jsonable_encoder(rig, custom_encoder={ObjectId: str})

        # Reference fields
        inv_data.Raw_Ingredient_Name = rig_data['Raw_Ingredient_Name']
        inv_data.Quanty = rig_data['Quanty']
        inv_data.Unit = rig_data['Unit']

        return inv_data



    async def retrieve_inventory(self, dict_filter_mongodb: dict) -> list[InventoryItem]:
        lst_inventory = list()

        async for inv in self.clt_inventory.find({
                'Raw_Ingredient_ID': {'$exists': True, '$ne': None}
            } | dict_filter_mongodb).sort({'DateTime': -1}):
            
            inv_data = await self.convert_inventory(inv)
            lst_inventory.append(inv_data)

        return lst_inventory




    @staticmethod
    def analyze_inventory(lst_inventory: list[InventoryItem], is_export_df: bool = False) -> list[dict] | pd.DataFrame:

        df_summary = pd.DataFrame([i.model_dump() for i in lst_inventory])

        df_total_qty: pd.DataFrame = (
            df_summary
            .groupby(['Raw_Ingredient_ID', 'Raw_Ingredient_Name', 'Location', 'Quanty', 'Unit', 'Action'])['Qty']
            .sum()
            .reset_index(name="TotalQty")
        ).pivot_table(
            columns=['Action'],
            values=['TotalQty'],
            aggfunc=['sum'],
            index=['Raw_Ingredient_ID', 'Raw_Ingredient_Name', 'Location', 'Quanty', 'Unit'],
            fill_value=0
        )
        
        flat_index = df_total_qty.columns.to_flat_index()
        df_total_qty.columns = flat_index.map(lambda t: t[-1])
        df_total_qty = df_total_qty.reset_index(drop=False)
        df_total_qty['remain'] = df_total_qty['add'] - df_total_qty['get']
        df_total_qty = df_total_qty.sort_values(by=['remain'], ascending=[True])

        return df_total_qty.to_dict(orient='records') if not is_export_df else df_total_qty



    async def add_inventory_items(self, lst_inv_item: list[InventoryItemInsert], current_user: UserPublic) -> list[InventoryItem]:
        
        try:
            lst_inv_item_dump = list()
            for i in lst_inv_item:
                i.email = current_user.email
                i.DateTime = datetime.now()
                lst_inv_item_dump.append(i.model_dump(by_alias=True, exclude_none=True))

            result = await self.clt_inventory.insert_many(lst_inv_item_dump)

        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Could not add inventory item(s): {e}")


        lst_inventory = list()
        async for inv in self.clt_inventory.find({"_id": {"$in": result.inserted_ids}}).sort({'DateTime': -1}):
            inv_data = await self.convert_inventory(inv)
            lst_inventory.append(inv_data)

        return lst_inventory

    


    async def get_full_ingredients(self, current_user: UserPublic, output_type: str = 'LST') -> list[IngredientForFil] | dict[str, IngredientForFil]:
        
        full_igrs = list() if output_type.upper() == 'LST' else dict()
        
        lst_full_pig = await self.retrieve_processed_ingredient(current_user)
        lst_full_rig = await self.retrieve_raw_ingredient(current_user)

        for pig in lst_full_pig:
            
            obj_igr = IngredientForFil(ID=pig.Processed_Ingredient_ID, Name=pig.Processed_Ingredient_Name, Unit=pig.Unit, Cost_Per_Unit=pig.Cost_Per_Unit)
            
            if isinstance(full_igrs, list):
                full_igrs.append(obj_igr)

            else:
                full_igrs.update({obj_igr.ID: obj_igr})
            
            
        for rig in lst_full_rig:
            
            obj_igr = IngredientForFil(ID=rig.Raw_Ingredient_ID, Name=rig.Raw_Ingredient_Name, Unit=rig.Unit, Cost_Per_Unit=rig.Cost_Per_Unit)
            
            if isinstance(full_igrs, list):
                full_igrs.append(obj_igr)
            
            else:
                full_igrs.update({obj_igr.ID: obj_igr})
        
        return full_igrs



    async def convert_receipt_file_to_dataframe(self, upload_file: UploadFile) -> List[ReceiptUpload]:

        try:
            df_receipt = pd.read_excel(upload_file.file, header=7)

            dict_sel_col = {
                'Shop name': 'Location',
                'Day': 'Order_Day',
                'Order code': 'Order_Code',
                
                'Payment time': 'Payment_Time',
                'Product code': 'Product_Code',
                'Quantity': 'Quantity',
                'Unit': 'Size',
                'Topping': 'Topping',
                'Amount after invoice discount': 'Amount',
                'Payment method': 'Payment_Method',
            }

            df_receipt: pd.DataFrame = df_receipt.loc[df_receipt.eval("~`Payment time`.isnull() & Status != 'Hủy'"), dict_sel_col.keys()]
            df_receipt = df_receipt.rename(columns=dict_sel_col)
            df_receipt = df_receipt.loc[df_receipt['Product_Code'].str.startswith('DRK')]
            
            df_receipt['Topping'] = df_receipt['Topping'].replace({np.nan: None})
            df_receipt['Payment_Time'] = pd.to_datetime(df_receipt['Payment_Time'], format="%Y-%m-%d %H:%M:%S")
            df_receipt['Order_Day'] = df_receipt['Order_Day'].astype(str)
            df_receipt['Amount'] = df_receipt['Amount'].astype(str).str.replace(',', '', regex=False).astype(float)
            df_receipt['Location'] = df_receipt['Location'].replace({'Haylà cafe': 'SGN', 'Haylà. express': 'NTR'})
            
            df_receipt['Payment_Method'] = df_receipt['Payment_Method'].replace({'Tiền mặt': 'Cash', 'Chuyển khoản': 'Tranfer'})
            df_receipt.loc[df_receipt.eval("Payment_Method.str.contains('Chuyển khoản: 0')"), 'Payment_Method'] = 'Cash'
            df_receipt.loc[df_receipt.eval("Payment_Method.str.contains('Tiền mặt: 0')"), 'Payment_Method'] = 'Tranfer'

            df_receipt['Size'] = df_receipt['Size'].str.replace('Size ', 'Size_').replace('ly', 'Size_M')

            lst_documents = list()
            for (loc, day, code), group in df_receipt.groupby(['Location', 'Order_Day', 'Order_Code']):
                
                ts: pd.Timestamp = group['Payment_Time'].iloc[0]
                payment_time = ts.to_pydatetime()
                                
                data = {
                    'Location': loc,
                    'Order_Day': day,
                    'Order_Code': code,
                    
                    'Payment_Time': payment_time,
                    'Payment_Method': group['Payment_Method'].iloc[0],
                    'Amount': float(group['Amount'].sum()),
                    
                    'Items': group[['Product_Code', 'Quantity', 'Size', 'Topping']].to_dict(orient='records')
                }

                receipt_data = ReceiptUpload(**data)
                lst_documents.append(receipt_data)
        
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Could not parse Excel: {e}")


        return lst_documents
    


    async def upload_receipts(self, upload_file: UploadFile) -> dict:
        
        try:
            lst_documents = await self.convert_receipt_file_to_dataframe(upload_file=upload_file)
            docs = [d.model_dump(by_alias=True, exclude_none=True) for d in lst_documents]

            ops = list()
            for doc in docs:

                # $setOnInsert ensures we only insert when there is no match
                ops.append(
                    UpdateOne(
                        # Filter
                        {
                            'Location': doc['Location'],
                            'Order_Day': doc['Order_Day'],
                            'Order_Code': doc['Order_Code'],
                        },
                        
                        # Insert values
                        {"$setOnInsert": doc},
                        upsert=True
                    )
                )

            if not ops:
                return {"inserted_count": 0}

            
            result = await self.clt_receipt.bulk_write(ops, ordered=False)

            return {
                'inserted_count': result.matched_count + result.upserted_count,
                'matched':  result.matched_count,
                'upserted': result.upserted_count
            }

            
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Upload receipts error: {e}")
        



    async def convert_receipt(self, receipt: dict, dict_drink: Dict[str, Drink], is_convert_pig_to_rig: bool, dict_pig: dict, current_user: UserPublic) -> Receipt:
        receipt_data = Receipt(**(jsonable_encoder(receipt, custom_encoder={ObjectId: str})))
        
        for item in receipt_data.Items:
            
            obj_drink = dict_drink.get(item.Product_Code)
            num_weight = obj_drink.Weighting.get(receipt_data.Location).get(item.Size)
            
            
            # Reference fields from Drink
            item.Group = obj_drink.Group
            item.Drink_Name = obj_drink.Drink_Name
            
            # Calculated fields based on Size
            item.Price_By_Size = getattr(getattr(obj_drink.Price, receipt_data.Location), item.Size)
            item.Total_Cost_By_Size = (obj_drink.Total_Cost * num_weight) + obj_drink.Extra_Cost.get(receipt_data.Location) 
            item.Margin_By_Size = (item.Price_By_Size - item.Total_Cost_By_Size) * 100 / item.Price_By_Size if item.Price_By_Size > 0 else 0
            
            
            for igr in obj_drink.Ingredients:
                
                if is_convert_pig_to_rig and igr.Ingredient_ID[:3] == 'PIG':
                    
                    # CONVERT PIG TO RIG
                    pig = dict_pig.get(igr.Ingredient_ID)
                    pig_qty_ratio = igr.Ingredient_Quanty / pig.Quanty
                    
                    for rig in pig.Raw_Ingredients:
                        
                        igr_data = DrinkIngredientItem(
                            Ingredient_ID=rig.Raw_Ingredient_ID,
                            Ingredient_Name=rig.Raw_Ingredient_Name,
                            Unit=rig.Unit,
                            Ingredient_Quanty=rig.Raw_Ingredient_Quanty * pig_qty_ratio * num_weight,
                            Cost_Per_Unit=rig.Cost_Per_Unit,
                            Total_Cost=rig.Total_Cost * pig_qty_ratio * num_weight,
                        )
                    
                        item.Ingredients_By_Size.append(igr_data)

                else:
                    
                    # GET BOTH PIG & RIG INFORMATION
                    igr_data = DrinkIngredientItem(
                        Ingredient_ID=igr.Ingredient_ID,
                        Ingredient_Name=igr.Ingredient_Name,
                        Unit=igr.Unit,
                        Ingredient_Quanty=igr.Ingredient_Quanty * num_weight,
                        Cost_Per_Unit=igr.Cost_Per_Unit,
                        Total_Cost=igr.Total_Cost * num_weight,
                    )
                    
                    item.Ingredients_By_Size.append(igr_data)
                    
                    
                
        
        return receipt_data



    async def retrieve_receipt(self, dict_filter_mongodb: dict, is_convert_pig_to_rig: bool, current_user: UserPublic) -> List[Receipt]:
        
        lst_receipt = list()
        
        # Get all drink to add information to Receipt Items Object
        dict_drink = await self.retrieve_drink(groupby='id', dict_filter_mongodb={}, current_user=current_user)
        dict_pig = dict()
        
        if is_convert_pig_to_rig:
            lst_pig = await self.retrieve_processed_ingredient(current_user)
            dict_pig = {item.Processed_Ingredient_ID: item for item in lst_pig}
        
        
        
        # async for receipt in self.clt_receipt.find({"Payment_Time": {"$gte": start, "$lt": end}}).sort({'Payment_Time': -1}):
        async for receipt in self.clt_receipt.find(dict_filter_mongodb).sort({'Payment_Time': -1}):
            receipt_data = await self.convert_receipt(receipt=receipt, dict_drink=dict_drink, is_convert_pig_to_rig=is_convert_pig_to_rig, dict_pig=dict_pig, current_user=current_user)
            lst_receipt.append(receipt_data)

        
        
        return lst_receipt
        
    
    
    
    # STOCK HERE START --------------------------------------------------------------------------------------------------------------------------------------------------------
    async def convert_stock(self, stock_item: dict) -> StockItem:
        
        stock_item_data = StockItem(**(jsonable_encoder(stock_item, custom_encoder={ObjectId: str})))

        rig = await self.clt_raw_ingredient.find_one({'Raw_Ingredient_ID': {'$exists': True, '$eq': stock_item_data.Raw_Ingredient_ID}})
        rig_data = jsonable_encoder(rig, custom_encoder={ObjectId: str})

        # Reference fields
        stock_item_data.Raw_Ingredient_Name = rig_data['Raw_Ingredient_Name']
        stock_item_data.Quanty = rig_data['Quanty']
        stock_item_data.Unit = rig_data['Unit']

        return stock_item_data



    async def retrieve_stock_items(self, dict_filter_mongodb: dict, current_user: UserPublic) -> list[StockItem]:
        
        LOCAL_TZ = ZoneInfo("Asia/Ho_Chi_Minh")
        
        def utc_to_local(dt_utc: datetime) -> datetime:
            # if it's naive but represents UTC, attach UTC first
            if dt_utc.tzinfo is None:
                dt_utc = dt_utc.replace(tzinfo=timezone.utc)
                
            # convert to local zone
            return dt_utc.astimezone(LOCAL_TZ)
        
        
        
        lst_stock = list()

        dict_filter = dict_filter_mongodb.copy() if dict_filter_mongodb else dict()
        
        dict_filter.update({'Raw_Ingredient_ID': {'$exists': True, '$ne': None}})
        
        if current_user.role.lower() not in ['admin']:
            
            since = datetime.now() - timedelta(days=7)
            dict_filter.update({
                'DateTime': {'$gte': since},
                'email': current_user.email
            })
            
        async for item in self.clt_stock.find(dict_filter).sort({'DateTime': -1}):
            
            item_data = await self.convert_stock(item)
            item_data.DateTime = utc_to_local(item_data.DateTime)
            
            lst_stock.append(item_data)

        return lst_stock
    
    
    
    async def insert_stock_items(self, lst_item: list[StockItemInsert], current_user: UserPublic) -> list[StockItem]:
        
        try:
            lst_stock_item_dump = list()
            
            for i in lst_item:
                i.email = current_user.email
                i.DateTime = datetime.now()
                lst_stock_item_dump.append(i.model_dump(by_alias=True, exclude_none=True))

            result = await self.clt_stock.insert_many(lst_stock_item_dump)

            
            
        
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Could not insert stock item(s): {e}")


        lst_stock_item = list()
        
        async for item in self.clt_stock.find(
                {
                    "_id": {"$in": result.inserted_ids},
                    "email": current_user.email
                }, 
            ).sort({'DateTime': -1}):
            
            item_data = await self.convert_stock(item)
            lst_stock_item.append(item_data)
        
        
        # # send mail
        # await mailer.send_email()
        
        
        return lst_stock_item
    
    
    
    async def delete_stock_items(self, lst_id: DeleteStockItems, current_user: UserPublic) -> list[StockItem]:
        
        try:
            
            obj_ids = [ObjectId(x) for x in lst_id.ids]
            
            dict_del_query = {"_id": {"$in": obj_ids}}
            
            
            if current_user.role.lower() not in ['admin']:
                dict_del_query.update({'email': current_user.email})
            
            result = await self.clt_stock.delete_many(dict_del_query)
            
            if result.deleted_count == 0:
                raise HTTPException(status_code=400, detail=f"Could not find item(s) to delete.")
            
        
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Could not delete stock item(s): {e}")


        
        lst_stock_item = await self.retrieve_stock_items(dict_filter_mongodb={}, current_user=current_user)
        
        return lst_stock_item
    
    
    
    async def summary_stock(self, obj_stock_summary_filter: SummaryStockFilter, current_user: UserPublic) -> dict:
        
        # Here: need to check date between last and nearly latest check date
        since = datetime.now() - timedelta(days=14)
        dict_filter_mongodb = obj_stock_summary_filter.model_dump(mode='json') | {'DateTime': {'$gte': since}}
        
        lst_stock = await self.retrieve_stock_items(dict_filter_mongodb=dict_filter_mongodb, current_user=current_user)
        
        df_data = pd.DataFrame([i.model_dump() for i in lst_stock])
        df_data['DateTime'] = df_data['DateTime'].dt.normalize()
        
        lst_latest2_dates = (
            pd.to_datetime(df_data.loc[df_data['Method'].str.lower().eq('check'), 'DateTime'])
            .dropna()
            .drop_duplicates()
            .nlargest(2)
            .sort_values(ascending=True)
            .tolist()
        )
        
        df_data = df_data.query("DateTime.isin(@lst_latest2_dates)")
        df_data['Qty_Total'] = df_data[['Qty_Instock', 'Qty_Outstock']].sum(axis=1)
        
        df_1st = df_data.query("DateTime < @lst_latest2_dates[-1]")        
        df_2nd = df_data.query("DateTime == @lst_latest2_dates[-1] & Method == 'check'")        
        
        df_1st_pivot = df_1st.pivot_table(
            columns=['Method'],
            values=['Qty_Total'],
            aggfunc=['sum'],
            index=['Raw_Ingredient_ID', 'Raw_Ingredient_Name', 'Location'],
            fill_value=0
        )
        
        flat_index = df_1st_pivot.columns.to_flat_index()
        df_1st_pivot.columns = flat_index.map(lambda t: t[-1])
        df_1st_pivot = df_1st_pivot.rename(columns={'check': lst_latest2_dates[0].strftime("%d/%m/%y")})
        
        
        if 'add' not in df_1st_pivot.columns:
            df_1st_pivot['add'] = 0 
        
        elif 'get' not in df_1st_pivot.columns:
            df_1st_pivot['get'] = 0
        
        
        df_1st_pivot['get'] = df_1st_pivot['get'].apply(lambda x: x * -1)
        
        
        df_2nd_pivot = df_2nd.pivot_table(
            columns=['Method'],
            values=['Qty_Total'],
            aggfunc=['sum'],
            index=['Raw_Ingredient_ID', 'Raw_Ingredient_Name', 'Location'],
            fill_value=0
        )
        
        flat_index = df_2nd_pivot.columns.to_flat_index()
        df_2nd_pivot.columns = flat_index.map(lambda t: t[-1])
        df_1st_pivot = df_1st_pivot.rename(columns={'check': lst_latest2_dates[-1]})
        
        a = 1
        
        
        
        
        
        
        
        # df_pivot = df_pivot.reset_index(drop=False)
        # df_pivot['remain'] = df_pivot['add'] - df_pivot['get']
        
        
        # df_pivot = df_pivot.sort_values(by=['remain'], ascending=[True])
        
        
        # tbl_html = df_pivot.to_html(
        #     table_id='dt-stock-summary', 
        #     columns=df_pivot.columns.tolist(),
        #     index=False, 
        #     index_names=False, 
        #     float_format="{:,.1f}".format,
        #     justify='left',
        #     classes='table table-hover table-bordered table-sm align-middle',  # mobile-cards
        # )
        
        return {
            'lst_latest2_dates': lst_latest2_dates,
            # 'dt_summary_stock': tbl_html
        }
        

    
    # STOCK HERE END --------------------------------------------------------------------------------------------------------------------------------------------------------
    
    
    
    