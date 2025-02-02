import json
import secrets
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse
import httpx
import asyncio
import base64
import requests
from integrations.integration_item import IntegrationItem

from redis_client import add_key_value_redis, get_value_redis, delete_key_redis

router = APIRouter(prefix="/notion", tags=["Notion"])

# Configuración real de tu aplicación Notion
CLIENT_ID = 'XXX'
CLIENT_SECRET = 'XXX'
encoded_client_id_secret = base64.b64encode(f'{CLIENT_ID}:{CLIENT_SECRET}'.encode()).decode()

REDIRECT_URI = 'http://localhost:8000/integrations/notion/oauth2callback'
authorization_base_url = 'https://api.notion.com/v1/oauth/authorize'

@router.get("/authorize")
async def authorize_notion(user_id: str, org_id: str):
    state_data = {
        'state': secrets.token_urlsafe(32),
        'user_id': user_id,
        'org_id': org_id
    }
    encoded_state = base64.urlsafe_b64encode(json.dumps(state_data).encode()).decode()
    
    auth_url = (f'{authorization_base_url}?client_id={CLIENT_ID}'
                f'&response_type=code&redirect_uri={REDIRECT_URI}'
                f'&state={encoded_state}')
    
    await add_key_value_redis(f'notion_state:{org_id}:{user_id}', json.dumps(state_data), expire=600)
    return {"authorization_url": auth_url}

@router.get("/oauth2callback")
async def oauth2callback_notion(request: Request):
    params = request.query_params
    if params.get('error'):
        raise HTTPException(status_code=400, detail=params.get('error_description'))
    
    try:
        encoded_state = params.get('state')
        code = params.get('code')
        state_data = json.loads(base64.urlsafe_b64decode(encoded_state).decode())
        
        original_state = state_data.get('state')
        user_id = state_data.get('user_id')
        org_id = state_data.get('org_id')
        
        saved_state = await get_value_redis(f'notion_state:{org_id}:{user_id}')
        if not saved_state or original_state != json.loads(saved_state).get('state'):
            raise HTTPException(status_code=400, detail='Invalid state')

        async with httpx.AsyncClient() as client:
            response = await client.post(
                'https://api.notion.com/v1/oauth/token',
                headers={
                    'Authorization': f'Basic {encoded_client_id_secret}',
                    'Content-Type': 'application/json'
                },
                json={
                    'grant_type': 'authorization_code',
                    'code': code,
                    'redirect_uri': REDIRECT_URI
                }
            )
            
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail=response.text)

            credentials = response.json()
            await add_key_value_redis(
                f'notion_credentials:{org_id}:{user_id}',
                json.dumps(credentials),
                expire=credentials.get('expires_in', 3600)
            )

        return HTMLResponse(content="<script>window.close()</script>")
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/credentials")
async def get_notion_credentials(user_id: str, org_id: str):
    credentials = await get_value_redis(f'notion_credentials:{org_id}:{user_id}')
    if not credentials:
        raise HTTPException(status_code=404, detail='No credentials found')
    return json.loads(credentials)

def _recursive_dict_search(data, target_key):
    """Búsqueda recursiva de claves en estructuras anidadas"""
    if isinstance(data, dict):
        for key, value in data.items():
            if key == target_key:
                return value
            if isinstance(value, (dict, list)):
                result = _recursive_dict_search(value, target_key)
                if result is not None:
                    return result
    elif isinstance(data, list):
        for item in data:
            result = _recursive_dict_search(item, target_key)
            if result is not None:
                return result
    return None

def create_integration_item_metadata_object(response_json: dict) -> IntegrationItem:
    """Crea objetos de metadatos unificados para Notion"""
    item_id = response_json.get('id')
    item_type = response_json.get('object', 'unknown')
    
    # Búsqueda de nombre en propiedades anidadas
    name = _recursive_dict_search(response_json, 'title') or \
           _recursive_dict_search(response_json, 'name') or \
           f"{item_type.capitalize()} {item_id[:6]}"
    
    # Manejo de parent_id
    parent_data = response_json.get('parent', {})
    parent_type = parent_data.get('type')
    parent_id = None
    if parent_type == 'page_id':
        parent_id = parent_data.get('page_id')
    elif parent_type == 'database_id':
        parent_id = parent_data.get('database_id')
    elif parent_type == 'workspace':
        parent_id = 'workspace'

    return IntegrationItem(
        id=item_id,
        name=name,
        type=item_type,
        parent_id=parent_id,
        creation_time=response_json.get('created_time'),
        last_modified_time=response_json.get('last_edited_time'),
        fields={
            'url': response_json.get('url'),
            'archived': response_json.get('archived', False)
        }
    )

@router.get("/items")
async def get_items_notion(credentials: dict) -> list[IntegrationItem]:
    """Obtiene todos los elementos de Notion"""
    try:
        access_token = credentials.get('access_token')
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Notion-Version': '2022-06-28',
            'Content-Type': 'application/json'
        }
        
        # Obtener todos los elementos paginados
        all_items = []
        start_cursor = None
        
        while True:
            payload = {
                "filter": {
                    "value": "page",
                    "property": "object"
                },
                "page_size": 100
            }
            if start_cursor:
                payload["start_cursor"] = start_cursor
                
            response = requests.post(
                'https://api.notion.com/v1/search',
                headers=headers,
                json=payload
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Error de Notion: {response.text}"
                )
            
            data = response.json()
            all_items.extend(data.get('results', []))
            
            if not data.get('has_more'):
                break
                
            start_cursor = data.get('next_cursor')

        return [create_integration_item_metadata_object(item) for item in all_items]
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))