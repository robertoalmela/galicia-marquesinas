#!/usr/bin/env python3
"""
Street View Download v2 - Parallel (3 workers)
5.000 stops → ~20 min instead of ~60 min
Cost: $0 (free tier)
"""

import json
import urllib.request
import os
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

from config_local import API_KEY
BASE_DIR = "/home/roberto/Desktop/GitHub/00-active/galicia-marquesinas"
IMG_DIR = os.path.join(BASE_DIR, "street_view")
PROGRESS_FILE = os.path.join(BASE_DIR, "sv_progress_v2.json")

for prov in ["A Coruña", "Pontevedra", "Lugo", "Ourense"]:
    os.makedirs(os.path.join(IMG_DIR, prov), exist_ok=True)

with open(os.path.join(BASE_DIR, 'stops.geojson')) as f:
    gtfs = json.load(f)

# Find unverified stops
unverified = []
for i, feat in enumerate(gtfs['features']):
    vs = feat['properties'].get('validation_status', 'unverified')
    if vs not in ('validated', 'no_shelter'):
        unverified.append((i, feat))

print(f"Paradas sin validar: {len(unverified)}")
print(f"Procesando: primeras 5.000")

batch = unverified[:5000]

# Load progress
def load_progress():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE) as f:
            return json.load(f)
    return {'completed': [], 'failed': [], 'no_sv': []}

progress = load_progress()
completed_set = set(progress['completed'])
failed_set = set(progress['failed'])
no_sv_set = set(progress['no_sv'])

stats = {'sv_ok': 0, 'sv_no': 0, 'downloaded': 0, 'download_fail': 0, 'cost': 0.0}
lock_progress = __import__('threading').Lock()
start_time = datetime.now()

def process_stop(item):
    idx, feat = item
    props = feat['properties']
    coords = feat['geometry']['coordinates']
    lat, lon = coords[1], coords[0]
    stop_id = props.get('stop_id', f'stop_{idx}')
    prov = props.get('province', 'Ourense')
    
    result = {'stop_id': stop_id, 'sv_ok': False, 'downloaded': False, 'cost': 0.0}
    
    # Step 1: Metadata check
    meta_url = f"https://maps.googleapis.com/maps/api/streetview/metadata?location={lat},{lon}&radius=50&key={API_KEY}"
    try:
        req = urllib.request.Request(meta_url, headers={'User-Agent': 'MarquesinasGalicia/1.0'})
        with urllib.request.urlopen(req, timeout=10) as resp:
            meta = json.loads(resp.read())
        result['cost'] += 0.005
        
        if meta.get('status') != 'OK':
            result['sv_ok'] = False
            feat['properties']['street_view_coverage'] = False
            feat['properties']['validation_status'] = 'no_sv'
            return result
        
        result['sv_ok'] = True
        pano_id = meta.get('pano_id', '')
        date = meta.get('date', '')
    except Exception:
        return result
    
    # Step 2: Download image
    img_filename = f"{stop_id}.jpg"
    img_path = os.path.join(IMG_DIR, prov, img_filename)
    
    # Skip if already downloaded
    if os.path.exists(img_path) and os.path.getsize(img_path) > 1000:
        result['downloaded'] = True
        result['cost'] += 0.007
        feat['properties']['street_view_coverage'] = True
        feat['properties']['sv_pano_id'] = pano_id
        feat['properties']['sv_date'] = date
        feat['properties']['sv_image'] = img_filename
        if feat['properties'].get('validation_status') == 'unverified':
            feat['properties']['validation_status'] = 'sv_available'
        return result
    
    img_url = f"https://maps.googleapis.com/maps/api/streetview?size=640x640&location={lat},{lon}&radius=50&heading=0&fov=90&pitch=0&key={API_KEY}"
    
    try:
        req = urllib.request.Request(img_url, headers={'User-Agent': 'MarquesinasGalicia/1.0'})
        with urllib.request.urlopen(req, timeout=15) as resp:
            img_data = resp.read()
        
        with open(img_path, 'wb') as f:
            f.write(img_data)
        
        result['downloaded'] = True
        result['cost'] += 0.007
        feat['properties']['street_view_coverage'] = True
        feat['properties']['sv_pano_id'] = pano_id
        feat['properties']['sv_date'] = date
        feat['properties']['sv_image'] = img_filename
        if feat['properties'].get('validation_status') == 'unverified':
            feat['properties']['validation_status'] = 'sv_available'
    except Exception:
        result['download_fail'] = True
    
    return result

# Filter out already completed
remaining = [(i, f) for i, f in batch if f['properties'].get('stop_id', f'stop_{i}') not in completed_set]
print(f"Restantes por procesar: {len(remaining)}")

count = 0
with ThreadPoolExecutor(max_workers=3) as executor:
    futures = {executor.submit(process_stop, item): item for item in remaining}
    
    for future in as_completed(futures):
        count += 1
        result = future.result()
        stop_id = result['stop_id']
        
        if result['sv_ok']:
            stats['sv_ok'] += 1
        else:
            stats['sv_no'] += 1
        
        if result.get('downloaded'):
            stats['downloaded'] += 1
        if result.get('download_fail'):
            stats['download_fail'] += 1
        
        stats['cost'] += result['cost']
        
        # Track progress
        if result['sv_ok'] and not result.get('downloaded') and not result.get('download_fail'):
            # Has SV but not downloaded (already existed or will retry)
            progress['completed'].append(stop_id)
        elif result['sv_ok']:
            progress['completed'].append(stop_id)
        elif not result['sv_ok']:
            progress['no_sv'].append(stop_id)
        
        # Progress report every 100
        if count % 100 == 0:
            elapsed = (datetime.now() - start_time).total_seconds()
            rate = count / elapsed if elapsed > 0 else 0
            eta = (len(remaining) - count) / rate / 60 if rate > 0 else 0
            print(f"  [{count:5d}/{len(remaining)}] "
                  f"SV: {stats['sv_ok']}✅ {stats['sv_no']}❌ | "
                  f"Img: {stats['downloaded']}↓ | "
                  f"Coste: ${stats['cost']:.2f} | "
                  f"Rate: {rate:.1f}/s | ETA: {eta:.0f}min")
            
            # Save progress
            with open(PROGRESS_FILE, 'w') as f:
                json.dump(progress, f)

# Save progress
with open(PROGRESS_FILE, 'w') as f:
    json.dump(progress, f)

# Save enriched GeoJSON
with open(os.path.join(BASE_DIR, 'stops.geojson'), 'w') as f:
    json.dump(gtfs, f, ensure_ascii=False)

# Final summary
elapsed = (datetime.now() - start_time).total_seconds()
total_images = sum(len(os.listdir(os.path.join(IMG_DIR, prov))) for prov in ["A Coruña", "Pontevedra", "Lugo", "Ourense"])
du = os.popen(f"du -sh {IMG_DIR}").read().strip()

print(f"\n{'='*60}")
print(f"=== RESUMEN FINAL ===")
print(f"Tiempo: {elapsed/60:.1f} min")
print(f"Procesadas: {count}")
print(f"Con Street View: {stats['sv_ok']} ({stats['sv_ok']/count*100:.1f}%)" if count else "")
print(f"Sin Street View: {stats['sv_no']} ({stats['sv_no']/count*100:.1f}%)" if count else "")
print(f"Imágenes descargadas: {total_images} total")
print(f"Espacio en disco: {du}")
print(f"Coste API: ${stats['cost']:.2f}")
print(f"Coste real: $0.00 (crédito gratuito)")
print(f"")
print(f"--- PROYECCIÓN 22.706 paradas ---")
factor = 22706 / max(count, 1)
print(f"Imágenes totales estimadas: ~{int(stats['sv_ok']*factor):,}")
print(f"Espacio estimado: ~{int(total_images*factor/1000*80):,}MB")
print(f"Coste total proyectado: ${stats['cost']*factor:.2f} (real: $0.00)")