#!/usr/bin/env python3
"""
Classification Pipeline v2 - Using Hermes vision_analyze via ollama-cloud/gemma4:31b
- Downloads 4 headings per stop
- Uploads to web server
- Returns URLs for classification
- Saves progress to JSON (actual classification via Hermes vision tool)
"""

import json
import urllib.request
import os
import time
import ftplib
from datetime import datetime

from config_local import API_KEY
BASE_DIR = "/home/roberto/Desktop/GitHub/00-active/galicia-marquesinas"
IMG_DIR = os.path.join(BASE_DIR, "sv_4dir")
GEOJSON = os.path.join(BASE_DIR, "stops.geojson")
URLS_FILE = os.path.join(BASE_DIR, "classification_urls.json")
CLASS_LOG = os.path.join(BASE_DIR, "classification_results.json")

for prov in ["A Coruña", "Pontevedra", "Lugo", "Ourense"]:
    os.makedirs(os.path.join(IMG_DIR, prov), exist_ok=True)

with open(GEOJSON) as f:
    gtfs = json.load(f)

# FTP config
FTP_HOST = "134.0.11.237"
FTP_USER = "robertoad3"
FTP_PASS = "Roberto.1993"
WEB_BASE = "https://robertoalmela.com/marquesinas_galicia/sv_classify"

# Find stops that need classification (from the 5000 with SV)
need_classify = []
for i, feat in enumerate(gtfs['features']):
    props = feat['properties']
    if props.get('ai_classification') or props.get('classification_status') == 'done':
        continue
    # Must have SV coverage (either from our download or sv_available)
    if props.get('street_view_coverage') == True or props.get('sv_image'):
        need_classify.append((i, feat))

print(f"Stops needing classification: {len(need_classify)}")

# Process in batches of 50
BATCH_SIZE = 50
TOTAL = min(BATCH_SIZE, len(need_classify))  # Start with 50
print(f"Processing batch: {TOTAL} stops")
print()

ftp = ftplib.FTP(FTP_HOST, FTP_USER, FTP_PASS)

# Create remote directory
for prov in ["A_Coruna", "Pontevedra", "Lugo", "Ourense"]:
    try:
        ftp.mkd(f"/web/marquesinas_galicia/sv_classify/{prov}")
    except:
        pass

stats = {'downloaded': 0, 'uploaded': 0, 'cost_imgs': 0.0}
url_map = {}  # stop_idx -> {heading: url}
start = datetime.now()

for batch_idx, (i, feat) in enumerate(need_classify[:TOTAL]):
    props = feat['properties']
    coords = feat['geometry']['coordinates']
    lat, lon = coords[1], coords[0]
    prov = props.get('province', 'Ourense')
    prov_dir = prov.replace('ñ', 'n').replace(' ', '_')
    
    headings = [0, 90, 180, 270]
    stop_urls = {}
    
    for h in headings:
        fname = f"stop_{i}_h{h}.jpg"
        local_prov_dir = os.path.join(IMG_DIR, prov)
        fpath = os.path.join(local_prov_dir, fname)
        
        # Download if not exists
        if not (os.path.exists(fpath) and os.path.getsize(fpath) > 1000):
            url = f"https://maps.googleapis.com/maps/api/streetview?size=640x640&location={lat},{lon}&radius=50&heading={h}&fov=90&pitch=-10&key={API_KEY}"
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "MarquesinasGalicia/1.0"})
                with urllib.request.urlopen(req, timeout=15) as resp:
                    img_data = resp.read()
                with open(fpath, 'wb') as f:
                    f.write(img_data)
                stats['downloaded'] += 1
                stats['cost_imgs'] += 0.007
            except:
                continue
        else:
            img_data = open(fpath, 'rb').read()
        
        # Upload to FTP
        try:
            remote_path = f"/web/marquesinas_galicia/sv_classify/{prov_dir}/{fname}"
            with open(fpath, 'rb') as f:
                ftp.storbinary(f'STOR {remote_path}', f)
            web_url = f"{WEB_BASE}/{prov_dir}/{fname}"
            stop_urls[h] = web_url
            stats['uploaded'] += 1
        except Exception as e:
            pass
    
    url_map[i] = stop_urls
    
    if (batch_idx + 1) % 10 == 0:
        elapsed = (datetime.now() - start).total_seconds()
        rate = (batch_idx + 1) / elapsed
        eta = (TOTAL - batch_idx - 1) / rate / 60
        print(f"  [{batch_idx+1:3d}/{TOTAL}] Downloaded: {stats['downloaded']} | Uploaded: {stats['uploaded']} | Cost: ${stats['cost_imgs']:.2f} | Rate: {rate:.1f}/s | ETA: {eta:.0f}min")

ftp.quit()

# Save URL map for classification
with open(URLS_FILE, 'w') as f:
    json.dump(url_map, f, indent=2)

elapsed = (datetime.now() - start).total_seconds()
print(f"\n{'='*60}")
print(f"=== DOWNLOAD & UPLOAD COMPLETE ===")
print(f"Time: {elapsed/60:.1f} min")
print(f"Stops: {TOTAL}")
print(f"Images downloaded: {stats['downloaded']}")
print(f"Images uploaded: {stats['uploaded']}")
print(f"Cost images: ${stats['cost_imgs']:.2f} (real: $0)")
print(f"URLs saved to: {URLS_FILE}")
print(f"\nNext: Run classification using vision_analyze on the URLs")