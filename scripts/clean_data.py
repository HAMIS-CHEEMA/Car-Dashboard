import pandas as pd
import os

# ============================
# PATHS
# ============================
raw_path = r"data\raw\vehicles.csv"
output_path = r"data\processed\cars_sample_80k.csv"

print("File exists:", os.path.exists(raw_path))
print("Loading...")

# ============================
# COLUMNS (image_url INCLUDE)
# ============================
cols = ['price', 'year', 'manufacturer', 'model', 'condition',
        'cylinders', 'fuel', 'odometer', 'title_status',
        'transmission', 'drive', 'type', 'paint_color', 'state',
        'image_url']   # <-- yeh add hui

# ============================
# LOAD IN CHUNKS
# ============================
chunks = pd.read_csv(raw_path, usecols=cols, chunksize=100000)

df_list = []
for i, chunk in enumerate(chunks):
    df_list.append(chunk)
    print(f"Chunk {i+1} loaded: {chunk.shape}")

df = pd.concat(df_list, ignore_index=True)
print("Total loaded:", df.shape)

# ============================
# CLEANING
# ============================
print("\n--- Cleaning Start ---")

df = df[(df['price'] >= 500) & (df['price'] <= 100000)]
print("After price filter:", df.shape)

df = df[(df['year'] >= 1990) & (df['year'] <= 2024)]
print("After year filter:", df.shape)

df = df[(df['odometer'] >= 0) & (df['odometer'] <= 300000)]
print("After odometer filter:", df.shape)

df = df.dropna(subset=['price', 'year', 'manufacturer', 'model', 'odometer'])
print("After dropna:", df.shape)

df = df.drop_duplicates()
print("After dedup:", df.shape)

# ============================
# IMAGE COLUMN HANDLING
# ============================
print("\n--- Image Column Handling ---")

# Placeholder image (jo har car ke liye fallback banega)
placeholder = "https://placehold.co/600x400/1A2E44/FFFFFF/png?text=No+Image"

# image_url khaali ya invalid ho to placeholder lagao
df['image_url'] = df['image_url'].fillna(placeholder)
df['image_url'] = df['image_url'].replace('', placeholder)
df['image_url'] = df['image_url'].apply(
    lambda x: x if isinstance(x, str) and x.startswith('http') else placeholder
)

print("Image URL column ready.")

# ============================
# OPTIONAL: BRAND LOGO COLUMN
# ============================
brand_domains = {
    'toyota': 'toyota.com',
    'honda': 'honda.com',
    'ford': 'ford.com',
    'chevrolet': 'chevrolet.com',
    'nissan': 'nissanusa.com',
    'bmw': 'bmw.com',
    'mercedes-benz': 'mercedes-benz.com',
    'audi': 'audi.com',
    'hyundai': 'hyundai.com',
    'kia': 'kia.com',
    'mazda': 'mazda.com',
    'subaru': 'subaru.com',
    'volkswagen': 'vw.com',
    'jeep': 'jeep.com',
    'ram': 'ramtrucks.com',
    'gmc': 'gmc.com',
    'lexus': 'lexus.com',
    'infiniti': 'infiniti.com',
    'acura': 'acura.com',
    'cadillac': 'cadillac.com',
    'chrysler': 'chrysler.com',
    'dodge': 'dodge.com',
    'buick': 'buick.com',
    'lincoln': 'lincoln.com',
    'volvo': 'volvocars.com',
    'mitsubishi': 'mitsubishicars.com',
    'porsche': 'porsche.com',
    'jaguar': 'jaguar.com',
    'land rover': 'landrover.com',
    'rover': 'landrover.com',
    'mini': 'miniusa.com',
    'tesla': 'tesla.com',
    'fiat': 'fiat.com',
    'alfa-romeo': 'alfaromeousa.com',
    'scion': 'scion.com',
    'saturn': 'saturn.com',
    'pontiac': 'pontiac.com',
    'mercury': 'mercuryvehicles.com',
    'hummer': 'hummer.com',
    'isuzu': 'isuzu.com',
    'suzuki': 'suzukiauto.com',
    'smart': 'smartusa.com',
    'ferrari': 'ferrari.com',
    'maserati': 'maserati.com',
    'bentley': 'bentleymotors.com',
    'rolls-royce': 'rolls-roycemotorcars.com',
    'aston martin': 'astonmartin.com',
    'lotus': 'lotuscars.com',
    'mclaren': 'mclaren.com',
    'bugatti': 'bugatti.com',
    'lamborghini': 'lamborghini.com',
}

df['brand_logo'] = df['manufacturer'].str.lower().map(
    lambda x: f"https://logo.clearbit.com/{brand_domains.get(x, '')}"
)

# Agar brand domain na mile to generic placeholder
df['brand_logo'] = df['brand_logo'].apply(
    lambda x: x if x != "https://logo.clearbit.com/" else placeholder
)

print("Brand logo column ready.")

# ============================
# SAMPLE
# ============================
df_sample = df.sample(n=80000, random_state=42)
print("\nFinal sample:", df_sample.shape)

# ============================
# SAVE
# ============================
df_sample.to_csv(output_path, index=False)
print(f"Saved to: {output_path}")