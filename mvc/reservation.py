from pydantic import BaseModel, Field, field_validator, model_validator, computed_field, EmailStr
from pydantic.functional_validators import BeforeValidator
from pydantic import TypeAdapter
from pydantic_core import PydanticCustomError
from typing import Optional, Literal, Union, Dict, List, Annotated
from bson import ObjectId
from pymongo import ReturnDocument, UpdateOne
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from fastapi import HTTPException, UploadFile
from fastapi.encoders import jsonable_encoder

from mvc.database import mongo_db
from mvc.users import UserPublic






# ---- ObjectId support (Pydantic v2) ----
def _validate_object_id(v) -> ObjectId:
    if isinstance(v, ObjectId):
        return v
    if isinstance(v, str):
        try:
            return ObjectId(v)
        except Exception:
            pass
    raise PydanticCustomError('objectid', 'Invalid ObjectId')

PyObjectId = Annotated[ObjectId, BeforeValidator(_validate_object_id)]



# ---- Shared enum for venue ----
VENUE = Literal[
    'Room 1',
    'Room 2',
    'Room 1 & 2',
    'Backroom',
    'Window table',
    'Sofa',
    'Anywhere'
]

STATUS = Literal[
    'Booking',
    'Arrived',
    'Leaved',
    'Cancel'
]

class _ReservationBase(BaseModel):
    name: Annotated[str, Field(min_length=2)]
    people: Annotated[int, Field(ge=1, le=30)]
    venue: VENUE
    allDay: Annotated[bool, Field(default=False)]
    
    # allow None in typing to match db rule; we enforce logic in validator
    start: Optional[datetime] = None
    end: Optional[datetime] = None
    
    status: STATUS
    
    desc: Annotated[str, Field(min_length=0, default="")]
    inputer: Annotated[str, Field(min_length=2)]

    
    # # Make sure "Z" (UTC) is parsed even in strict environments
    # @field_validator("start", "end", mode="before")
    # @classmethod
    # def _parse_z_datetime(cls, v):
    #     if isinstance(v, str) and v.endswith("Z"):
    #         # fromisoformat doesn't like 'Z' => replace with '+00:00'
    #         return datetime.fromisoformat(v.replace("Z", "+00:00"))
    #     return v
    
    
    
    @model_validator(mode="after")
    def _check_all_day_and_times(self):
        """
        - If allDay == True: start == None and end == None
        - If allDay == False: start != None and end != None and start < end
        """
        if self.allDay:
            if self.start is not None or self.end is not None:
                raise ValueError("For all-day events, start and end must be null.")
       
        else:
            if self.start is None or self.end is None:
                raise ValueError("For timed events, start and end must be provided.")
            
            if not (self.start < self.end):
                raise ValueError("For timed events, start must be earlier than end.")
        
        return self

    
    
    model_config = dict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={
            ObjectId: lambda oid: str(oid),
            # datetime: lambda dt: dt.strftime("%d/%m/%y %H:%M"),
            # datetime: lambda dt: dt.isoformat(),
        }
    )


class ReservationAdd(_ReservationBase):
    """
    Use for inserts when MongoDB will assign _id (or you set it client-side).
    """
    pass


class ReservationDB(_ReservationBase):
    """
    Use for documents read from / written to MongoDB (includes _id).
    """
    id: Annotated[PyObjectId, Field(alias="_id")]

    
    


class Reservation:

    def __init__(self):
        self.is_local = mongo_db.is_local
        
        self.clt_reservation = mongo_db.hayladb['reservation']


    
    
    
    
    async def retrieve_reservation(self, current_user: UserPublic, json_dumps: bool) -> list[ReservationDB]:
        
        today = datetime.now()
        month_start = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        dict_db_filter = {
            'allDay': False,
            'start': {"$gte": month_start}
        }
        
        HCM = ZoneInfo("Asia/Ho_Chi_Minh")
        
        obj_reservation = list()
        
        async for event in self.clt_reservation.find(dict_db_filter).sort({'start': 1}):
            
            event_data = ReservationDB(**(jsonable_encoder(event, custom_encoder={ObjectId: str})))
            event_data.start = event_data.start.replace(tzinfo=timezone.utc).astimezone(HCM)
            event_data.end = event_data.end.replace(tzinfo=timezone.utc).astimezone(HCM)
            
            obj_reservation.append(event_data.model_dump(mode='json') if json_dumps else event_data)
            
        
        return obj_reservation
    
    
    
    
    async def add_reservation(self, obj_reservation: ReservationAdd, current_user: UserPublic) -> ReservationAdd:
        
        try:
            obj_reservation.inputer = current_user.email
            obj_reservation_dump = obj_reservation.model_dump(by_alias=True, exclude_none=True)
            
            result = await self.clt_reservation.insert_one(obj_reservation_dump)
            
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Could not insert stock item(s): {e}")


        
        
        return obj_reservation

    
    
    
    
    
    
    # @staticmethod
    # async def convert_raw_ingredient(rig: dict, current_user: UserPublic) -> RawIngredient:
    #     rig_data = RawIngredient(**(jsonable_encoder(rig, custom_encoder={ObjectId: str})))

    #     if current_user.role.upper() not in ['ADMIN']:
    #         rig_data.Cost_Per_Unit = 0
        
    #     return rig_data



    # async def retrieve_raw_ingredient(self, current_user: UserPublic, is_group: bool = False, is_show_disable: bool = False) -> list[RawIngredient] | Dict[str, RawIngredient]:
        
    #     dict_db_filter = {'Raw_Ingredient_ID': {'$exists': True, '$ne': None}}
        
    #     if not is_show_disable:
    #         dict_db_filter |= {'Enable': True}
        
    #     if current_user.role.lower() not in ['admin']:
    #         dict_db_filter |= {'Location': {'$in': [current_user.location]}}
        
    #     obj_raw_ingredient = list() if not is_group else dict()

    #     async for rig in self.clt_raw_ingredient.find(dict_db_filter).sort({'Enable': -1, 'Group': 1, 'Raw_Ingredient_Name': 1}):
            
    #         rig_data = await self.convert_raw_ingredient(rig, current_user)
                
    #         if isinstance(obj_raw_ingredient, dict):
    #             obj_raw_ingredient.setdefault(rig_data.Group, []).append(rig_data)
            
    #         else:
    #             obj_raw_ingredient.append(rig_data)
            

    #     return obj_raw_ingredient




    # async def convert_processed_ingredient(self, pig: dict, current_user: UserPublic) -> ProcessedIngredient:
        
    #     pig_data = ProcessedIngredient(**(jsonable_encoder(pig, custom_encoder={ObjectId: str})))

    #     for item in pig_data.Raw_Ingredients:
    #         rig = await self.clt_raw_ingredient.find_one({'Raw_Ingredient_ID': {'$exists': True, '$eq': item.Raw_Ingredient_ID}})
    #         rig_data = await self.convert_raw_ingredient(jsonable_encoder(rig, custom_encoder={ObjectId: str}), current_user)
    #         item.add_data_ref_cal_fields(rig_data, pig_qty=pig_data.Quanty)  # item = RawIngredientItem

    #         # Calculated fields - pro igr
    #         pig_data.Total_Cost += item.Total_Cost
    #         pig_data.Cost_Per_Unit = pig_data.Total_Cost / pig_data.Quanty

    #     return pig_data



    # async def retrieve_processed_ingredient(self, current_user: UserPublic) -> list[ProcessedIngredient]:

    #     lst_processed_ingredient = list()

    #     async for pig in self.clt_processed_ingredient.find({'Processed_Ingredient_ID': {'$exists': True, '$ne': None}}):
    #         pig_data = await self.convert_processed_ingredient(pig, current_user)
    #         lst_processed_ingredient.append(pig_data)

    #     return lst_processed_ingredient



    # async def convert_drink(self, drk: dict, current_user: UserPublic) -> Drink:

    #     drk_data = Drink(**(jsonable_encoder(drk, custom_encoder={ObjectId: str})))
        
    #     for item in drk_data.Ingredients:

    #         if str(item.Ingredient_ID)[:3].upper() == 'RIG':

    #             drk_igr = await self.clt_raw_ingredient.find_one({'Raw_Ingredient_ID': {'$exists': True, '$eq': item.Ingredient_ID}})
    #             drk_igr_data = await self.convert_raw_ingredient(jsonable_encoder(drk_igr, custom_encoder={ObjectId: str}), current_user)

    #             item.add_data_ref_cal_fields(drk_igr_data)

    #         else:

    #             drk_igr = await self.clt_processed_ingredient.find_one({'Processed_Ingredient_ID': {'$exists': True, '$eq': item.Ingredient_ID}})
    #             drk_igr_data = await self.convert_processed_ingredient(drk_igr, current_user)

    #             item.add_data_ref_cal_fields(drk_igr_data)


    #         drk_data.Total_Cost += item.Total_Cost
            
    #         for loc in drk_data.Location:
                
    #             if loc == 'SGN':
    #                 continue

    #             obj_price_loc = getattr(drk_data.Price, loc)
    #             dict_weighting: dict = drk_data.Weighting.get(loc)
                
    #             if drk_data.Drink_ID in ['DRK31', 'DRK32']:
    #                 drk_data.Extra_Cost[loc] = 4000
                
    #             if obj_price_loc.Size_S > 0:
    #                 dict_weighting['Size_S'] = 1
    #                 dict_weighting['Size_M'] = 1.5
    #                 dict_weighting['Size_L'] = 1.5 * 1.5
                
    #             elif obj_price_loc.Size_S == 0 and obj_price_loc.Size_M > 0:
    #                 dict_weighting['Size_S'] = 0
    #                 dict_weighting['Size_M'] = 1
    #                 dict_weighting['Size_L'] = 1.5


    #     return drk_data



    # async def retrieve_drink(self, groupby: Literal['GROUP', 'ID', None], dict_filter_mongodb: dict, current_user: UserPublic) -> Dict[str, list[Drink] | Drink] | list[Drink]:

    #     if groupby is None:
    #         drinks = list()
    #     else:
    #         drinks = dict()

    #     async for drk in self.clt_drink.find({
    #         'Drink_ID': {'$exists': True, '$ne': None},
    #         'Enable': True
    #     } | dict_filter_mongodb).sort({'Group': 1, 'Location': -1, 'Drink_Name': 1}):

    #         drk_data = await self.convert_drink(drk, current_user)

    #         if groupby.upper() == 'GROUP':
    #             group_key = drk_data.Group
    #             drinks.setdefault(group_key, []).append(drk_data)
            
    #         elif groupby.upper() == 'ID':
    #             group_key = drk_data.Drink_ID
    #             drinks.update({group_key: drk_data})
            
    #         else:
    #             drinks.append(drk_data)
                
        
    #     return drinks



    # async def update_drink(self, oid: str, obj_drink: DrinkUpdate) -> DrinkUpdate:

    #     try:
    #         oid = ObjectId(oid)
    #     except Exception as e:
    #         raise HTTPException(status_code=400, detail=f'Invalid drink_oid: {e}')

    #     update_data = {k: v for k, v in obj_drink.model_dump().items() if v is not None}

    #     if not update_data:
    #         raise HTTPException(status_code=400, detail='No fields to update')

    #     updated_drink = await self.clt_drink.find_one_and_update(
    #         {'_id': oid},
    #         {'$set': update_data},
    #         return_document=ReturnDocument.AFTER,
    #         # projection={'hashed_password': 0}
    #     )

    #     if not updated_drink:
    #         raise HTTPException(status_code=404, detail='Drink not found')

    #     updated_drink = DrinkUpdate(**updated_drink)

    #     return updated_drink


    
    # # Here
    # async def retrieve_drink_v2(self, groupby: Literal['GROUP', 'ID', None], dict_filter_mongodb: dict, current_user: UserPublic) -> Dict[str, list[DrinkV2] | DrinkV2] | list[DrinkV2]:
        
    #     drinks = list() if (groupby is None) else dict()
        
    #     dict_full_igr = await self.get_full_ingredients(output_type='DICT', current_user=current_user)
        
    #     async for drk in self.clt_drink_v2.find({
    #         'Drink_ID': {'$exists': True, '$ne': None},
    #         'Enable': True
    #     } | dict_filter_mongodb).sort({'Group': 1, 'Location': -1, 'Drink_ID': 1}):
            
    #         drk_data = DrinkV2(**(jsonable_encoder(drk, custom_encoder={ObjectId: str})))
    #         drk_data.recipe_update(dict_full_igr)
            
    #         if groupby.upper() == 'GROUP':
    #             group_key = drk_data.Group
    #             drinks.setdefault(group_key, []).append(drk_data)
            
    #         elif groupby.upper() == 'ID':
    #             group_key = drk_data.Drink_ID
    #             drinks.update({group_key: drk_data})
            
    #         else:
    #             drinks.append(drk_data)
                
        
    #     return drinks

    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    

    # async def retrieve_fixed_cost(self) -> list[FixedCost]:

    #     lst_fixed_cost = list()

    #     async for fix in self.clt_fixed_cost.find({'Fixed_Cost_ID': {'$exists': True, '$ne': None}}):
    #         lst_fixed_cost.append(FixedCost(**(jsonable_encoder(fix, custom_encoder={ObjectId: str}))))

    #     return lst_fixed_cost




    # async def convert_inventory(self, inv: dict) -> InventoryItem:
    #     inv_data = InventoryItem(**(jsonable_encoder(inv, custom_encoder={ObjectId: str})))

    #     rig = await self.clt_raw_ingredient.find_one({'Raw_Ingredient_ID': {'$exists': True, '$eq': inv_data.Raw_Ingredient_ID}})
    #     rig_data = jsonable_encoder(rig, custom_encoder={ObjectId: str})

    #     # Reference fields
    #     inv_data.Raw_Ingredient_Name = rig_data['Raw_Ingredient_Name']
    #     inv_data.Quanty = rig_data['Quanty']
    #     inv_data.Unit = rig_data['Unit']

    #     return inv_data



    # async def retrieve_inventory(self, dict_filter_mongodb: dict) -> list[InventoryItem]:
    #     lst_inventory = list()

    #     async for inv in self.clt_inventory.find({
    #             'Raw_Ingredient_ID': {'$exists': True, '$ne': None}
    #         } | dict_filter_mongodb).sort({'DateTime': -1}):
            
    #         inv_data = await self.convert_inventory(inv)
    #         lst_inventory.append(inv_data)

    #     return lst_inventory




    # @staticmethod
    # def analyze_inventory(lst_inventory: list[InventoryItem], is_export_df: bool = False) -> list[dict] | pd.DataFrame:

    #     df_summary = pd.DataFrame([i.model_dump() for i in lst_inventory])

    #     df_total_qty: pd.DataFrame = (
    #         df_summary
    #         .groupby(['Raw_Ingredient_ID', 'Raw_Ingredient_Name', 'Location', 'Quanty', 'Unit', 'Action'])['Qty']
    #         .sum()
    #         .reset_index(name="TotalQty")
    #     ).pivot_table(
    #         columns=['Action'],
    #         values=['TotalQty'],
    #         aggfunc=['sum'],
    #         index=['Raw_Ingredient_ID', 'Raw_Ingredient_Name', 'Location', 'Quanty', 'Unit'],
    #         fill_value=0
    #     )
        
    #     flat_index = df_total_qty.columns.to_flat_index()
    #     df_total_qty.columns = flat_index.map(lambda t: t[-1])
    #     df_total_qty = df_total_qty.reset_index(drop=False)
    #     df_total_qty['remain'] = df_total_qty['add'] - df_total_qty['get']
    #     df_total_qty = df_total_qty.sort_values(by=['remain'], ascending=[True])

    #     return df_total_qty.to_dict(orient='records') if not is_export_df else df_total_qty


    
    # async def add_inventory_items(self, lst_inv_item: list[InventoryItemInsert], current_user: UserPublic) -> list[InventoryItem]:
        
    #     try:
    #         lst_inv_item_dump = list()
    #         for i in lst_inv_item:
    #             i.email = current_user.email
    #             i.DateTime = datetime.now()
    #             lst_inv_item_dump.append(i.model_dump(by_alias=True, exclude_none=True))

    #         result = await self.clt_inventory.insert_many(lst_inv_item_dump)

    #     except Exception as e:
    #         raise HTTPException(status_code=400, detail=f"Could not add inventory item(s): {e}")


    #     lst_inventory = list()
    #     async for inv in self.clt_inventory.find({"_id": {"$in": result.inserted_ids}}).sort({'DateTime': -1}):
    #         inv_data = await self.convert_inventory(inv)
    #         lst_inventory.append(inv_data)

    #     return lst_inventory

    


    # async def get_full_ingredients(self, current_user: UserPublic, output_type: str = 'LST') -> list[IngredientForFil] | dict[str, IngredientForFil]:
        
    #     full_igrs = list() if output_type.upper() == 'LST' else dict()
        
    #     lst_full_pig = await self.retrieve_processed_ingredient(current_user)
    #     lst_full_rig = await self.retrieve_raw_ingredient(current_user)

    #     for pig in lst_full_pig:
            
    #         obj_igr = IngredientForFil(ID=pig.Processed_Ingredient_ID, Name=pig.Processed_Ingredient_Name, Unit=pig.Unit, Cost_Per_Unit=pig.Cost_Per_Unit)
            
    #         if isinstance(full_igrs, list):
    #             full_igrs.append(obj_igr)

    #         else:
    #             full_igrs.update({obj_igr.ID: obj_igr})
            
            
    #     for rig in lst_full_rig:
            
    #         obj_igr = IngredientForFil(ID=rig.Raw_Ingredient_ID, Name=rig.Raw_Ingredient_Name, Unit=rig.Unit, Cost_Per_Unit=rig.Cost_Per_Unit)
            
    #         if isinstance(full_igrs, list):
    #             full_igrs.append(obj_igr)
            
    #         else:
    #             full_igrs.update({obj_igr.ID: obj_igr})
        
    #     return full_igrs



    # async def convert_receipt_file_to_dataframe(self, upload_file: UploadFile) -> List[ReceiptUpload]:

    #     try:
    #         df_receipt = pd.read_excel(upload_file.file, header=7)

    #         dict_sel_col = {
    #             'Shop name': 'Location',
    #             'Day': 'Order_Day',
    #             'Order code': 'Order_Code',
                
    #             'Payment time': 'Payment_Time',
    #             'Product code': 'Product_Code',
    #             'Quantity': 'Quantity',
    #             'Unit': 'Size',
    #             'Topping': 'Topping',
    #             'Amount after invoice discount': 'Amount',
    #             'Payment method': 'Payment_Method',
    #         }

    #         df_receipt: pd.DataFrame = df_receipt.loc[df_receipt.eval("~`Payment time`.isnull() & Status != 'Hủy'"), dict_sel_col.keys()]
    #         df_receipt = df_receipt.rename(columns=dict_sel_col)
    #         df_receipt = df_receipt.loc[df_receipt['Product_Code'].str.startswith('DRK')]
            
    #         df_receipt['Topping'] = df_receipt['Topping'].replace({np.nan: None})
    #         df_receipt['Payment_Time'] = pd.to_datetime(df_receipt['Payment_Time'], format="%Y-%m-%d %H:%M:%S")
    #         df_receipt['Order_Day'] = df_receipt['Order_Day'].astype(str)
    #         df_receipt['Amount'] = df_receipt['Amount'].astype(str).str.replace(',', '', regex=False).astype(float)
    #         df_receipt['Location'] = df_receipt['Location'].replace({'Haylà cafe': 'SGN', 'Haylà. express': 'NTR'})
            
    #         df_receipt['Payment_Method'] = df_receipt['Payment_Method'].replace({'Tiền mặt': 'Cash', 'Chuyển khoản': 'Tranfer'})
    #         df_receipt.loc[df_receipt.eval("Payment_Method.str.contains('Chuyển khoản: 0')"), 'Payment_Method'] = 'Cash'
    #         df_receipt.loc[df_receipt.eval("Payment_Method.str.contains('Tiền mặt: 0')"), 'Payment_Method'] = 'Tranfer'

    #         df_receipt['Size'] = df_receipt['Size'].str.replace('Size ', 'Size_').replace('ly', 'Size_M')

    #         lst_documents = list()
    #         for (loc, day, code), group in df_receipt.groupby(['Location', 'Order_Day', 'Order_Code']):
                
    #             ts: pd.Timestamp = group['Payment_Time'].iloc[0]
    #             payment_time = ts.to_pydatetime()
                                
    #             data = {
    #                 'Location': loc,
    #                 'Order_Day': day,
    #                 'Order_Code': code,
                    
    #                 'Payment_Time': payment_time,
    #                 'Payment_Method': group['Payment_Method'].iloc[0],
    #                 'Amount': float(group['Amount'].sum()),
                    
    #                 'Items': group[['Product_Code', 'Quantity', 'Size', 'Topping']].to_dict(orient='records')
    #             }

    #             receipt_data = ReceiptUpload(**data)
    #             lst_documents.append(receipt_data)
        
    #     except Exception as e:
    #         raise HTTPException(status_code=400, detail=f"Could not parse Excel: {e}")


    #     return lst_documents
    


    # async def upload_receipts(self, upload_file: UploadFile) -> dict:
        
    #     try:
    #         lst_documents = await self.convert_receipt_file_to_dataframe(upload_file=upload_file)
    #         docs = [d.model_dump(by_alias=True, exclude_none=True) for d in lst_documents]

    #         ops = list()
    #         for doc in docs:

    #             # $setOnInsert ensures we only insert when there is no match
    #             ops.append(
    #                 UpdateOne(
    #                     # Filter
    #                     {
    #                         'Location': doc['Location'],
    #                         'Order_Day': doc['Order_Day'],
    #                         'Order_Code': doc['Order_Code'],
    #                     },
                        
    #                     # Insert values
    #                     {"$setOnInsert": doc},
    #                     upsert=True
    #                 )
    #             )

    #         if not ops:
    #             return {"inserted_count": 0}

            
    #         result = await self.clt_receipt.bulk_write(ops, ordered=False)

    #         return {
    #             'inserted_count': result.matched_count + result.upserted_count,
    #             'matched':  result.matched_count,
    #             'upserted': result.upserted_count
    #         }

            
    #     except Exception as e:
    #         raise HTTPException(status_code=400, detail=f"Upload receipts error: {e}")
        



    # async def convert_receipt(self, receipt: dict, dict_drink: Dict[str, Drink], is_convert_pig_to_rig: bool, dict_pig: dict, current_user: UserPublic) -> Receipt:
    #     receipt_data = Receipt(**(jsonable_encoder(receipt, custom_encoder={ObjectId: str})))
        
    #     for item in receipt_data.Items:
            
    #         obj_drink = dict_drink.get(item.Product_Code)
    #         num_weight = obj_drink.Weighting.get(receipt_data.Location).get(item.Size)
            
            
    #         # Reference fields from Drink
    #         item.Group = obj_drink.Group
    #         item.Drink_Name = obj_drink.Drink_Name
            
    #         # Calculated fields based on Size
    #         item.Price_By_Size = getattr(getattr(obj_drink.Price, receipt_data.Location), item.Size)
    #         item.Total_Cost_By_Size = (obj_drink.Total_Cost * num_weight) + obj_drink.Extra_Cost.get(receipt_data.Location) 
    #         item.Margin_By_Size = (item.Price_By_Size - item.Total_Cost_By_Size) * 100 / item.Price_By_Size if item.Price_By_Size > 0 else 0
            
            
    #         for igr in obj_drink.Ingredients:
                
    #             if is_convert_pig_to_rig and igr.Ingredient_ID[:3] == 'PIG':
                    
    #                 # CONVERT PIG TO RIG
    #                 pig = dict_pig.get(igr.Ingredient_ID)
    #                 pig_qty_ratio = igr.Ingredient_Quanty / pig.Quanty
                    
    #                 for rig in pig.Raw_Ingredients:
                        
    #                     igr_data = DrinkIngredientItem(
    #                         Ingredient_ID=rig.Raw_Ingredient_ID,
    #                         Ingredient_Name=rig.Raw_Ingredient_Name,
    #                         Unit=rig.Unit,
    #                         Ingredient_Quanty=rig.Raw_Ingredient_Quanty * pig_qty_ratio * num_weight,
    #                         Cost_Per_Unit=rig.Cost_Per_Unit,
    #                         Total_Cost=rig.Total_Cost * pig_qty_ratio * num_weight,
    #                     )
                    
    #                     item.Ingredients_By_Size.append(igr_data)

    #             else:
                    
    #                 # GET BOTH PIG & RIG INFORMATION
    #                 igr_data = DrinkIngredientItem(
    #                     Ingredient_ID=igr.Ingredient_ID,
    #                     Ingredient_Name=igr.Ingredient_Name,
    #                     Unit=igr.Unit,
    #                     Ingredient_Quanty=igr.Ingredient_Quanty * num_weight,
    #                     Cost_Per_Unit=igr.Cost_Per_Unit,
    #                     Total_Cost=igr.Total_Cost * num_weight,
    #                 )
                    
    #                 item.Ingredients_By_Size.append(igr_data)
                    
                    
                
        
    #     return receipt_data



    # async def retrieve_receipt(self, dict_filter_mongodb: dict, is_convert_pig_to_rig: bool, current_user: UserPublic) -> List[Receipt]:
        
    #     lst_receipt = list()
        
    #     # Get all drink to add information to Receipt Items Object
    #     dict_drink = await self.retrieve_drink(groupby='id', dict_filter_mongodb={}, current_user=current_user)
    #     dict_pig = dict()
        
    #     if is_convert_pig_to_rig:
    #         lst_pig = await self.retrieve_processed_ingredient(current_user)
    #         dict_pig = {item.Processed_Ingredient_ID: item for item in lst_pig}
        
        
        
    #     # async for receipt in self.clt_receipt.find({"Payment_Time": {"$gte": start, "$lt": end}}).sort({'Payment_Time': -1}):
    #     async for receipt in self.clt_receipt.find(dict_filter_mongodb).sort({'Payment_Time': -1}):
    #         receipt_data = await self.convert_receipt(receipt=receipt, dict_drink=dict_drink, is_convert_pig_to_rig=is_convert_pig_to_rig, dict_pig=dict_pig, current_user=current_user)
    #         lst_receipt.append(receipt_data)

        
        
    #     return lst_receipt
        
    
    
    
    # # STOCK HERE START --------------------------------------------------------------------------------------------------------------------------------------------------------
    # async def convert_stock(self, stock_item: dict) -> StockItem:
        
    #     stock_item_data = StockItem(**(jsonable_encoder(stock_item, custom_encoder={ObjectId: str})))

    #     rig = await self.clt_raw_ingredient.find_one({'Raw_Ingredient_ID': {'$exists': True, '$eq': stock_item_data.Raw_Ingredient_ID}})
    #     rig_data = jsonable_encoder(rig, custom_encoder={ObjectId: str})

    #     # Reference fields
    #     stock_item_data.Raw_Ingredient_Name = rig_data['Raw_Ingredient_Name']
    #     stock_item_data.Quanty = rig_data['Quanty']
    #     stock_item_data.Unit = rig_data['Unit']

    #     return stock_item_data



    # async def retrieve_stock_items(self, dict_filter_mongodb: dict, current_user: UserPublic) -> list[StockItem]:
        
    #     LOCAL_TZ = ZoneInfo("Asia/Ho_Chi_Minh")
        
    #     def utc_to_local(dt_utc: datetime) -> datetime:
    #         # if it's naive but represents UTC, attach UTC first
    #         if dt_utc.tzinfo is None:
    #             dt_utc = dt_utc.replace(tzinfo=timezone.utc)
                
    #         # convert to local zone
    #         return dt_utc.astimezone(LOCAL_TZ)
        
        
        
    #     lst_stock = list()

    #     dict_filter = dict_filter_mongodb.copy() if dict_filter_mongodb else dict()
        
    #     dict_filter.update({'Raw_Ingredient_ID': {'$exists': True, '$ne': None}})
        
    #     if current_user.role.lower() not in ['admin']:
            
    #         since = datetime.now() - timedelta(days=7)
    #         dict_filter.update({
    #             'DateTime': {'$gte': since},
    #             'email': current_user.email
    #         })
            
    #     async for item in self.clt_stock.find(dict_filter).sort({'DateTime': -1}):
            
    #         item_data = await self.convert_stock(item)
    #         item_data.DateTime = utc_to_local(item_data.DateTime)
            
    #         lst_stock.append(item_data)

    #     return lst_stock
    
    
    
    # async def insert_stock_items(self, lst_item: list[StockItemInsert], current_user: UserPublic) -> list[StockItem]:
        
    #     try:
    #         lst_stock_item_dump = list()
            
    #         for i in lst_item:
    #             i.email = current_user.email
    #             i.DateTime = datetime.now()
    #             lst_stock_item_dump.append(i.model_dump(by_alias=True, exclude_none=True))

    #         result = await self.clt_stock.insert_many(lst_stock_item_dump)

            
            
        
    #     except Exception as e:
    #         raise HTTPException(status_code=400, detail=f"Could not insert stock item(s): {e}")


    #     lst_stock_item = list()
        
    #     async for item in self.clt_stock.find(
    #             {
    #                 "_id": {"$in": result.inserted_ids},
    #                 "email": current_user.email
    #             }, 
    #         ).sort({'DateTime': -1}):
            
    #         item_data = await self.convert_stock(item)
    #         lst_stock_item.append(item_data)
        
        
    #     # # send mail
    #     # await mailer.send_email()
        
        
    #     return lst_stock_item
    
    
    
    # async def delete_stock_items(self, lst_id: DeleteStockItems, current_user: UserPublic) -> list[StockItem]:
        
    #     try:
            
    #         obj_ids = [ObjectId(x) for x in lst_id.ids]
            
    #         dict_del_query = {"_id": {"$in": obj_ids}}
            
            
    #         if current_user.role.lower() not in ['admin']:
    #             dict_del_query.update({'email': current_user.email})
            
    #         result = await self.clt_stock.delete_many(dict_del_query)
            
    #         if result.deleted_count == 0:
    #             raise HTTPException(status_code=400, detail=f"Could not find item(s) to delete.")
            
        
    #     except Exception as e:
    #         raise HTTPException(status_code=400, detail=f"Could not delete stock item(s): {e}")


        
    #     lst_stock_item = await self.retrieve_stock_items(dict_filter_mongodb={}, current_user=current_user)
        
    #     return lst_stock_item
    
    
    
    # async def summary_stock(self, obj_stock_summary_filter: SummaryStockFilter, current_user: UserPublic) -> dict:
        
    #     since = datetime.now() - timedelta(days=14)
    #     dict_filter_mongodb = obj_stock_summary_filter.model_dump(mode='json') | {'DateTime': {'$gte': since}}
        
    #     lst_stock = await self.retrieve_stock_items(dict_filter_mongodb=dict_filter_mongodb, current_user=current_user)
        
    #     df_data = pd.DataFrame([i.model_dump() for i in lst_stock])
        
    #     df_dates = (
    #         pd.to_datetime(df_data.loc[df_data['Method'].str.lower().eq('check'), 'DateTime'].dt.date)
    #         .dropna()
    #         .drop_duplicates()
    #         .nlargest(2)
    #         .sort_values(ascending=True)
    #         .reset_index(drop=True)
    #     )
        
    #     start_date = df_data.loc[df_data.eval(f"Method == 'check' & DateTime.dt.date == @df_dates.min().date()"), 'DateTime'].drop_duplicates().min()
    #     end_date = df_data.loc[df_data.eval(f"Method == 'check' & DateTime.dt.date == @df_dates.max().date()"), 'DateTime'].drop_duplicates().max()
        
    #     df_data = df_data.query("(Method == 'check' & DateTime.between(@start_date, @end_date.replace(hour=23, minute=59))) | (Method.isin(['get', 'add']) & DateTime.between(@start_date, @end_date))")
        
    #     df_data['DateTime'] = df_data['DateTime'].dt.normalize()
    #     df_data['Qty_Total'] = df_data[['Qty_Instock', 'Qty_Outstock']].sum(axis=1)
        
    #     df_data.loc[df_data.eval("Method == 'check' & DateTime == @start_date.replace(hour=0, minute=0, second=0, microsecond=0)"), 'Method'] = 'From'
    #     df_data.loc[df_data.eval("Method == 'check' & DateTime == @end_date.replace(hour=0, minute=0, second=0, microsecond=0)"), 'Method'] = 'To'
    #     df_data['Method'] = df_data['Method'].str.capitalize()
        
    #     df_pivot = df_data.pivot_table(
    #         columns=['Method'],
    #         values=['Qty_Total'],
    #         aggfunc=['sum'],
    #         index=['Raw_Ingredient_ID', 'Raw_Ingredient_Name', 'Location'],
    #         fill_value=0
    #     )
        
    #     flat_index = df_pivot.columns.to_flat_index()
    #     df_pivot.columns = flat_index.map(lambda t: t[-1])
        
        
    #     for col in ['Add', 'Get']:
    #         if col not in df_pivot.columns.to_list():
    #             df_pivot[col] = 0
            
        
    #     df_pivot['Remain'] = df_pivot['From'] + df_pivot['Add'] - df_pivot['Get'] 
    #     df_pivot['Gap'] = df_pivot['To'] - df_pivot['Remain']
    #     df_pivot['Status'] = df_pivot['Gap'].apply(lambda x: 'OK' if -1 <= x <= 1 else 'Error') 
        
    #     df_pivot = df_pivot.reindex(columns=['From', 'Add', 'Get', 'Remain', 'To', 'Gap', 'Status'])
    #     df_pivot = df_pivot.reset_index(drop=False)
        
    #     df_pivot = df_pivot.rename(columns={
    #         'From': f'From: {start_date.strftime("%d/%m/%y")}',
    #         'To': f'To: {end_date.strftime("%d/%m/%y")}'
    #     })
        
    #     tbl_html = df_pivot.to_html(
    #         table_id='dt-stock-summary',
    #         columns=df_pivot.columns.tolist(),
    #         index=False,
    #         index_names=False, 
    #         float_format="{:,.1f}".format,
    #         justify='left',
    #         classes='table table-hover table-bordered table-sm align-middle',  # mobile-cards 
    #     )
        
    #     # consider to convert df_pivot to model
        
    #     return {
    #         # 'lst_latest2_dates': lst_latest2_dates,
    #         'dt_summary_stock': tbl_html
    #     }
        
        
    
    # # STOCK HERE END --------------------------------------------------------------------------------------------------------------------------------------------------------
    
    
    
    