from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import requests
import math

app = FastAPI()

# ⚠️ CRITICAL: Allows your GitHub site to talk to this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_BASE = "https://sedeaplicaciones.minetur.gob.es/ServiciosRESTCarburantes/PreciosCarburantes"

@app.get("/provinces")
def get_provinces():
    r = requests.get(f"{API_BASE}/Provincias/")
    return r.json()

@app.get("/municipalities/{prov_id}")
def get_municipalities(prov_id: str):
    r = requests.get(f"{API_BASE}/MunicipiosProvincia/{prov_id}")
    return r.json()

@app.get("/search")
async def search(municipality: str, fuel_type: str = "95", radius: float = 5.0):
    fuel_map = {
        "95": "Precio Gasolina 95 E5",
        "98": "Precio Gasolina 98 E5",
        "diesel": "Precio Gasóleo A",
        "premium": "Precio Gasóleo A mejorado"
    }
    f_key = fuel_map.get(fuel_type, "Precio Gasolina 95 E5")
    
    try:
        # Fetch all stations
        data = requests.get(f"{API_BASE}/EstacionesTerrestres/").json()['ListaEESSPrecio']
        
        # Find center coords
        center = next((s for s in data if s['Municipio'].upper() == municipality.upper()), None)
        if not center: raise HTTPException(status_code=404, detail="City not found")
        
        c_lat = float(center['Latitud'].replace(',', '.'))
        c_lon = float(center['Longitud (WGS84)'].replace(',', '.'))

        results = []
        for s in data:
            if not s.get(f_key): continue
            lat = float(s['Latitud'].replace(',', '.'))
            lon = float(s['Longitud (WGS84)'].replace(',', '.'))
            
            # Haversine
            dlat, dlon = math.radians(lat-c_lat), math.radians(lon-c_lon)
            a = math.sin(dlat/2)**2 + math.cos(math.radians(c_lat)) * math.cos(math.radians(lat)) * math.sin(dlon/2)**2
            dist = 6371 * 2 * math.asin(math.sqrt(a))

            if dist <= radius:
                results.append({
                    "brand": s['Rótulo'],
                    "price": float(s[f_key].replace(',', '.')),
                    "dist": round(dist, 2),
                    "address": s['Dirección'],
                    "url": f"https://www.google.com/maps/search/{s['Dirección']} {s['Rótulo']}"
                })
        
        return sorted(results, key=lambda x: x['price'])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
