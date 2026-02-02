import os
import googlemaps
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")

if not API_KEY:
    print("Error: No API Key")
    exit(1)

gmaps = googlemaps.Client(key=API_KEY)

# Geocode the Plus Code
query = "98FQ+P3 Huichapan, Hidalgo"
print(f"Geocoding: {query}")

try:
    results = gmaps.geocode(query)
    if results:
        loc = results[0]['geometry']['location']
        print(f"FOUND: lat={loc['lat']}, lng={loc['lng']}")
        print(f"Address: {results[0]['formatted_address']}")
    else:
        print("No results found.")
except Exception as e:
    print(f"Error: {e}")
