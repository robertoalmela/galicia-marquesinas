#!/usr/bin/env python3
"""
Classification Pipeline v1
- Downloads 4 headings per stop (0,90,180,270)
- Uses gemma4:31b via Ollama to classify each image
- Picks best classification across 4 headings
- Updates GeoJSON with ai_classification
- Handles 5000 stops (pilot: first 100)

Cost: $0 images (free credit) + $0 AI (local Ollama)
"""

import json
import urllib.request
import os
from datetime import datetime

from config_local import API_KEY
BASE_DIR = "/home/roberto/Desktop/GitHub/00-active/galicia-marquesinas"
IMG_DIR = os.path.join(BASE_DIR, "sv_4dir")
GEOJSON = os.path.join(BASE_DIR, "stops.geojson")
CLASS_LOG = os.path.join(BASE_DIR, "classification_log.json")

for prov in ["A Coruña", "Pontevedra", "Lugo", "Ourense"]:
    os.makedirs(os.path.join(IMG_DIR, prov), exist_ok=True)

with open(GEOJSON) as f:
    gtfs = json.load(f)

# OLLAMA classify function
OLLAMA_MODEL = "gemma3:12b"  # Good vision, fits in VRAM

CLASSIFICATIONS = ["marquesina_cerrada", "marquesina_metalica", "marquesina_obra", 
                   "poste_marcado", "poste_simple", "no_visible"]

# Priority: marquesina > poste > no_visible (pick best classification from 4 dirs)
PRIORITY = {c: i for i, c in enumerate(CLASSIFICATIONS)}

def ollama_classify(image_path):
    """Classify image using local Ollama with gemma3 vision model"""
    import base64
    with open(image_path, 'rb') as f:
        img_b64 = base64.b64encode(f.read()).decode()
    
    prompt = """You are a bus stop classifier. Look at this Google Street View image.
Classify the bus stop infrastructure as EXACTLY ONE of:
- marquesina_cerrada: enclosed shelter with walls/panels
- marquesina_metalica: open metal frame shelter with roof only
- marquesina_obra: brick/concrete/stone shelter
- poste_marcado: pole with bus stop sign or marking
- poste_simple: simple pole, no shelter or sign
- no_visible: no bus stop infrastructure visible

Reply with ONLY the classification word, nothing else."""

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "images": [img_b64],
        "stream": False,
        "options": {"temperature": 0.1, "num_predict": 20}
    }
    
    try:
        data = json.dumps(payload).encode()
        req = urllib.request.Request(
            "http://localhost:11434/api/generate",
            data=data,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read())
        
        response = result.get("response", "").strip().lower()
        # Extract classification
        for c in CLASSIFICATIONS:
            if c in response:
                return c
        return "no_visible"
    except Exception as e:
        return f"error: {e}"

def download_sv(lat, lon, heading, out_path):
    """Download Street View image"""
    url = f"https://maps.googleapis.com/maps/api/streetview?size=640x640&location={lat},{lon}&radius=50&heading={heading}&fov=90&pitch=-10&key={API_KEY}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "MarquesinasGalicia/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read()
    except Exception:
        return None

# Process first 100 stops as pilot
TOTAL = 100

# Find stops with SV coverage
sv_stops = [(i, f) for i, f in enumerate(gtfs['features']) 
            if f['properties'].get('street_view_coverage') is True
            or f['properties'].get('sv_image')]

# Filter: only stops that already have single-heading image but no 4dir
need_4dir = []
for i, feat in sv_stops[:5000]:  # from the 5000 we already processed
    if 'ai_classification' not in feat['properties']:
        need_4dir.append((i, feat))

pilot = need_4dir[:TOTAL]
print(f"Stops needing classification: {len(need_4dir)}")
print(f"Processing pilot: {len(pilot)} stops")
print(f"Model: {OLLAMA_MODEL}")
print()

stats = {'downloaded': 0, 'classified': 0, 'cost_imgs': 0.0}
class_counts = {c: 0 for c in CLASSIFICATIONS}
class_counts['error'] = 0
start = datetime.now()
log = []

for idx, (i, feat) in enumerate(pilot):
    props = feat['properties']
    coords = feat['geometry']['coordinates']
    lat, lon = coords[1], coords[0]
    prov = props.get('province', 'Ourense')
    stop_idx = i
    
    # Download 4 directions
    headings = [0, 90, 180, 270]
    images = {}
    
    for h in headings:
        fname = f"stop_{stop_idx}_h{h}.jpg"
        fpath = os.path.join(IMG_DIR, prov, fname)
        
        if os.path.exists(fpath) and os.path.getsize(fpath) > 1000:
            images[h] = fpath
            continue
        
        img_data = download_sv(lat, lon, h, fpath)
        if img_data:
            with open(fpath, 'wb') as f:
                f.write(img_data)
            images[h] = fpath
            stats['downloaded'] += 1
            stats['cost_imgs'] += 0.007
    
    # Classify each direction
    best_class = "no_visible"
    best_priority = 999
    dir_results = {}
    
    for h in headings:
        if h not in images:
            dir_results[h] = "no_image"
            continue
        
        cls = ollama_classify(images[h])
        dir_results[h] = cls
        
        # Pick best: marquesina > poste > no_visible
        if cls in PRIORITY and PRIORITY[cls] < best_priority:
            best_priority = PRIORITY[cls]
            best_class = cls
    
    # Update GeoJSON
    props['ai_classification'] = best_class
    props['classification_dir_results'] = dir_results
    props['classification_date'] = datetime.now().isoformat()[:10]
    props['validation_status'] = 'ai_classified'
    
    class_counts[best_class] = class_counts.get(best_class, 0) + 1
    stats['classified'] += 1
    
    log.append({
        'stop_idx': stop_idx,
        'name': props['name'],
        'province': prov,
        'classification': best_class,
        'directions': dir_results,
    })
    
    icon = '🏠' if 'marquesina' in best_class else '🪧' if 'poste' in best_class else '❓'
    if (idx + 1) % 10 == 0:
        elapsed = (datetime.now() - start).total_seconds()
        rate = (idx + 1) / elapsed
        eta = (len(pilot) - idx - 1) / rate / 60
        print(f"  [{idx+1:3d}/{TOTAL}] {icon} {props['name'][:30]:30s} → {best_class:20s} | dirs={dir_results} | Rate: {rate:.1f}/s | ETA: {eta:.0f}min")

# Save
elapsed = (datetime.now() - start).total_seconds()
with open(GEOJSON, 'w') as f:
    json.dump(gtfs, f, ensure_ascii=False)
with open(CLASS_LOG, 'w') as f:
    json.dump(log, f, ensure_ascii=False, indent=2)

print(f"\n{'='*60}")
print(f"=== CLASSIFICATION RESULTS ({TOTAL} stops) ===")
print(f"Time: {elapsed/60:.1f} min")
print(f"Classified: {stats['classified']}")
print(f"Images downloaded: {stats['downloaded']}")
print("")
print("Classification breakdown:")
for c in CLASSIFICATIONS:
    n = class_counts.get(c, 0)
    pct = n / TOTAL * 100 if TOTAL else 0
    bar = '█' * int(pct / 2)
    print(f"  {c:20s}: {n:3d} ({pct:5.1f}%) {bar}")
print("")
print(f"Cost images: ${stats['cost_imgs']:.2f} (real: $0)")
print("Cost AI: $0 (local Ollama)")
print("Total cost: $0.00")