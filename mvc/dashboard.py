import pandas as pd
import numpy as np
from pydantic import BaseModel, Field, field_validator, model_validator, computed_field, EmailStr
from typing import Optional, Literal, Union, Dict, List, Annotated
from bson import ObjectId
from pymongo import ReturnDocument, UpdateOne
from datetime import datetime
from fastapi import HTTPException, UploadFile
from fastapi.encoders import jsonable_encoder


from mvc.users import UserPublic
from mvc.operation import Operation




class Dashboard(Operation):
    
    def __init__(self):
        super().__init__()
        self.df_receipt = pd.DataFrame()
        self.df_drink = pd.DataFrame()
        self.df_ingredient = pd.DataFrame()
        
        """
        need 3 dfs for dashboard ananlyzing:
            df by receipt
            df by drink
            df by ingredient (need convert pig to rig for calculating)
        """
        

    
    async def dashboard_analyze(self, dict_filter: dict, current_user: UserPublic) -> dict:
        
        lst_receipt = await self.retrieve_receipt(dict_filter=dict_filter, current_user=current_user)
        
        raw_receipt = list()
        
        for rec in lst_receipt:
            
            raw_receipt.append(rec.model_dump(exclude={'id', 'Order_Day', 'Order_Code', 'Items'}))
            
            # for item in rec.Items:
               
            #    a = item.model_dump() | {'Location': rec.Location, 'Payment_Time': rec.Payment_Time}
               
            #    raw.append(a) 
               
        
        self.df_receipt = pd.DataFrame(raw_receipt)
        self.df_receipt.to_csv('df_receipt.csv', encoding='utf-8')
        
        return {
            'revenue': self.df_receipt['Amount'].sum()
        }


