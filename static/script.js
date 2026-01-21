document.addEventListener('DOMContentLoaded', () => {
    // --- Configuration ---
    const DEFAULT_ZOOM = 13;
    const OSRM_API_URL = 'https://router.project-osrm.org/route/v1/driving/';
    
    // --- State ---
    let map;
    let userMarker = null;
    let destinationMarker = null;
    let routePolyline = null;
    let userLocation = null; // { lat, lng }
    let destinationLocation = null; // { lat, lng }

    // --- DOM Elements ---
    const statusText = document.getElementById('status-text');
    const calcBtn = document.getElementById('calc-route-btn');
    const resetBtn = document.getElementById('reset-btn');
    const tripInfo = document.getElementById('trip-info');
    const distanceValue = document.getElementById('distance-value');
    const loader = document.getElementById('loader');

    // --- Initialization ---
    initMap();
    locateUser();

    function initMap() {
        // Initialize with a default view until we find the user
        map = L.map('map').setView([0, 0], 2);

        // Add Dark Matter Tiles for premium look
        L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
            subdomains: 'abcd',
            maxZoom: 20
        }).addTo(map);

        // Map Click Event -> Pin Destination
        map.on('click', (e) => {
            handleMapClick(e.latlng);
        });
    }

    function locateUser() {
        if (!navigator.geolocation) {
            updateStatus('Geolocation not supported', true);
            return;
        }

        updateStatus('Locating you...');
        
        navigator.geolocation.getCurrentPosition(
            (position) => {
                const { latitude, longitude } = position.coords;
                userLocation = { lat: latitude, lng: longitude };
                
                // Add/Move User Marker
                if (userMarker) {
                    userMarker.setLatLng([latitude, longitude]);
                } else {
                    // Custom Icon for User
                    const userIcon = L.divIcon({
                        className: 'user-pin',
                        html: `<div style="background-color: #00f2ff; width: 16px; height: 16px; border-radius: 50%; box-shadow: 0 0 15px #00f2ff; border: 3px solid white;"></div>`,
                        iconSize: [22, 22],
                        iconAnchor: [11, 11]
                    });

                    userMarker = L.marker([latitude, longitude], { icon: userIcon }).addTo(map);
                    userMarker.bindPopup("<b>You are here</b>").openPopup();
                }

                // Center map
                map.setView([latitude, longitude], DEFAULT_ZOOM);
                updateStatus('Location found. Pin a destination.');
            },
            (error) => {
                console.error(error);
                updateStatus('Unable to retrieve location', true);
                // Fallback location (e.g., New York) if needed, or just let user scroll
                map.setView([40.7128, -74.0060], 10);
            },
            { enableHighAccuracy: true }
        );
    }

    function handleMapClick(latlng) {
        if (!userLocation) {
            alert("Please wait for your location to be detected first.");
            return;
        }

        // Update Destination State
        destinationLocation = latlng;

        // Visual Feedback (Marker)
        if (destinationMarker) {
            destinationMarker.setLatLng(latlng);
        } else {
            const destIcon = L.divIcon({
                className: 'dest-pin',
                html: `<div style="background-color: #ff4757; width: 20px; height: 20px; transform: rotate(45deg); border-radius: 4px 50% 50% 50%; border: 3px solid white; box-shadow: 0 0 10px #ff4757;"></div>`,
                iconSize: [26, 26],
                iconAnchor: [13, 26]
            });
            destinationMarker = L.marker(latlng, { icon: destIcon }).addTo(map);
        }

        // Enable Button
        calcBtn.disabled = false;
        updateStatus('Destination pinned. Ready to route.');
        
        // Clear previous route if any
        if (routePolyline) {
            map.removeLayer(routePolyline);
            routePolyline = null;
            tripInfo.classList.add('hidden');
        }
    }

    // --- Logic ---
    calcBtn.addEventListener('click', calculateRoute);

    async function calculateRoute() {
        if (!userLocation || !destinationLocation) return;

        loader.classList.remove('hidden');
        updateStatus('Calculating shortest path...');

        const start = `${userLocation.lng},${userLocation.lat}`;
        const end = `${destinationLocation.lng},${destinationLocation.lat}`;
        const url = `${OSRM_API_URL}${start};${end}?overview=full&geometries=geojson`;

        try {
            const response = await fetch(url);
            const data = await response.json();

            if (data.code !== 'Ok') {
                throw new Error('No route found');
            }

            const route = data.routes[0];
            const geometry = route.geometry;
            const distanceMeters = route.distance;
            const distanceKm = (distanceMeters / 1000).toFixed(2);

            drawRoute(geometry);
            showStats(distanceKm);
            updateStatus('Route calculated!');

        } catch (error) {
            console.error(error);
            updateStatus('Error calculating route', true);
            alert('Could not calculate route. Try a closer point or check connection.');
        } finally {
            loader.classList.add('hidden');
        }
    }

    function drawRoute(geojson) {
        if (routePolyline) map.removeLayer(routePolyline);

        // Flip coordinates for Leaflet (GeoJSON is Lng,Lat; Leaflet needs Lat,Lng)
        // Actually L.geoJSON handles this automatically usually, but if we use raw coordinates:
        // Leaflet's L.geoJSON handles GeoJSON geometry natively.
        
        routePolyline = L.geoJSON(geojson, {
            style: {
                color: '#00f2ff',
                weight: 5,
                opacity: 0.8,
                lineCap: 'round'
            }
        }).addTo(map);

        // Fit bounds to show entire route
        map.fitBounds(routePolyline.getBounds(), { padding: [50, 50] });
    }

    function showStats(km) {
        distanceValue.innerText = `${km} km`;
        tripInfo.classList.remove('hidden');
    }

    resetBtn.addEventListener('click', () => {
        if (destinationMarker) map.removeLayer(destinationMarker);
        if (routePolyline) map.removeLayer(routePolyline);
        destinationLocation = null;
        calcBtn.disabled = true;
        tripInfo.classList.add('hidden');
        destinationMarker = null;
        updateStatus('Map reset. Pin a destination.');
        
        // Recenter on user
        if (userLocation) {
            map.setView([userLocation.lat, userLocation.lng], DEFAULT_ZOOM);
        }
    });

    function updateStatus(msg, isError = false) {
        statusText.innerText = msg;
        statusText.style.color = isError ? '#ff4757' : '#ffffff';
    }
});
