"""
Google Places API integration for Lead Generation (Prospecting)
"""
import googlemaps
from typing import List, Dict, Any, Optional

class PlacesClient:
    """Client for Google Places & Geocoding APIs"""
    
    def __init__(self, api_key: str):
        self.client = googlemaps.Client(key=api_key)
        
    def geocode_region(self, region_query: str) -> Optional[Dict[str, float]]:
        """
        Geocode a region string (e.g. "San Juan del Río, Qro") to get lat/lng.
        Returns {'lat': float, 'lng': float} or None.
        """
        try:
            results = self.client.geocode(region_query)
            if results and len(results) > 0:
                location = results[0]['geometry']['location']
                return location
            return None
        except Exception as e:
            print(f"Geocoding Error: {e}")
            return None

    def search_nearby_places(
        self, 
        lat: float, 
        lng: float, 
        radius: int = 5000, 
        keyword: str = "Cremería o Tienda de Abarrotes"
    ) -> List[Dict[str, Any]]:
        """
        Search for places nearby a location using Places API (New).
        Docs: https://developers.google.com/maps/documentation/places/web-service/text-search
        """
        import requests
        
        try:
            print(f"DEBUG: Searching Places (New API). Lat: {lat}, Lng: {lng}, Radius: {radius}, Keyword: {keyword}")
            
            url = "https://places.googleapis.com/v1/places:searchText"
            
            headers = {
                "Content-Type": "application/json",
                "X-Goog-Api-Key": self.client.key,
                "X-Goog-FieldMask": "places.name,places.formattedAddress,places.location,places.rating,places.types,places.id,places.displayName"
            }
            
            # Radius in New API is used in locationBias
            payload = {
                "textQuery": keyword,
                "locationBias": {
                    "circle": {
                        "center": {
                            "latitude": lat,
                            "longitude": lng
                        },
                        "radius": float(radius)
                    }
                },
                "maxResultCount": 20
            }
            
            response = requests.post(url, json=payload, headers=headers)
            
            if response.status_code != 200:
                error_msg = f"Places API Error {response.status_code}: {response.text}"
                print(error_msg)
                raise Exception(error_msg)
                
            data = response.json()
            results = data.get("places", [])
            print(f"DEBUG: Places API found {len(results)} results")
            
            places = []
            for place in results:
                places.append({
                    "name": place.get("displayName", {}).get("text", "Sin Nombre"),
                    "address": place.get("formattedAddress", "Sin Dirección"),
                    "lat": place["location"]["latitude"],
                    "lng": place["location"]["longitude"],
                    "rating": place.get("rating", 0),
                    "place_id": place.get("id"),
                    "types": place.get("types", [])
                })
            
            return places
            
        except Exception as e:
            print(f"Places Search Error: {e}")
            raise e

    def detect_market(self, lat: float, lng: float) -> Optional[str]:
        """
        Detect if the location is inside or very close to a Market.
        Returns the Name of the market (e.g. "Mercado 23") or None.
        """
        try:
            # We search specifically for "Mercado" with a tight radius
            places = self.search_nearby_places(
                lat=lat, 
                lng=lng, 
                radius=150, 
                keyword="Mercado"
            )
            
            if not places:
                return None
                
            # Filter the best match
            for place in places:
                name = place.get('name', '').lower()
                types = place.get('types', [])
                
                # Strong signal check
                if 'market' in types or 'shopping_mall' in types or 'mercado' in name:
                    # Return the Clean Name (Title Case)
                    return place.get('name')
            
            return None
            
        except Exception as e:
            print(f"Market Detection Error: {e}")
            return None
