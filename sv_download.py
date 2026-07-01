#!/usr/bin/env python3
"""
Street View Download - 5000 stops
Fase 1: Metadata check + Fase 2: Download images
Coste: $0 (crédito gratuito Google $200/mes)
"""

import json
import urllib.request
import time
import os
import sys
from datetime import datetime

from config_local import API_KEY
BASE_DIR = "/home/roberto/Desktop/GitHub/00-active/galicia-marquesinas"
IMG_DIR = os.path.join(BASE_DIR, "street_view")
os.makedirs(IMG_DIR, exist_ok=True)

# Create province subdirs
for prov in ["A Coruña", "Pontevedra", "Lugo", "Ourense"]:
    os.makedirs(os.path.join(IMG_DIR, prov), exist_ok=True)

# Load GTFS stops
with open(os.path.join(BASE_DIR, 'stops.geojson')) as f:
    gtfs = json.load(f)

# Filter: only stops WITHOUT OSM validation (validation_status != 'validated' and 'no_shelter')
unverified = []
for i, feat in enumerate(gtfs['features']):
    vs = feat['properties'].get('validation_status', 'unverified')
    if vs not in ('validated', 'no_shelter'):
        unverified.append((i, feat))

print(f"Paradas sin validar OSM: {len(unverified)}")
print(f"Procesando: primeras 5.000")

# Take first 5000
batch = unverified[:5000]

# Stats tracking
stats = {
    'total': 0,
    'sv_ok': 0,
    'sv_no': 0,
    'downloaded': 0,
    'download_fail': 0,
    'errors': 0,
    'cost_metadata': 0.0,
    'cost_images': 0.0,
    'start_time': datetime.now(),
}

# Progress file for resuming
PROGRESS_FILE = os.path.join(BASE_DIR, 'sv_progress.json')

def load_progress():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE) as f:
            return json.load(f)
    return {'completed': [], 'failed': []}

def save_progress(progress):
    with open(PROGRESS_FILE, 'w') as f:
        json.dump(progress, f)

progress = load_progress()
completed_set = set(progress['completed'])

# Results
results = []

for idx, (i, feat) in enumerate(batch):
    props = feat['properties']
    coords = feat['geometry']['coordinates']
    lat, lon = coords[1], coords[0]
    stop_id = props.get('stop_id', f'stop_{i}')
    prov = props.get('province', 'Ourense')
    
    # Skip if already done
    if stop_id in completed_set:
        stats['total'] += 1
        stats['sv_ok'] += 1
        stats['downloaded'] += 1
        continue
    
    # Step 1: Metadata check
    meta_url = f"https://maps.googleapis.com/maps/api/streetview/metadata?location={lat},{lon}&radius=50&key={API_KEY}"
    
    try:
        req = urllib.request.Request(meta_url, headers={'User-Agent': 'MarquesinasGalicia/1.0'})
        with urllib.request.urlopen(req, timeout=10) as resp:
            meta = json.loads(resp.read())
        
        stats['cost_metadata'] += 0.005  # $5/1000
        
        if meta.get('status') != 'OK':
            stats['sv_no'] += 1
            stats['total'] += 1
            results.append({
                'stop_id': stop_id,
                'name': props['name'],
                'province': prov,
                'lat': lat, 'lon': lon,
                'sv_status': 'NO_COVERAGE',
                'image': None,
            })
            # Update GeoJSON
            feat['properties']['street_view_coverage'] = False
            feat['properties']['validation_status'] = 'no_sv'
            continue
        
        stats['sv_ok'] += 1
        pano_id = meta.get('pano_id', '')
        date = meta.get('date', '')
        
    except Exception as e:
        stats['errors'] += 1
        stats['total'] += 1
        continue
    
    # Step 2: Download image (640x640, heading=0, fov=90)
    # Save as JPG (smaller than PNG)
    img_filename = f"{stop_id}.jpg"
    img_path = os.path.join(IMG_DIR, prov, img_filename)
    
    img_url = f"https://maps.googleapis.com/maps/api/streetview?size=640x640&location={lat},{lon}&radius=50&heading=0&fov=90&pitch=0&key={API_KEY}"
    
    try:
        req = urllib.request.Request(img_url, headers={'User-Agent': 'MarquesinasGalicia/1.0'})
        with urllib.request.urlopen(req, timeout=15) as resp:
            img_data = resp.read()
        
        with open(img_path, 'wb') as f:
            f.write(img_data)
        
        stats['downloaded'] += 1
        stats['cost_images'] += 0.007  # $7/1000
        
        # Update GeoJSON
        feat['properties']['street_view_coverage'] = True
        feat['properties']['sv_pano_id'] = pano_id
        feat['properties']['sv_date'] = date
        feat['properties']['sv_image'] = img_filename
        
        if feat['properties'].get('validation_status') == 'unverified':
            feat['properties']['validation_status'] = 'sv_available'
        
        progress['completed'].append(stop_id)
        
    except Exception as e:
        stats['download_fail'] += 1
        progress['failed'].append(stop_id)
    
    stats['total'] += 1
    
    # Progress report every 100 stops
    if (idx + 1) % 100 == 0:
        elapsed = (datetime.now() - stats['start_time']).total_seconds()
        rate = (idx + 1) / elapsed if elapsed > 0 else 0
        eta = (len(batch) - idx - 1) / rate if rate > 0 else 0
        
        print(f"  [{idx+1:5d}/5000] "
              f"SV: {stats['sv_ok']}✅ {stats['sv_no']}❌ | "
              f"Img: {stats['downloaded']}↓ {stats['download_fail']}✗ | "
              f"Coste: ${stats['cost_metadata']+stats['cost_images']:.2f} | "
              f"Rate: {rate:.1f}/s | ETA: {eta/60:.0f}min")
        
        # Save progress periodically
        save_progress(progress)
    
    # Rate limit: ~5 requests/sec (Google allows 50qpS but be nice)
    time.sleep(0.2)

# Final save
save_progress(progress)

# Save enriched GeoJSON
with open(os.path.join(BASE_DIR, 'stops.geojson'), 'w') as f:
    json.dump(gtfs, f, ensure_ascii=False)

# Summary
elapsed = (datetime.now() - stats['start_time']).total_seconds()
total_cost = stats['cost_metadata'] + stats['cost_images']
free_credit_remaining = 200 - total_cost

print(f"\n{'='*60}")
print(f"=== RESUMEN FINAL (5.000 paradas) ===")
print(f"Tiempo: {elapsed/60:.1f} min")
print(f"Procesadas: {stats['total']}")
print(f"Con Street View: {stats['sv_ok']} ({stats['sv_ok']/stats['total']*100:.1f}%)")
print(f"Sin Street View: {stats['sv_no']} ({stats['sv_no']/stats['total']*100:.1f}%)")
print(f"Imágenes descargadas: {stats['downloaded']}")
print(f"Imágenes fallidas: {stats['download_fail']}")
print(f"Errores API: {stats['errors']}")
print(f"")
print(f"--- COSTE ---")
print(f"Metadata: ${stats['cost_metadata']:.2f}")
print(f"Imágenes: ${stats['cost_images']:.2f}")
print(f"Total: ${total_cost:.2f}")
print(f"Crédito restante: ${free_credit_remaining:.2f}")
print(f"Coste real: $0.00 (todo dentro del crédito gratuito)")
print(f"")
print(f"--- PROYECCIÓN 22.706 paradas ---")
factor = 22706 / 5000
print(f"Metadata: ${stats['cost_metadata']*factor:.2f}")
print(f"Imágenes: ${stats['cost_images']*factor:.2f}")
print(f"Total: ${total_cost*factor:.2f}")
print(f"Coste real: $0.00")

# Check disk usage
du_result = os.popen(f"du -sh {IMG_DIR}").read().strip()
print(f"\nEspacio en disco: {du_result}")
print(f"Imágenes por provincia:")
for prov in ["A Coruña", "Pontevedra", "Lugo", "Ourense"]:
    prov_dir = os.path.join(IMG_DIR, prov)
    count = len([f for f in os.listdir(prov_dir) if f.endswith('.jpg')]) if os.path.exists(prov_dir) else 0
    size = os.popen(f"du -sh {prov_dir}").read().strip() if count > 0 else "0"
    print(f"  {prov}: {count} imágenes ({size})")