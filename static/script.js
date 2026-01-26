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
        updateStatus('Waiting for GPS fix...');

        // Poll the server for GPS location every 2 seconds
        setInterval(async () => {
            try {
                const response = await fetch('/api/location');
                const data = await response.json();

                // check if valid data (simple check for 0,0 default)
                if (data.lat === 0 && data.lng === 0) {
                    updateStatus('Waiting for GPS lock...', true); // warning color
                    return;
                }

                userLocation = { lat: data.lat, lng: data.lng };

                // Add/Move User Marker
                if (userMarker) {
                    userMarker.setLatLng([data.lat, data.lng]);
                } else {
                    // Custom Icon for User
                    const userIcon = L.divIcon({
                        className: 'user-pin',
                        html: `<div style="background-color: #00f2ff; width: 16px; height: 16px; border-radius: 50%; box-shadow: 0 0 15px #00f2ff; border: 3px solid white;"></div>`,
                        iconSize: [22, 22],
                        iconAnchor: [11, 11]
                    });

                    userMarker = L.marker([data.lat, data.lng], { icon: userIcon }).addTo(map);
                    userMarker.bindPopup("<b>You are here</b>").openPopup();

                    // Center map on first fix
                    map.setView([data.lat, data.lng], DEFAULT_ZOOM);
                }

                // If looking at status text, update it unless we have a route
                if (!destinationLocation) {
                    updateStatus('GPS Fix Acquired. Pin a destination.');
                }

            } catch (error) {
                console.error('Error fetching GPS data:', error);
                updateStatus('Connection lost to GPS server', true);
            }
        }, 2000); // 2 second interval
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
    startTravelBtn.addEventListener('click', startTravel);
    stopTravelBtn.addEventListener('click', stopTravel);

    async function startTravel() {
        if (!destinationLocation) return;

        startTravelBtn.classList.add('hidden');
        stopTravelBtn.classList.remove('hidden');
        updateStatus('Autonomous Travel Started! 🚀');

        try {
            await fetch('/api/navigate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(destinationLocation)
            });
        } catch (error) {
            console.error(error);
            updateStatus('Failed to start navigation', true);
        }
    }

    async function stopTravel() {
        startTravelBtn.classList.remove('hidden');
        stopTravelBtn.classList.add('hidden');
        updateStatus('Travel Stopped by User');

        try {
            await fetch('/api/stop', { method: 'POST' });
        } catch (error) {
            console.error(error);
        }
    }

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
            updateStatus('Route calculated! Ready to Travel.');

            // Enable Travel Button
            startTravelBtn.classList.remove('hidden');

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
