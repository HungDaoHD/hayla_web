from fastapi import APIRouter, Depends, status, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from routers.auth.oauth2 import require_role
from mvc.users import UserPublic
from mvc.operation import Operation, InventoryItemInsert, DrinkUpdate


lst_role = ['Admin', 'Staff']
router = APIRouter(prefix='/operation', tags=['operation'], dependencies=[Depends(require_role(role=lst_role))])
router.mount('/static', StaticFiles(directory='static'), name='static')
templates = Jinja2Templates(directory='templates')



@router.get('/fixed_cost', response_class=HTMLResponse, dependencies=[Depends(require_role(role=['Admin']))])
async def retrieve_fixed_cost(request: Request, current_user: UserPublic = Depends(require_role(role=['Admin']))):

    opt = Operation()
    lst_fixed_cost = await opt.retrieve_fixed_cost()

    return templates.TemplateResponse('operation/fixed_cost.html', {
        'request': request,
        'user': current_user.model_dump(),
        'lst_fixed_cost': lst_fixed_cost
    })



@router.get('/raw_ingredient', response_class=HTMLResponse, dependencies=[Depends(require_role(role=['Admin']))])
async def retrieve_raw_ingredient(request: Request, current_user: UserPublic = Depends(require_role(role=['Admin']))):

    opt = Operation()
    lst_raw_ingredient = await opt.retrieve_raw_ingredient(current_user, is_show_disable=True)

    return templates.TemplateResponse('operation/raw_ingredient.html', {
        'request': request,
        'user': current_user.model_dump(),
        'lst_raw_ingredient': lst_raw_ingredient
    })



@router.get('/processed_ingredient', response_class=HTMLResponse)
async def retrieve_processed_ingredient(request: Request, current_user: UserPublic = Depends(require_role(role=lst_role))):

    opt = Operation()
    lst_processed_ingredient = await opt.retrieve_processed_ingredient(current_user)

    js_pigs = [p.model_dump() for p in lst_processed_ingredient]

    return templates.TemplateResponse('operation/processed_ingredient.html', {
        'request': request,
        'user': current_user.model_dump(),
        'lst_processed_ingredient': lst_processed_ingredient,
        'js_pigs': js_pigs,
    })



@router.get('/drink', response_class=HTMLResponse)
async def retrieve_drink(request: Request, current_user: UserPublic = Depends(require_role(role=lst_role))):

    opt = Operation()
    dict_drink = await opt.retrieve_drink(current_user)
    lst_full_igr = await opt.get_full_ingredients(current_user)

    js_drinks = {k: [i.model_dump() for i in v] for k, v in dict_drink.items()}
    js_full_igr = {i.ID: i.model_dump() for i in lst_full_igr}

    return templates.TemplateResponse('operation/drink.html', {
        'request': request,
        'user': current_user.model_dump(),
        'dict_drink': dict_drink,
        'js_drinks': js_drinks,
        'js_full_igr': js_full_igr,
    })



@router.post('/drink/{oid}/update', response_class=JSONResponse)
async def update_drink(oid: str, obj_drink: DrinkUpdate, current_user: UserPublic = Depends(require_role(role=['Admin']))):
    opt = Operation()
    updated_drink: DrinkUpdate = await opt.update_drink(oid=oid, obj_drink=obj_drink)
    return JSONResponse(content=updated_drink.model_dump(mode='json'))



@router.get('/inventory', response_class=HTMLResponse)
async def retrieve_inventory(request: Request, current_user: UserPublic = Depends(require_role(role=lst_role))):

    opt = Operation()
    lst_inv = await opt.retrieve_inventory()
    lst_rig = await opt.retrieve_raw_ingredient(current_user)
    lst_loc = ['SGN', 'NTR']

    dict_total_qty = opt.analyze_inventory(lst_inv)

    return templates.TemplateResponse('operation/inventory.html', {
        'request': request,
        'user': current_user.model_dump(),
        'lst_inv': lst_inv,
        'dict_rig': {i.Raw_Ingredient_ID: i.model_dump() for i in lst_rig},
        'lst_loc': lst_loc,
        'dict_total_qty': dict_total_qty,
    })



@router.post('/inventory/add-items', response_class=JSONResponse)
async def inventory_add_items(lst_inv_item: list[InventoryItemInsert], current_user: UserPublic = Depends(require_role(role=lst_role))):

    opt = Operation()
    lst_inv = await opt.add_inventory_items(lst_inv_item, current_user)

    return JSONResponse(content=[i.model_dump(mode='json') for i in lst_inv])

