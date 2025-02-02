from fastapi import APIRouter, Request, HTTPException, Query
from fastapi.responses import RedirectResponse, HTMLResponse
import requests
import redis
import secrets
import base64
import json

router = APIRouter()
redis_client = redis.Redis(host='localhost', port=6379, db=0)

CLIENT_ID = "88bd9549-9cb9-4b7e-8a0f-187fa76575c9"
CLIENT_SECRET = "e7210923-5470-4cc6-89a3-9c9ba5092aca"
REDIRECT_URI = "http://localhost:8000/integrations/hubspot/oauth2callback"
SCOPES = "contacts"  # Scope oficial para contactos

@router.get("/hubspot/authorize")
async def authorize_hubspot(
    user_id: str = Query(...),
    org_id: str = Query(...)
):
    try:
        # Generar y almacenar state
        state = secrets.token_urlsafe(32)
        state_data = {
            "state": state,
            "user_id": user_id,
            "org_id": org_id
        }
        
        redis_key = f"hubspot:{org_id}:{user_id}:state"
        redis_client.setex(redis_key, 600, json.dumps(state_data))
        
        # Codificar state para URL
        encoded_state = base64.urlsafe_b64encode(
            json.dumps(state_data).encode()
        ).decode()
        
        # Construir URL de HubSpot
        auth_url = (
            f"https://app.hubspot.com/oauth/authorize?"
            f"client_id={CLIENT_ID}&"
            f"redirect_uri={REDIRECT_URI}&"
            f"scope={SCOPES}&"
            f"state={encoded_state}"
        )
        
        return RedirectResponse(auth_url)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/hubspot/oauth2callback")
async def oauth2callback_hubspot(code: str, state: str):
    try:
        # Decodificar state
        state_data = json.loads(base64.urlsafe_b64decode(state).decode())
        redis_key = f"hubspot:{state_data['org_id']}:{state_data['user_id']}:state"
        
        # Validar state
        stored_state = redis_client.get(redis_key)
        if not stored_state or json.loads(stored_state)["state"] != state_data["state"]:
            raise HTTPException(status_code=400, detail="State inválido")
        
        # Obtener access token
        token_data = {
            "grant_type": "authorization_code",
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "redirect_uri": REDIRECT_URI,
            "code": code
        }
        
        response = requests.post(
            "https://api.hubapi.com/oauth/v1/token",
            data=token_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        response.raise_for_status()
        
        token_info = response.json()
        
        # Almacenar token
        token_key = f"hubspot:{state_data['org_id']}:{state_data['user_id']}:token"
        redis_client.setex(
            token_key,
            token_info.get("expires_in", 3600),
            token_info["access_token"]
        )
        
        # Limpiar state
        redis_client.delete(redis_key)
        
        # Cerrar ventana y notificar éxito
        return HTMLResponse("""
            <html><script>
                window.opener.postMessage({
                    type: 'hubspot-auth-success',
                    user_id: '""" + state_data["user_id"] + """',
                    org_id: '""" + state_data["org_id"] + """'
                }, '*');
                window.close();
            </script></html>
        """)
        
    except Exception as e:
        return HTMLResponse(f"""
            <html><script>
                window.opener.postMessage({{
                    type: 'hubspot-auth-error',
                    error: '{str(e)}'
                }}, '*');
                window.close();
            </script></html>
        """)

@router.get("/hubspot/credentials")
async def get_hubspot_credentials(
    user_id: str = Query(...),
    org_id: str = Query(...)
):
    token_key = f"hubspot:{org_id}:{user_id}:token"
    access_token = redis_client.get(token_key)
    
    if not access_token:
        raise HTTPException(status_code=404, detail="Token no encontrado")
    
    return {"access_token": access_token.decode()}

@router.get("/hubspot/items")
async def get_items_hubspot(
    user_id: str = Query(...),
    org_id: str = Query(...)
):
    try:
        credentials = await get_hubspot_credentials(user_id, org_id)
        headers = {"Authorization": f"Bearer {credentials['access_token']}"}
        
        all_contacts = []
        after = None
        
        while True:
            params = {"limit": 100, "after": after} if after else {"limit": 100}
            response = requests.get(
                "https://api.hubapi.com/crm/v3/objects/contacts",
                headers=headers,
                params=params
            )
            response.raise_for_status()
            
            data = response.json()
            contacts = data.get("results", [])
            
            for contact in contacts:
                all_contacts.append({
                    "id": contact["id"],
                    "name": f'{contact["properties"].get("firstname", "")} {contact["properties"].get("lastname", "")}'.strip(),
                    "email": contact["properties"].get("email", ""),
                    "company": contact["properties"].get("company", "")
                })
            
            if not data.get("paging", {}).get("next"):
                break
                
            after = data["paging"]["next"]["after"]
        
        print(f"Contactos obtenidos: {len(all_contacts)}")
        return all_contacts
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))