# backend/integrations/hubspot.py
from datetime import datetime
from typing import List

async def get_items_hubspot(
    user_id: str = Query(...),
    org_id: str = Query(...)
) -> List[IntegrationItem]:
    try:
        credentials = await get_hubspot_credentials(user_id, org_id)
        headers = {
            "Authorization": f"Bearer {credentials['access_token']}",
            "Accept": "application/json"
        }
        
        items = []
        after = None
        
        while True:
            params = {
                "limit": 100,
                "properties": [
                    "firstname", "lastname", "email", "company", 
                    "phone", "createdate", "lastmodifieddate",
                    "associatedcompanyid", "hs_object_id"
                ]
            }
            if after:
                params["after"] = after

            response = requests.get(
                "https://api.hubapi.com/crm/v3/objects/contacts",
                headers=headers,
                params=params
            )
            response.raise_for_status()
            
            data = response.json()
            contacts = data.get("results", [])
            
            for contact in contacts:
                props = contact.get("properties", {})
                
                # Obtener nombre de la compañía si está disponible
                company_id = props.get("associatedcompanyid")
                company_name = props.get("company", "Sin compañía asociada")
                
                item = IntegrationItem(
                    id=props.get("hs_object_id", contact["id"]),
                    name=f'{props.get("firstname", "")} {props.get("lastname", "")}'.strip() or "Contacto sin nombre",
                    type="HubSpot Contact",
                    creation_time=datetime.fromtimestamp(int(props["createdate"])/1000) if "createdate" in props else None,
                    last_modified_time=datetime.fromtimestamp(int(props["lastmodifieddate"])/1000) if "lastmodifieddate" in props else None,
                    parent_id=company_id,
                    parent_path_or_name=company_name,
                    url=f"https://app.hubspot.com/contacts/{credentials.get('portal_id', '')}/contact/{contact['id']}",
                    directory=False,
                    visibility=True
                )
                items.append(item)
            
            if not data.get("paging", {}).get("next"):
                break
                
            after = data["paging"]["next"]["after"]

        print(f"[HubSpot] {len(items)} items procesados:")
        for item in items:
            print(f"• {item.name} ({item.id})")
            
        return items
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
    except requests.HTTPError as e:
        error_msg = f"Error en API HubSpot: {e.response.status_code} - {e.response.text}"
        print(error_msg)
        raise HTTPException(status_code=502, detail=error_msg)
    except Exception as e:
        error_msg = f"Error general: {str(e)}"
        print(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)