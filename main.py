from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import requests
import math

app = FastAPI()

# This is CRITICAL to stop the "NetworkError" and "Unexpected Character" issues
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
    try:
        dlat, dlon = math.radians(lat2-lat1), math.radians(lon2-lon1)
        a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
        return R * 2 * math.asin(math.sqrt(a))
    except: return 999.0

@app.get("/provinces")
def get_provinces():
    r = requests.get(f"{API_BASE}/Provincias/")
    return r.json()

@app.get("/municipalities/{prov_id}")
def get_municipalities(prov_id: str):
    r = requests.get(f"{API_BASE}/MunicipiosProvincia/{prov_id}")
    return r.json()

@app.get("/search")
async def search(municipality: str, fuel_key: str, radius: float, province: str):
    r = requests.get(f"{API_BASE}/EstacionesTerrestres/")
    all_data = r.json().get('ListaEESSPrecio', [])
    
    # Identify the center coordinates for the municipality
    center = next((s for s in all_data if s['Municipio'].upper() == municipality.upper() 
                   and s['Provincia'].upper() == province.upper()), None)
    
    if not center: return {"stations": []}
    
    c_lat = float(center['Latitud'].replace(',', '.'))
    c_lon = float(center['Longitud (WGS84)'].replace(',', '.'))

    results = []
    for s in all_data:
        p_val = s.get(fuel_key)
        if not p_val: continue
        
        lat, lon = float(s['Latitud'].replace(',', '.')), float(s['Longitud (WGS84)'].replace(',', '.'))
        dist = haversine(c_lat, c_lon, lat, lon)

        if dist <= radius:
            results.append({
                "brand": s['Rótulo'],
                "price": float(p_val.replace(',', '.')),
                "distance": round(dist, 2),
                "address": s['Dirección']
            })
    
    return {"stations": sorted(results, key=lambda x: x['price'])}
