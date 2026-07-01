#!/usr/bin/env python3
"""
Street View METADATA CHECK - ALL unverified stops
Sin descarga de imágenes. Solo verifica cobertura.
Coste: $0 (metadata es gratis con crédito)
Tiempo estimado: ~30-45 min para 22.706 paradas
"""

import json
import urllib.request
import time
import os
import sys
from datetime import datetime

BASE_DIR = "/home/roberto/Desktop/GitHub/00-active/galicia-marquesinas"

with open(os.path.join(BASE_DIR, 'stops.geojson')) as f:
    gtfs = json.load(f)

# Find stops that need SV coverage check
need_check = []
for i, feat in enumerate(gtfs['features']):
    vs = feat['properties'].get('validation_status', 'unverified')
    svc = feat['properties'].get('street_view_coverage')
    if svc is None and vs not in ('validated', 'validated_no_shelter'):
        need_check.append((i, feat))

print(f"Paradas sin check de Street View: {len(need_check)}")

PROGRESS_FILE = os.path.join(BASE_DIR, 'sv_metadata_progress.json')

def load_progress():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE) as f:
            return json.load(f)
    return {'checked': []}

def save_progress(progress):
    with open(PROGRESS_FILE, 'w') as f:
        json.dump(progress, f)


progress = load_progress()
checked_set = set(progress['checked'])

stats = {
    'total': 0, 'sv_ok': 0, 'sv_no': 0, 'errors': 0,
    'skipped': 0, 'start': datetime.now()
}

# Save every 200 stops
SAVE_INTERVAL = 200

for idx, (i, feat) in enumerate(need_check):
    props = feat['properties']
    coords = feat['geometry']['coordinates']
    lat, lon = coords[1], coords[0]
    stop_id = props.get('stop_id', f'stop_{i}')
    
    if stop_id in checked_set:
        stats['skipped'] += 1
        continue
    
    api_key = os.environ.get('GMAPS_KEY', '')
    meta_url = f"https://maps.googleapis.com/maps/api/streetview/metadata?location={lat},{lon}&radius=50&key={api_key}"
    
    try:
        req = urllib.request.Request(meta_url, headers={'User-Agent': 'MarquesinasGalicia/1.0'})
        with urllib.request.urlopen(req, timeout=10) as resp:
            meta = json.loads(resp.read())
        
        if meta.get('status') == 'OK':
            props['street_view_coverage'] = True
            props['sv_pano_id'] = meta.get('pano_id', '')
            props['sv_date'] = meta.get('date', '')
            if props.get('validation_status') == 'unverified':
                props['validation_status'] = 'sv_available'
            stats['sv_ok'] += 1
        else:
            props['street_view_coverage'] = False
            if props.get('validation_status') == 'unverified':
                props['validation_status'] = 'no_sv'
            stats['sv_no'] += 1
    
    except Exception as e:
        stats['errors'] += 1
    
    stats['total'] += 1
    progress['checked'].append(stop_id)
    
    # Progress report every 200
    if (idx + 1) % 200 == 0:
        elapsed = (datetime.now() - stats['start']).total_seconds()
        rate = (idx + 1 - stats['skipped']) / elapsed if elapsed > 0 else 0
        remaining = len(need_check) - idx - 1
        eta = remaining / rate if rate > 0 else 0
        pct = (idx + 1) / len(need_check) * 100
        print(f"  [{idx+1:5d}/{len(need_check)}] {pct:.1f}% | "
              f"SV: {stats['sv_ok']}✅ {stats['sv_no']}❌ {stats['errors']}err | "
              f"Skip: {stats['skipped']} | "
              f"Rate: {rate:.1f}/s | ETA: {eta/60:.0f}min")
        sys.stdout.flush()
        save_progress(progress)
        # Save GeoJSON checkpoint
        with open(os.path.join(BASE_DIR, 'stops.geojson'), 'w') as f:
            json.dump(gtfs, f, ensure_ascii=False)
    
    time.sleep(0.05)  # ~20 req/s

# Final save
save_progress(progress)
with open(os.path.join(BASE_DIR, 'stops.geojson'), 'w') as f:
    json.dump(gtfs, f, ensure_ascii=False)

# Summary
elapsed = (datetime.now() - stats['start']).total_seconds()
total_checked = stats['sv_ok'] + stats['sv_no']
print(f"\n{'='*60}")
print(f"=== RESUMEN METADATA CHECK ===")
print(f"Tiempo: {elapsed/60:.1f} min")
print(f"Procesadas: {stats['total']} (skipped: {stats['skipped']})")
print(f"Con Street View: {stats['sv_ok']} ({stats['sv_ok']/max(total_checked,1)*100:.1f}%)")
print(f"Sin Street View: {stats['sv_no']} ({stats['sv_no']/max(total_checked,1)*100:.1f}%)")
print(f"Errores: {stats['errors']}")
print(f"Coste: $0.00 (metadata es gratis)")