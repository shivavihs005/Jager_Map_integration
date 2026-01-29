const map = L.map('map').setView([0, 0], 2);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© OpenStreetMap contributors'
}).addTo(map);

const marker = L.marker([0, 0]).addTo(map);
let firstFix = false;

function updateGPS() {
    fetch('/api/gps')
        .then(response => response.json())
        .then(data => {
            const lat = data.lat;
            const lng = data.lng;

            document.getElementById('lat').textContent = lat.toFixed(6);
            document.getElementById('lng').textContent = lng.toFixed(6);

            if (lat !== 0 || lng !== 0) {
                document.getElementById('status').textContent = "LOCKED";
                document.getElementById('status').style.color = "green";

                const newLatLng = new L.LatLng(lat, lng);
                marker.setLatLng(newLatLng);

                if (!firstFix) {
                    map.setView(newLatLng, 15);
                    firstFix = true;
                } else {
                    map.panTo(newLatLng);
                }
            } else {
                document.getElementById('status').textContent = "SEARCHING...";
                document.getElementById('status').style.color = "orange";
            }
        })
        .catch(error => {
            console.error('Error fetching GPS:', error);
            document.getElementById('status').textContent = "ERROR";
            document.getElementById('status').style.color = "red";
        });
}

// Update every second
setInterval(updateGPS, 1000);
