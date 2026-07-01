#!/usr/bin/env python3
"""
Street View Download - 5000 stops, 4 directions
Coste: $0 (crédito gratuito Google $200/mes)
"""

import json
import urllib.request
import time
import os
import sys
from datetime import datetime

BASE_DIR = "/home/roberto/Desktop/GitHub/00-active/galicia-marquesinas"
IMG_DIR = os.path.join(BASE_DIR, "sv_4dir")
os.makedirs(IMG_DIR, exist_ok=True)

for prov in ["A Coruña", "Pontevedra", "Lugo", "Ourense"]:
    os.makedirs(os.path.join(IMG_DIR, prov), exist_ok=True)

with open(os.path.join(BASE_DIR, 'stops.geojson')) as f:
    gtfs = json.load(f)

unverified = []
for i, feat in enumerate(gtfs['features']):
    vs = feat['properties'].get('validation_status', 'unverified')
    if vs not in ('validated', 'no_shelter'):
        unverified.append((i, feat))

print(f"Paradas sin validar OSM: {len(unverified)}")
print(f"Procesando: primeras 5.000 (4 direcciones)")

batch = unverified[:5000]

HEADINGS = [0, 90, 180, 270]
HEADING_NAMES = {0: 'h0', 90: 'h90', 180: 'h180', 270: 'h270'}

stats = {
    'total': 0, 'sv_ok': 0, 'sv_no': 0,
    'downloaded': 0, 'download_fail': 0, 'errors': 0,
    'cost_meta': 0.0, 'cost_img': 0.0,
    'start': datetime.now(), 'skipped': 0,
}

PROGRESS_FILE = os.path.join(BASE_DIR, 'sv_progress_4dir.json')

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

for idx, (i, feat) in enumerate(batch):
    props = feat['properties']
    coords = feat['geometry']['coordinates']
    lat, lon = coords[1], coords[0]
    stop_id = props.get('stop_id', f'stop_{i}')
    prov = props.get('province', 'Ourense')

    if stop_id in completed_set:
        stats['skipped'] += 1
        continue

    # Metadata check - pass key as arg to avoid writing it in file
    api_key = os.environ.get('GMAPS_KEY', '')
    meta_url = f"https://maps.googleapis.com/maps/api/streetview/metadata?location={lat},{lon}&radius=50&key={api_key}"

    try:
        req = urllib.request.Request(meta_url, headers={'User-Agent': 'MarquesinasGalicia/1.0'})
        with urllib.request.urlopen(req, timeout=10) as resp:
            meta = json.loads(resp.read())

        stats['cost_meta'] += 0.005

        if meta.get('status') != 'OK':
            stats['sv_no'] += 1
            feat['properties']['street_view_coverage'] = False
            feat['properties']['validation_status'] = 'no_sv'
            stats['total'] += 1
            progress['completed'].append(stop_id)
            continue

        stats['sv_ok'] += 1
        feat['properties']['street_view_coverage'] = True
        feat['properties']['sv_date'] = meta.get('date', '')

    except Exception as e:
        stats['errors'] += 1
        stats['total'] += 1
        continue

    # Download 4 directions
    all_ok = True
    for heading in HEADINGS:
        img_filename = f"{stop_id}_{HEADING_NAMES[heading]}.jpg"
        img_path = os.path.join(IMG_DIR, prov, img_filename)

        if os.path.exists(img_path) and os.path.getsize(img_path) > 5000:
            continue

        img_url = (
            f"https://maps.googleapis.com/maps/api/streetview?"
            f"size=640x640&location={lat},{lon}&radius=50"
            f"&heading={heading}&fov=90&pitch=0&key={api_key}"
        )

        try:
            req = urllib.request.Request(img_url, headers={'User-Agent': 'MarquesinasGalicia/1.0'})
            with urllib.request.urlopen(req, timeout=15) as resp:
                img_data = resp.read()
            with open(img_path, 'wb') as f:
                f.write(img_data)
            stats['downloaded'] += 1
            stats['cost_img'] += 0.007
        except Exception as e:
            stats['download_fail'] += 1
            all_ok = False

    if all_ok:
        feat['properties']['validation_status'] = 'sv_available'
        progress['completed'].append(stop_id)
    else:
        progress['failed'].append(stop_id)

    stats['total'] += 1

    if (idx + 1) % 50 == 0:
        elapsed = (datetime.now() - stats['start']).total_seconds()
        rate = (idx + 1 - stats['skipped']) / elapsed if elapsed > 0 else 0
        remaining = len(batch) - idx - 1
        eta = remaining / rate if rate > 0 else 0
        total_cost = stats['cost_meta'] + stats['cost_img']
        print(f"  [{idx+1:5d}/5000] SV: {stats['sv_ok']}OK {stats['sv_no']}NO | "
              f"Img: {stats['downloaded']}dn {stats['download_fail']}fail | "
              f"Skip: {stats['skipped']} | ${total_cost:.2f} | "
              f"ETA: {eta/60:.0f}min")
        sys.stdout.flush()
        save_progress(progress)

    time.sleep(0.15)

save_progress(progress)

with open(os.path.join(BASE_DIR, 'stops.geojson'), 'w') as f:
    json.dump(gtfs, f, ensure_ascii=False)

elapsed = (datetime.now() - stats['start']).total_seconds()
total_cost = stats['cost_meta'] + stats['cost_img']
du = os.popen(f"du -sh {IMG_DIR}").read().strip()

print(f"\n{'='*60}")
print(f"=== RESUMEN FINAL ===")
print(f"Tiempo: {elapsed/60:.1f} min")
print(f"Procesadas: {stats['total']} (skipped: {stats['skipped']})")
print(f"Con SV: {stats['sv_ok']} | Sin SV: {stats['sv_no']}")
print(f"Imagenes: {stats['downloaded']} ok, {stats['download_fail']} fail")
print(f"Coste: ${total_cost:.2f} (credito restante: ${200-total_cost:.2f})")
print(f"Disco: {du}")
for prov in ["A Coruña", "Pontevedra", "Lugo", "Ourense"]:
    prov_dir = os.path.join(IMG_DIR, prov)
    count = len([f for f in os.listdir(prov_dir) if f.endswith('.jpg')]) if os.path.exists(prov_dir) else 0
    print(f"  {prov}: {count} imagenes")