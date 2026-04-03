from fastapi import FastAPI, HTTPException, Query
from typing import List, Optional
import requests
import math
import urllib.parse

app = FastAPI(
    title="Gas Station Pro API",
    description="API to find the cheapest gas stations in Spain based on location and radius.",
    version="1.0.0"
)

# --- Configuration & Constants ---
API_BASE = "https://sedeaplicaciones.minetur.gob.es/ServiciosRESTCarburantes/PreciosCarburantes"
API_ALL_STATIONS = f"{API_BASE}/EstacionesTerrestres/"

FUEL_MAP = {
    "95": "Precio Gasolina 95 E5",
    "98": "Precio Gasolina 98 E5",
    "diesel": "Precio Gasóleo A",
    "premium": "Precio Gasóleo A mejorado",
    "glp": "Precio Gases licuados del petróleo"
}


# --- Helper Functions ---
def calculate_distance(lat1, lon1, lat2, lon2):
    """Haversine formula to calculate distance between two points in km."""
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2)
    c = 2 * math.asin(math.sqrt(a))
    return R * c


# --- API Endpoints ---

@app.get("/")
def read_root():
    return {"message": "Welcome to Gas Station Pro API. Go to /docs for interactive testing."}


@app.get("/search")
async def search_stations(
        municipality: str,
        fuel_type: str = Query("95", description="Options: 95, 98, diesel, premium, glp"),
        radius: float = 5.0,
        brand_filter: Optional[str] = None,
        address_filter: Optional[str] = None
):
    """
    Finds gas stations within a radius of a specific municipality.
    """
    f_key = FUEL_MAP.get(fuel_type.lower())
    if not f_key:
        raise HTTPException(status_code=400, detail="Invalid fuel type")

    try:
        response = requests.get(API_ALL_STATIONS, timeout=20)
        data = response.json().get('ListaEESSPrecio', [])

        # 1. Find center point (The chosen municipality)
        center_lat, center_lon = None, None
        for s in data:
            if s['Municipio'].upper() == municipality.upper():
                center_lat = float(s['Latitud'].replace(',', '.'))
                center_lon = float(s['Longitud (WGS84)'].replace(',', '.'))
                break

        if center_lat is None:
            raise HTTPException(status_code=404, detail="Municipality not found or has no coordinates")

        # 2. Filter stations by distance and optional text filters
        results = []
        for s in data:
            price_str = s.get(f_key)
            if not price_str: continue

            lat = float(s['Latitud'].replace(',', '.'))
            lon = float(s['Longitud (WGS84)'].replace(',', '.'))
            dist = calculate_distance(center_lat, center_lon, lat, lon)

            if dist <= radius:
                brand = s['Rótulo']
                address = s['Dirección']

                # Secondary Filters
                if brand_filter and brand_filter.upper() not in brand.upper(): continue
                if address_filter and address_filter.upper() not in address.upper(): continue

                # Create Google Maps Link
                map_query = urllib.parse.quote(f"{address} {brand}")
                map_url = f"https://www.google.com/maps/search/?api=1&query={map_query}"

                results.append({
                    "brand": brand,
                    "price": float(price_str.replace(',', '.')),
                    "distance_km": round(dist, 2),
                    "address": address,
                    "google_maps_url": map_url
                })

        # Sort by price (cheapest first)
        results.sort(key=lambda x: x['price'])

        return {
            "metadata": {
                "municipality": municipality,
                "fuel": fuel_type,
                "radius_km": radius,
                "total_found": len(results)
            },
            "stations": results
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)