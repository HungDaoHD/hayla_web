import pandas as pd
import numpy as np
import traceback
from pydantic import BaseModel, Field, field_validator, model_validator, computed_field, EmailStr
from typing import Optional, Literal, Union, Dict, List, Annotated
from bson import ObjectId
from pymongo import ReturnDocument, UpdateOne
from datetime import datetime, timedelta
from fastapi import HTTPException, UploadFile
from fastapi.encoders import jsonable_encoder



from mvc.users import UserPublic
from mvc.operation import Operation



class DashboardFilterInput(BaseModel):
    Location: List[Literal["SGN", "NTR"]] = Field(min_length=1)
    Payment_Time: List[Annotated[str, Field(pattern=r"^\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])$", description="Date in YYYY-MM-DD format")]]



class DashboardFilterOutput(BaseModel):
    Location: List[Literal["SGN", "NTR"]] = Field(min_length=1)
    StartDate: Annotated[datetime, Field(default=None)]
    EndDate: Annotated[datetime, Field(default=None)]
    PrevStartDate: Annotated[datetime, Field(default=None)]
    PrevEndtDate: Annotated[datetime, Field(default=None)]
    DeltaDay: Annotated[timedelta, Field(default=None)]
    
    def to_mongodb_query(self) -> dict:
        dict_filter_mongodb = {"Location": {"$in": self.Location}}
        
        if self.StartDate and self.EndDate:
            dict_filter_mongodb.update({
                "$or": [
                    {
                        "Payment_Time": {
                            "$gte": self.PrevStartDate,
                            "$lte": self.PrevEndtDate,
                        }
                    },
                    {
                        "Payment_Time": {
                            "$gte": self.StartDate,
                            "$lte": self.EndDate,
                        }
                    },
                ],
            })
        
        return dict_filter_mongodb
        
        

class DashboardResult(BaseModel):
    Period: Annotated[str, Field(default="YYYY-MM-DD")]
    Revenue: Annotated[float, Field(default=0)]
    DirectCost: Annotated[float, Field(default=0)]
    FixedCost: Annotated[float, Field(default=0)]
    NetProfit: Annotated[float, Field(default=0)]



class AreaChart(BaseModel):
    Colors: list = Field(default=['#1890ff', '#13c2c2'])
    Series: list = Field(default=[
        {'name': 'Page Views', 'data': [31, 40, 28, 51, 42, 129, 100]},
        {'name': 'Sessions', 'data': [11, 32, 45, 32, 34, 52, 41]}
    ])
    Xaxis: dict = Field(default={'categories': ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']})
       
    




class DashboardAnalyze(BaseModel):
    Previous: DashboardResult
    Current: DashboardResult
    ChartRevDcost: AreaChart = Field(default_factory=AreaChart)
    HTML_RawIngredientUsage: str = Field(default='')
    HTML_DrinkSummary: str = Field(default='')
    




class Dashboard(Operation):
    
    def __init__(self):
        super().__init__()
        self.df_receipt = pd.DataFrame()
        self.df_drink = pd.DataFrame()
        self.df_ingredient = pd.DataFrame()
        self.df_fixed_cost = pd.DataFrame()
        self.df_inventory = pd.DataFrame()
    
    
    
    async def analyze_fixed_cost(self):
        
        lst_fixed_cost = await self.retrieve_fixed_cost()
        raw_fixed_cost = list()
        
        for fix in lst_fixed_cost:
            obj_fix = fix.model_dump(exclude={'id', 'Cost'})
            
            obj_fix.update({'SGN': fix.Cost.SGN, 'NTR': fix.Cost.NTR})
                
            raw_fixed_cost.append(obj_fix)
            
        
        self.df_fixed_cost = pd.DataFrame(raw_fixed_cost)

        print(f"Fixed cost to dataFrame completed")
        


    async def analyze_receipts_drinks_ingredients(self, dboard_filter_output: DashboardFilterOutput, current_user: UserPublic):
        
        lst_receipt = await self.retrieve_receipt(dict_filter_mongodb=dboard_filter_output.to_mongodb_query(), is_convert_pig_to_rig=True, current_user=current_user)
        
        raw_receipt = list()
        raw_dink = list()
        raw_igr = list()
        
        for rec in lst_receipt:
            
            raw_receipt.append(rec.model_dump(exclude={'id', 'Order_Day', 'Order_Code', 'Items'}))
            
            for item in rec.Items:
                drk = item.model_dump() | {'Location': rec.Location, 'Payment_Time': rec.Payment_Time}
                raw_dink.append(drk)
                
                for igr in item.Ingredients_By_Size:
                    igr_data = {
                        'Location': rec.Location, 
                        'Payment_Time': rec.Payment_Time,
                        'Quantity': item.Quantity,
                        # 'Product_Code': item.Product_Code,
                        # 'Size': item.Size,
                        # 'Drink_Name': item.Drink_Name,
                        # 'Total_Cost_By_Size': item.Total_Cost_By_Size
                    } | igr.model_dump()

                    raw_igr.append(igr_data)
                    
                
                
        self.df_receipt = pd.DataFrame(raw_receipt)
        self.df_receipt['Payment_Date'] = pd.to_datetime(self.df_receipt['Payment_Time'].dt.date)
        self.df_receipt['Payment_Period'] = self.df_receipt['Payment_Time'].apply(lambda x: 'Current' if x >= dboard_filter_output.StartDate else 'Previous')
        
        
        self.df_drink = pd.DataFrame(raw_dink)
        self.df_drink['Payment_Date'] = pd.to_datetime(self.df_drink['Payment_Time'].dt.date)
        self.df_drink['Payment_Period'] = self.df_drink['Payment_Time'].apply(lambda x: 'Current' if x >= dboard_filter_output.StartDate else 'Previous')
        self.df_drink['Total_Cost_By_Size_Qty'] = self.df_drink['Total_Cost_By_Size'] * self.df_drink['Quantity']
        self.df_drink['Size'] = self.df_drink['Size'].str.replace(r"^Size_", r"", regex=True)
        self.df_drink['GP'] = (self.df_drink['Price_By_Size'] * self.df_drink['Quantity']) - self.df_drink['Total_Cost_By_Size_Qty']
        
        
        
        self.df_ingredient = pd.DataFrame(raw_igr)
        self.df_ingredient['Payment_Period'] = self.df_ingredient['Payment_Time'].apply(lambda x: 'Current' if x >= dboard_filter_output.StartDate else 'Previous')
        self.df_ingredient['Ingredient_Quanty_x_Quantity'] = self.df_ingredient['Ingredient_Quanty'] * self.df_ingredient['Quantity']
        
        print(f"Receipts, drinks, ingredients to dataFrames completed")
        
        

    
    async def analyze_inventories(self, dboard_filter_output: DashboardFilterOutput):
        
        dict_filter_mongodb = {'Location': dboard_filter_output.to_mongodb_query().get('Location')}
        self.df_inventory = self.analyze_inventory(lst_inventory=await self.retrieve_inventory(dict_filter_mongodb=dict_filter_mongodb), is_export_df=True)
        
        print(f"Inventory to dataFrame completed")
        
        
        
    
    def dashboard_filter_output(self, dboard_filter_input: DashboardFilterInput) -> DashboardFilterOutput:
        
        start_dt = datetime.fromisoformat(dboard_filter_input.Payment_Time[0])
        end_dt = datetime.fromisoformat(dboard_filter_input.Payment_Time[1])
        
        delta = (end_dt - start_dt) + timedelta(days=1)
        prev_start_dt = start_dt - delta
        prev_end_dt   = end_dt - delta
        
        start_dt = start_dt.replace(hour=0, minute=0, second=0, microsecond=0)
        end_dt = end_dt.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        prev_start_dt = prev_start_dt.replace(hour=0, minute=0, second=0, microsecond=0)
        prev_end_dt = prev_end_dt.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        return DashboardFilterOutput(
            Location=dboard_filter_input.Location, 
            StartDate=start_dt,
            EndDate=end_dt,
            PrevStartDate=prev_start_dt,
            PrevEndtDate=prev_end_dt,
            DeltaDay=delta,
        )
    
    
    
    def dashboard_cast_flow(self, dboard_analyze: DashboardAnalyze, dboard_filter_output: DashboardFilterOutput) -> DashboardAnalyze:
    
        monthly_fixed_cost = float(self.df_fixed_cost[dboard_filter_output.Location].sum().sum())
            
        df_cast_flow: pd.DataFrame = self.df_receipt.groupby('Payment_Date')['Amount'].sum()
        df_cast_flow = pd.concat([df_cast_flow, self.df_drink.groupby('Payment_Date')['Total_Cost_By_Size_Qty'].sum()], axis=1).reset_index(drop=False)
        
        df_cast_flow['Fixed_Cost'] = monthly_fixed_cost / df_cast_flow['Payment_Date'].dt.days_in_month
        df_cast_flow['Net_Profit'] = df_cast_flow['Amount'] - (df_cast_flow['Total_Cost_By_Size_Qty'] + df_cast_flow['Fixed_Cost'])

        df_cast_flow_prev = df_cast_flow.query("Payment_Date.between(@dboard_filter_output.PrevStartDate, @dboard_filter_output.PrevEndtDate)")
        df_cast_flow_curr = df_cast_flow.query("Payment_Date.between(@dboard_filter_output.StartDate, @dboard_filter_output.EndDate)")
        
        dboard_analyze.Previous.Revenue = df_cast_flow_prev['Amount'].sum()
        dboard_analyze.Current.Revenue = df_cast_flow_curr['Amount'].sum()
        
        dboard_analyze.Previous.FixedCost = df_cast_flow_prev['Fixed_Cost'].sum()
        dboard_analyze.Current.FixedCost = df_cast_flow_curr['Fixed_Cost'].sum()
        
        dboard_analyze.Previous.DirectCost = df_cast_flow_prev['Total_Cost_By_Size_Qty'].sum()
        dboard_analyze.Current.DirectCost = df_cast_flow_curr['Total_Cost_By_Size_Qty'].sum()
        
        dboard_analyze.Previous.NetProfit = df_cast_flow_prev['Net_Profit'].sum()
        dboard_analyze.Current.NetProfit = df_cast_flow_curr['Net_Profit'].sum()

        if not (df_cast_flow_curr['Payment_Date'] == dboard_filter_output.EndDate.replace(hour=0, minute=0, second=0, microsecond=0)).any():
            
            df_predict = pd.DataFrame({
                'Payment_Date': pd.date_range(
                    start=df_cast_flow_curr['Payment_Date'].max() + timedelta(days=1),
                    end=dboard_filter_output.EndDate,
                    freq='D'
                ),
                'Amount': np.nan,
                'Total_Cost_By_Size_Qty': np.nan,
                'Fixed_Cost': df_cast_flow_curr.iloc[-1,:]['Fixed_Cost'],
                'Net_Profit': 0,
            })
            
            pred_fixed_cost = df_predict['Fixed_Cost'].sum() - dboard_analyze.Current.NetProfit
            
            df_predict['Amount'] = (pred_fixed_cost * (1 + (dboard_analyze.Current.DirectCost / dboard_analyze.Current.Revenue))) / df_predict.shape[0]
            
            df_predict['Total_Cost_By_Size_Qty'] = df_predict['Amount'] * (dboard_analyze.Current.DirectCost / dboard_analyze.Current.Revenue)
                
            df_cast_flow_curr = pd.concat([df_cast_flow_curr, df_predict], axis=0).reset_index(drop=True)
            
        
        chart_area = AreaChart(
            Colors=['#1890ff', '#13c2c2', '#faad14', '#ff3300'],
            Series=[
                {
                    'name': 'Revenue',
                    'type': 'area',
                    'data': df_cast_flow_curr['Amount'].round(0).values.tolist(),
                },
                {
                    'name': 'Direct Cost',
                    'type': 'area',
                    'data': df_cast_flow_curr['Total_Cost_By_Size_Qty'].round(0).values.tolist(),
                },
                {
                    'name': 'Net Profit (inc. fixed cost)',
                    'type': 'area',
                    'data': df_cast_flow_curr['Net_Profit'].round(0).values.tolist(),
                },
                {
                    'name': 'Fixed Cost',
                    'data': df_cast_flow_curr['Fixed_Cost'].round(0).values.tolist(),
                },
                
            ],
            Xaxis={
                'categories': df_cast_flow_curr['Payment_Date'].astype(str).values.tolist(),
                'type': 'datetime',
            }
        )
        
        dboard_analyze.ChartRevDcost = chart_area
    
        return dboard_analyze

    
    
    def dashboard_rig_usage(self, dboard_analyze: DashboardAnalyze) -> DashboardAnalyze:
        
        df_rig_usage = (
            self.df_ingredient
            .groupby(['Ingredient_ID', 'Location', 'Payment_Period', 'Ingredient_Name', 'Unit', 'Cost_Per_Unit'])['Ingredient_Quanty_x_Quantity'].sum()
            .unstack(level='Payment_Period').fillna(0)
            .reset_index(drop=False)
            .sort_values(by=['Current'], ascending=False)
        )
        
        df_inventory = self.df_inventory[['Raw_Ingredient_ID', 'Location', 'Quanty', 'remain']].copy()
        df_inventory['remain'] = df_inventory['remain'] * df_inventory['Quanty']
        
        df_rig_usage = df_rig_usage.merge(df_inventory, how='left', left_on=['Ingredient_ID', 'Location'], right_on=['Raw_Ingredient_ID', 'Location'])
        df_rig_usage = df_rig_usage.rename(columns={
            'Current': 'Current_Usage_Qty', 
            'Previous': 'Previous_Usage_Qty',
            'remain': 'Stock_Remain_Qty',
        }).drop(columns=['Raw_Ingredient_ID', 'Quanty'], errors='ignore')

        
        dboard_analyze.HTML_RawIngredientUsage = df_rig_usage.to_html(
            table_id='dt-rig-usage', 
            columns=df_rig_usage.columns.tolist()[2:],  # Exclude 'Ingredient_ID' and 'Location'
            index=False, 
            index_names=False, 
            float_format="{:,.0f}".format,
            justify='left',
            classes='table table-striped table-borderless table-sm',
        )
        
        return dboard_analyze
    
    
    
    def dashboard_drk_margin(self, dboard_analyze: DashboardAnalyze) -> DashboardAnalyze:
        
        df_drk_summary = (
            self.df_drink
            .loc[self.df_drink['Payment_Period'].isin(['Current'])]
            .groupby(['Product_Code','Location','Drink_Name','Size','Payment_Period'], as_index=False)
            .agg(
                Qty = ('Quantity', 'sum'),
                GP = ('GP', 'sum'),
                Avg_Margin = ('Margin_By_Size','mean'),
            )
            .pivot_table(
                index = ['Product_Code','Location','Drink_Name','Size'],
                values = ['Qty','GP', 'Avg_Margin'],
                fill_value = 0,
                observed= False,
            )
            .reset_index(drop=False)
            .sort_values(by=['Qty'], ascending=False)
        )
        
        dboard_analyze.HTML_DrinkSummary = df_drk_summary.to_html(
            table_id='dt-drk-summary', 
            columns=df_drk_summary.columns.tolist()[1:-3] + ['Qty', 'GP', 'Avg_Margin'],  # Exclude 'Product_Code'
            index=False, 
            index_names=False, 
            float_format="{:,.0f}".format,
            justify='left',
            classes='table table-striped table-borderless table-sm',
        )
        
        dboard_analyze.HTML_DrinkSummary = dboard_analyze.HTML_DrinkSummary.replace('<th>', '<th class="text-nowrap">')    
        
        return dboard_analyze
    
    
    
    
    async def dashboard_analyze(self, dboard_filter_input: DashboardFilterInput, current_user: UserPublic) -> DashboardAnalyze:
        
        try:
        
            dboard_filter_output = self.dashboard_filter_output(dboard_filter_input=dboard_filter_input)
            
            await self.analyze_fixed_cost()
            await self.analyze_receipts_drinks_ingredients(dboard_filter_output=dboard_filter_output, current_user=current_user)
            await self.analyze_inventories(dboard_filter_output=dboard_filter_output)
            
            if self.df_receipt.empty or self.df_drink.empty:
                raise HTTPException(status_code=400, detail=f"Filter data is empty!")
            
            str_date_format = '%b-%d'
            
            dboard_data = {
                'Previous': {
                    'Period': f"{dboard_filter_output.PrevStartDate.strftime(str_date_format)} to {dboard_filter_output.PrevEndtDate.strftime(str_date_format)}",
                    'Revenue': 0,
                    'DirectCost': 0,
                },
                'Current': {
                    'Period': f"{dboard_filter_output.StartDate.strftime(str_date_format)} to {dboard_filter_output.EndDate.strftime(str_date_format)}",
                    'Revenue': 0,
                    'DirectCost': 0,
                },
            }
            
            # Cast Flow
            dboard_analyze = self.dashboard_cast_flow(dboard_analyze=DashboardAnalyze(**dboard_data), dboard_filter_output=dboard_filter_output)
            
        
            # Raw Ingredient Usage
            dboard_analyze = self.dashboard_rig_usage(dboard_analyze=dboard_analyze)
            
            
            # Drink Margin
            dboard_analyze = self.dashboard_drk_margin(dboard_analyze=dboard_analyze)
            
            
        except Exception as e:
            print(f"Error analyzing dashboard: {traceback.format_exc()}")
            raise HTTPException(status_code=400, detail=f"<b>Could not analyze dashboard</b>:\n{e}")
        
        
        
        return dboard_analyze


