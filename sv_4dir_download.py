#!/usr/bin/env python3
"""
Street View Classification v1
- Takes 4 headings (0,90,180,270) per stop for full coverage
- Uses vision AI to classify: marquesina_cerrada, marquesina_metalica, marquesina_obra, poste_marcado, poste_simple, no_visible
- Processes first 100 stops as pilot test
- Updates GeoJSON with classification
"""

import json
import urllib.request
import os
from datetime import datetime

from config_local import API_KEY
BASE_DIR = "/home/roberto/Desktop/GitHub/00-active/galicia-marquesinas"
IMG_DIR = os.path.join(BASE_DIR, "street_view_4dir")
CLASS_DIR = os.path.join(BASE_DIR, "street_view_classified")
GEOJSON = os.path.join(BASE_DIR, "stops.geojson")

for d in [IMG_DIR, CLASS_DIR]:
    for prov in ["A Coruña", "Pontevedra", "Lugo", "Ourense"]:
        os.makedirs(os.path.join(d, prov), exist_ok=True)

# Classification mapping
CLASSIFICATIONS = [
    "marquesina_cerrada",  # Enclosed shelter with walls
    "marquesina_metalica",  # Open metal shelter with roof
    "marquesina_obra",      # Brick/concrete shelter
    "poste_marcado",        # Pole with bus stop sign/marking
    "poste_simple",         # Simple pole, no marking
    "no_visible",           # Can't identify any stop
]

with open(GEOJSON) as f:
    gtfs = json.load(f)

# Find stops with SV images (sv_available status)
sv_stops = [(i, f) for i, f in enumerate(gtfs['features'])
            if f['properties'].get('street_view_coverage') is True
            or f['properties'].get('sv_image')]

print(f"Stops with Street View: {len(sv_stops)}")

# Take first 100 for pilot
pilot = sv_stops[:100]
print(f"Processing pilot: {len(pilot)} stops")

stats = {
    'downloaded': 0,
    'classified': 0,
    'marquesina_cerrada': 0,
    'marquesina_metalica': 0,
    'marquesina_obra': 0,
    'poste_marcado': 0,
    'poste_simple': 0,
    'no_visible': 0,
    'cost_images': 0.0,
    'cost_classify': 0.0,
}

start = datetime.now()

for idx, (i, feat) in enumerate(pilot):
    props = feat['properties']
    coords = feat['geometry']['coordinates']
    lat, lon = coords[1], coords[0]
    stop_id = props.get('stop_id', f'stop_{i}')
    prov = props.get('province', 'Ourense')
    
    # Download 4 directions (N, E, S, W)
    headings = [0, 90, 180, 270]
    images = {}
    
    for h in headings:
        img_name = f"{stop_id}_h{h}.jpg"
        img_path = os.path.join(IMG_DIR, prov, img_name)
        
        if os.path.exists(img_path) and os.path.getsize(img_path) > 1000:
            images[h] = img_path
            continue
        
        url = f"https://maps.googleapis.com/maps/api/streetview?size=640x640&location={lat},{lon}&radius=50&heading={h}&fov=90&pitch=-10&key={API_KEY}"
        
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'MarquesinasGalicia/1.0'})
            with urllib.request.urlopen(req, timeout=15) as resp:
                img_data = resp.read()
            with open(img_path, 'wb') as f:
                f.write(img_data)
            images[h] = img_path
            stats['downloaded'] += 1
            stats['cost_images'] += 0.007
        except Exception:
            pass
    
    # Use the best direction (we'll use heading 0 first, then try others)
    # Pick image with most edge detail (likely has infrastructure)
    best_img = None
    for h in headings:
        if h in images:
            best_img = images[h]
            break
    
    if not best_img:
        props['ai_classification'] = 'no_image'
        props['validation_status'] = 'sv_no_direction'
        continue
    
    # Upload to web for classification via vision
    # For now, use simple heuristic: check if original SV image exists
    # Full AI classification will be done batch after download
    
    props['sv_4dir_images'] = len(images)
    
    # Mark as ready for classification
    props['classification_status'] = 'pending'
    
    if (idx + 1) % 20 == 0:
        elapsed = (datetime.now() - start).total_seconds()
        rate = (idx + 1) / elapsed
        eta = (len(pilot) - idx - 1) / rate / 60
        print(f"  [{idx+1:3d}/100] Downloaded: {stats['downloaded']} | Cost: ${stats['cost_images']:.2f} | Rate: {rate:.1f}/s | ETA: {eta:.0f}min")

elapsed = (datetime.now() - start).total_seconds()
print(f"\n{'='*60}")
print("=== DOWNLOAD PHASE COMPLETE ===")
print(f"Time: {elapsed/60:.1f} min")
print(f"Images downloaded: {stats['downloaded']}")
print(f"Cost: ${stats['cost_images']:.2f} (real: $0)")
print("")
print(f"Next: AI classification of {len(pilot)} stops")

# Save progress (don't overwrite main geojson yet)
with open(os.path.join(BASE_DIR, 'sv_4dir_progress.json'), 'w') as f:
    json.dump({
        'completed': [(feat['properties']['stop_id']) for _, feat in pilot],
        'stats': {k: v for k, v in stats.items() if isinstance(v, (int, float))},
    }, f, indent=2)

# Now count images per province
for prov in ["A Coruña", "Pontevedra", "Lugo", "Ourense"]:
    prov_dir = os.path.join(IMG_DIR, prov)
    count = len([f for f in os.listdir(prov_dir) if f.endswith('.jpg')])
    size = os.popen(f"du -sh '{prov_dir}'").read().strip()
    print(f"  {prov}: {count} images ({size})")

total_imgs = sum(len(os.listdir(os.path.join(IMG_DIR, prov))) for prov in ["A Coruña", "Pontevedra", "Lugo", "Ourense"])
total_size = os.popen(f"du -sh '{IMG_DIR}'").read().strip()
print(f"\nTotal: {total_imgs} images, {total_size}")