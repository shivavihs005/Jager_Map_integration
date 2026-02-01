import requests
import time

class MapMatcher:
    def __init__(self):
        self.osrm_url = "http://router.project-osrm.org/nearest/v1/driving/{},{}"
        self.last_request_time = 0
        self.request_interval = 1.0 # 1 second between requests to be polite

    def match_to_road(self, lat, lng):
        """
        Snaps the given lat/lng to the nearest road using OSRM.
        Returns (snapped_lat, snapped_lng) or None if failed.
        """
        # Rate Limiting
        current_time = time.time()
        if current_time - self.last_request_time < self.request_interval:
            return None
        
        self.last_request_time = current_time

        try:
            # OSRM expects {lng},{lat}
            url = self.osrm_url.format(lng, lat)
            response = requests.get(url, timeout=2)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('code') == 'Ok' and data.get('waypoints'):
                    # Get the location of the first waypoint (nearest)
                    location = data['waypoints'][0]['location']
                    # API returns [lng, lat]
                    snapped_lng, snapped_lat = location
                    return snapped_lat, snapped_lng
        except requests.RequestException:
            # Silently fail on connection errors (common if offline)
            return None
        except Exception as e:
            print(f"[MapMatcher] Unexpected Error: {e}")
            return None
            
        return None

# Global instance
map_matcher = MapMatcher()
