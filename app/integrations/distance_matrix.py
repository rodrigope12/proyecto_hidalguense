"""
Google Distance Matrix API integration for travel time calculations
"""
import os
import googlemaps
from typing import List, Tuple, Dict, Any
import math


class DistanceMatrixClient:
    """Client for Google Distance Matrix API"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = googlemaps.Client(key=api_key)
    
    def get_distance_matrix(
        self, 
        origins: List[Tuple[float, float]], 
        destinations: List[Tuple[float, float]],
        mode: str = "driving"
    ) -> Dict[str, Any]:
        """
        Get distance and duration matrix between origins and destinations.
        
        Args:
            origins: List of (lat, lng) tuples
            destinations: List of (lat, lng) tuples
            mode: Travel mode (driving, walking, bicycling, transit)
        
        Returns:
            Dict with 'distances' and 'durations' matrices
        """
        # Format locations for API
        origins_formatted = [f"{lat},{lng}" for lat, lng in origins]
        destinations_formatted = [f"{lat},{lng}" for lat, lng in destinations]
        
        result = self.client.distance_matrix(
            origins=origins_formatted,
            destinations=destinations_formatted,
            mode=mode,
            units="metric"
        )
        
        # Parse results into matrices
        n_origins = len(origins)
        n_destinations = len(destinations)
        
        distances = [[0] * n_destinations for _ in range(n_origins)]
        durations = [[0] * n_destinations for _ in range(n_origins)]
        
        for i, row in enumerate(result.get("rows", [])):
            for j, element in enumerate(row.get("elements", [])):
                if element.get("status") == "OK":
                    distances[i][j] = element.get("distance", {}).get("value", 0)  # meters
                    durations[i][j] = element.get("duration", {}).get("value", 0)  # seconds
                else:
                    # Fallback to haversine distance if API fails
                    distances[i][j] = int(self._haversine_distance(
                        origins[i][0], origins[i][1],
                        destinations[j][0], destinations[j][1]
                    ) * 1000)  # km to meters
                    durations[i][j] = int(distances[i][j] / 13.89)  # ~50 km/h average
        
        return {
            "distances": distances,  # in meters
            "durations": durations,  # in seconds
            "raw_result": result
        }
    
    def get_full_matrix(
        self, 
        locations: List[Tuple[float, float]],
        mode: str = "driving"
    ) -> Dict[str, Any]:
        """
        Get a square distance/duration matrix for all locations.
        Handles API limits by batching requests.
        """
        n = len(locations)
        
        # Google Distance Matrix API has limits:
        # - Max 25 origins or destinations per request
        # - Max 100 elements per request
        # For simplicity, if n <= 10, do one request
        
        if n <= 10:
            return self.get_distance_matrix(locations, locations, mode)
        
        # For larger matrices, we need to batch
        # This is a simplified version - production should handle this better
        batch_size = 10
        distances = [[0] * n for _ in range(n)]
        durations = [[0] * n for _ in range(n)]
        
        for i_start in range(0, n, batch_size):
            i_end = min(i_start + batch_size, n)
            for j_start in range(0, n, batch_size):
                j_end = min(j_start + batch_size, n)
                
                origins = locations[i_start:i_end]
                destinations = locations[j_start:j_end]
                
                result = self.get_distance_matrix(origins, destinations, mode)
                
                for i_local, i_global in enumerate(range(i_start, i_end)):
                    for j_local, j_global in enumerate(range(j_start, j_end)):
                        distances[i_global][j_global] = result["distances"][i_local][j_local]
                        durations[i_global][j_global] = result["durations"][i_local][j_local]
        
        return {
            "distances": distances,
            "durations": durations
        }
    
    @staticmethod
    def _haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate haversine distance between two points in km"""
        R = 6371  # Earth's radius in km
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)
        
        a = (math.sin(delta_lat/2)**2 + 
             math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon/2)**2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c


def calculate_haversine_matrix(locations: List[Tuple[float, float]]) -> List[List[float]]:
    """
    Calculate full distance matrix using haversine formula.
    Useful when API calls need to be minimized or for testing.
    
    Returns distances in meters.
    """
    n = len(locations)
    matrix = [[0] * n for _ in range(n)]
    
    for i in range(n):
        for j in range(n):
            if i != j:
                dist = DistanceMatrixClient._haversine_distance(
                    locations[i][0], locations[i][1],
                    locations[j][0], locations[j][1]
                )
                matrix[i][j] = int(dist * 1000)  # Convert to meters
    
    return matrix
