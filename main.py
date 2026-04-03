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
    try:
        dlat, dlon = math.radians(lat2-lat1), math.radians(lon2-lon1)
        a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
        return R * 2 * math.asin(math.sqrt(a))
    except: return 999.0

@app.get("/provinces")
def get_provinces():
    try:
        r = requests.get(f"{API_BASE}/Provincias/", timeout=25)
        return r.json()
    except: return {"ListaProvincias": []}

@app.get("/municipalities/{prov_id}")
def get_municipalities(prov_id: str):
    try:
        r = requests.get(f"{API_BASE}/MunicipiosProvincia/{prov_id}", timeout=25)
        return r.json()
    except: return {"ListaMunicipios": []}

@app.get("/search")
async def search(municipality: str, fuel_key: str, radius: float, province: str):
    try:
        r = requests.get(f"{API_BASE}/EstacionesTerrestres/", timeout=35)
        all_data = r.json().get('ListaEESSPrecio', [])
        center = next((s for s in all_data if s['Municipio'].upper() == municipality.upper() and s['Provincia'].upper() == province.upper()), None)
        if not center: return {"stations": []}
        c_lat, c_lon = float(center['Latitud'].replace(',', '.')), float(center['Longitud (WGS84)'].replace(',', '.'))
        results = []
        for s in all_data:
            if not s.get(fuel_key): continue
            lat, lon = float(s['Latitud'].replace(',', '.')), float(s['Longitud (WGS84)'].replace(',', '.'))
            dist = haversine(c_lat, c_lon, lat, lon)
            if dist <= radius:
                results.append({"brand": s['Rótulo'], "price": float(s[fuel_key].replace(',', '.')), "distance": round(dist, 2), "address": s['Dirección']})
        return {"stations": sorted(results, key=lambda x: x['price'])}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))
