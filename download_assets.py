import requests
import os

assets = [
    ("https://unpkg.com/leaflet@1.9.4/dist/leaflet.css", "static/vendor/leaflet.css"),
    ("https://unpkg.com/leaflet@1.9.4/dist/leaflet.js", "static/vendor/leaflet.js"),
    ("https://cdnjs.cloudflare.com/ajax/libs/nipplejs/0.10.1/nipplejs.min.js", "static/vendor/nipplejs.min.js")
]

os.makedirs("static/vendor", exist_ok=True)

for url, path in assets:
    print(f"Downloading {url} to {path}...")
    try:
        r = requests.get(url)
        if r.status_code == 200:
            with open(path, 'wb') as f:
                f.write(r.content)
            print("Success!")
        else:
            print(f"Failed: Status {r.status_code}")
    except Exception as e:
        print(f"Error: {e}")
