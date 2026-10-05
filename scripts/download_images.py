import pandas as pd
import requests
import os
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm

# ============ CONFIG ============
INPUT_CSV = "data/processed/cars_sample_80k.csv"
OUTPUT_CSV = "data/processed/cars_with_local_images.csv"
IMAGE_FOLDER = "assets/car_images"
TOP_N = 500  # Kitni cars ki images download karni hain
TIMEOUT = 5  # seconds
MAX_WORKERS = 20  # Parallel downloads
# ================================

os.makedirs(IMAGE_FOLDER, exist_ok=True)

# CSV load karein
df = pd.read_csv(INPUT_CSV)

# Sirf top N cars lein (price ke hisaab se sort kar ke, ya random)
df = df.dropna(subset=['image_url'])
df = df[df['image_url'].str.startswith('http')]
df = df.head(TOP_N).copy()  # Ya aap filter laga sakte hain

print(f"Total cars to process: {len(df)}")

def check_and_download(row):
    url = row['image_url']
    idx = row.name
    manufacturer = str(row['manufacturer']).replace(' ', '_')
    year = str(row['year']).replace('.0', '')
    filename = f"{idx}_{manufacturer}_{year}.jpg"
    filepath = os.path.join(IMAGE_FOLDER, filename)
    
    try:
        r = requests.get(url, timeout=TIMEOUT, stream=True)
        if r.status_code == 200:
            with open(filepath, 'wb') as f:
                for chunk in r.iter_content(1024):
                    f.write(chunk)
            return filepath
    except Exception:
        pass
    return None

# Parallel download
with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
    results = list(tqdm(executor.map(check_and_download, [row for _, row in df.iterrows()]), total=len(df)))

df['local_image_path'] = results

# Jo download nahi hui, unke liye placeholder
df['local_image_path'] = df['local_image_path'].fillna('assets/placeholder.png')

# Save
df.to_csv(OUTPUT_CSV, index=False)
print(f"\nDone! Saved to {OUTPUT_CSV}")
print(f"Downloaded: {df['local_image_path'].notna().sum()} images")