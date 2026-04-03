from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import requests
import math

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_BASE = "https://sedeaplicaciones.minetur.gob.es/ServiciosRESTCarburantes/PreciosCarburantes"

def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dlat, dlon = math.radians(lat2-lat1), math.radians(lon2-lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return R * 2 * math.asin(math.sqrt(a))

@app.get("/provinces")
def get_provinces():
    # Returns the official Ministry list
    return requests.get(f"{API_BASE}/Provincias/").json()

@app.get("/municipalities/{prov_id}")
def get_municipalities(prov_id: str):
    return requests.get(f"{API_BASE}/MunicipiosProvincia/{prov_id}").json()

@app.get("/search")
async def search(municipality: str, fuel_key: str, radius: float, province: str):
    try:
        # Full dump fetch (matches original python file logic)
        data_resp = requests.get(f"{API_BASE}/EstacionesTerrestres/").json()
        data = data_resp.get('ListaEESSPrecio', [])
        
        # Find center coords
        center = next((s for s in data if s['Municipio'].upper() == municipality.upper() 
                       and s['Provincia'].upper() == province.upper()), None)
        
        if not center: return {"stations": []}
        
        c_lat = float(center['Latitud'].replace(',', '.'))
        c_lon = float(center['Longitud (WGS84)'].replace(',', '.'))

        results = []
        for s in data:
            if not s.get(fuel_key): continue
            lat = float(s['Latitud'].replace(',', '.'))
            lon = float(s['Longitud (WGS84)'].replace(',', '.'))
            dist = haversine(c_lat, c_lon, lat, lon)

            if dist <= radius:
                results.append({
                    "brand": s['Rótulo'],
                    "price": float(s[fuel_key].replace(',', '.')),
                    "distance": round(dist, 2),
                    "address": s['Dirección']
                })
        
        return {"stations": sorted(results, key=lambda x: x['price'])}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
