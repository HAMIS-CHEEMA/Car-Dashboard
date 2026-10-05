"""
Takes your cars_with_local_images.csv and:
  1. Drops the 'brand_logo' and 'local_image_path' columns
  2. Replaces the 'image_url' column with a matching GitHub raw URL,
     found by looking for one of your 80 known car keywords inside
     each row's manufacturer + model text.
  3. Rows with no match get an empty image_url (you can fill these
     manually, or they'll just show no picture in the dashboard).

Usage:
    pip install pandas
    python update_image_urls.py

Also adds a clean 'matched_car_name' column (e.g. "Toyota Camry") for
matched rows, left blank otherwise -- use THIS column for your slicer,
not the raw/messy 'model' column, so the dropdown only shows clean
80-car names instead of junk scraped text.

Expects, in the same folder:
    cars_sample_80k.csv          (your 80,000-row dataset)
    car_image_urls.csv           (the 80-car GitHub URL list)

Output:
    cars_sample_80k_updated.csv
"""

import pandas as pd
import re

INPUT_CARS_CSV = r"D:\DataScience\Month_3\Car-Dashboard\data\processed\cars_sample_80k_updated.csv"
GITHUB_URLS_CSV = r"D:\DataScience\Month_3\Car-Dashboard\data\processed\car_image_urls.csv"
OUTPUT_CSV = r"D:\DataScience\Month_3\Car-Dashboard\data\processed\cars_sample_80k_updated.csv"

COLUMNS_TO_DROP = ["brand_logo", "local_image_path"]


def word_set(text):
    """Split into whole lowercase word/number tokens (no substring matching).
    Hyphens and dots are stripped (not treated as separators) so 'F-150'
    and 'f150', or 'CR-V' and 'crv', normalize to the same token."""
    cleaned = str(text).lower().replace("-", "").replace(".", "")
    return set(re.findall(r"[a-z0-9]+", cleaned))


def main():
    cars_df = pd.read_csv(INPUT_CARS_CSV)
    urls_df = pd.read_csv(GITHUB_URLS_CSV)  # columns: name, brand, model, filename, image_url

    # Build lookup: (brand_token, set of model tokens, url, clean_name),
    # ordered so that entries with MORE model tokens (more specific) are
    # checked first.
    lookup = []
    for _, row in urls_df.iterrows():
        brand_token = str(row["brand"]).lower().strip()
        model_tokens = word_set(row["model"])
        lookup.append((brand_token, model_tokens, row["image_url"], row["name"]))
    lookup.sort(key=lambda x: -len(x[1]))  # most specific models first

    def find_match(manufacturer, model):
        manufacturer_norm = str(manufacturer).lower().strip()
        model_words = word_set(model)
        for brand_token, model_tokens, url, clean_name in lookup:
            if manufacturer_norm != brand_token:
                continue
            # every token of the known model must appear as a WHOLE WORD
            # in this row's model text (e.g. "3" must be its own word,
            # not just present inside some other number)
            if model_tokens and model_tokens.issubset(model_words):
                return url, clean_name
        return None, None

    # Drop columns that exist (ignore if already missing)
    existing_to_drop = [c for c in COLUMNS_TO_DROP if c in cars_df.columns]
    cars_df = cars_df.drop(columns=existing_to_drop)

    # Rebuild image_url
    manufacturer_col = "manufacturer" if "manufacturer" in cars_df.columns else cars_df.columns[2]
    model_col = "model" if "model" in cars_df.columns else cars_df.columns[3]

    matches = cars_df.apply(
        lambda r: find_match(r[manufacturer_col], r[model_col]), axis=1
    )
    cars_df["image_url"] = [m[0] for m in matches]
    cars_df["matched_car_name"] = [m[1] for m in matches]

    cars_df.to_csv(OUTPUT_CSV, index=False)

    matched = cars_df["image_url"].notna().sum()
    total = len(cars_df)
    print(f"Matched {matched}/{total} rows to a GitHub image URL.")
    print(f"Dropped columns: {existing_to_drop}")
    print(f"Saved to {OUTPUT_CSV}")


if __name__ == "__main__":
    main()