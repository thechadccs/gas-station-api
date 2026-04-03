from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import requests
import math
from typing import Optional, List

# Create the application instance
app = FastAPI(title="Gas Station Pro Backend")

# Agreement: CORS Middleware is required for the frontend to communicate with this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Concepts: This code mirrors the original non-web service logic for data parsing/math
API_BASE = "https://sedeaplicaciones.minetur.gob.es/ServiciosRESTCarburantes/PreciosCarburantes"
HEADERS = {'User-Agent': 'GasStationPro_LocalPort/1.0'}

# Agreement: Calculate distance using the original local Python Haversine method
def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2)
    c = 2 * math.asin(math.sqrt(a))
    return R * c

# --- Endpoints providing lists ---

@app.get("/provinces")
async def get_provinces():
    try:
        url = f"{API_BASE}/Provincias/"
        response = requests.get(url, headers=HEADERS, timeout=30)
        return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"API Error: {str(e)}")

@app.get("/municipalities/{province_id}")
async def get_municipalities(province_id: str):
    try:
        url = f"{API_BASE}/MunicipiosProvincia/{province_id}"
        response = requests.get(url, headers=HEADERS, timeout=30)
        return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"API Error: {str(e)}")

# --- Core Search Endpoint ---

# Agreement: Implementation of the cascading logic and exact results structure
@app.get("/search")
async def search(
    municipality: str,
    fuel_key: str, # The literal key like "Precio Gasolina 95 E5" from the frontend list
    radius: float,
    province_name: Optional[str] = None
):
    try:
        url = f"{API_BASE}/EstacionesTerrestres/"
        response = requests.get(url, headers=HEADERS, timeout=60) # High timeout for full dump
        response_data = response.json()
        all_stations = response_data.get('ListaEESSPrecio', [])

        # Agreement: Find center coords by exact municipality name (like original python file)
        # Handle the Ministry's strict casing/accents (using basic upper for simplicity as agreed previously)
        center_coords = None
        target_muni_upper = municipality.strip().upper()
        
        # Concepts: Province name helps narrow down if multiple munis exist
        for s in all_stations:
            # Check municipality. If province is provided, it must also match
            if s['Municipio'].upper() == target_muni_upper:
                if province_name:
                    if s['Provincia'].upper() == province_name.strip().upper():
                        lat = float(s['Latitud'].replace(',', '.'))
                        lon = float(s['Longitud (WGS84)'].replace(',', '.'))
                        center_coords = (lat, lon)
                        break
                else:
                    # Found muni, no province needed (or province check not requested)
                    lat = float(s['Latitud'].replace(',', '.'))
                    lon = float(s['Longitud (WGS84)'].replace(',', '.'))
                    center_coords = (lat, lon)
                    break

        if not center_coords:
            raise HTTPException(status_code=404, detail="Municipality coordinates not found.")

        center_lat, center_lon = center_coords
        results = []

        # Concepts: The filtering and formatting rules from the original local file
        for s in all_stations:
            price_str = s.get(fuel_key)
            if not price_str or price_str == "":
                continue

            lat = float(s['Latitud'].replace(',', '.'))
            lon = float(s['Longitud (WGS84)'].replace(',', '.'))
            
            # Use original Haversine logic
            distance = calculate_distance(center_lat, center_lon, lat, lon)

            if distance <= radius:
                # Rule: Format address for the specific results box behavior (Map link activation)
                brand_label = s['Rótulo']
                full_address = s['Dirección']
                
                # Agreement: Implementation of results columns: brand, price, distance, address
                results.append({
                    "brand": brand_label,
                    "price": float(price_str.replace(',', '.')),
                    "distance": round(distance, 2),
                    "address": full_address,
                    # Generated in backend to map exactly to browser/app map intent as in original file
                    "maps_link": f"https://www.google.com/maps/search/?api=1&query={full_address}, Spain"
                })

        # Concepts: The final results sorting by price (cheapest first)
        results.sort(key=lambda x: x['price'])
        
        return results

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
