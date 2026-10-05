"""
Fetch one representative image per car model from Wikidata / Wikimedia Commons
and save the results to a CSV: name, wikidata_id, image_url, status

v2: handles 429 (Too Many Requests) with automatic retry + backoff, and
resumes from an existing car_images.csv so you don't redo cars that already
succeeded.

Usage:
    pip install requests
    python fetch_car_images.py

Output:
    car_images.csv
"""

import csv
import os
import time
import requests

CAR_NAMES = [
    "Toyota Camry", "Toyota Corolla", "Honda Accord", "Honda Civic",
    "Nissan Altima", "Hyundai Elantra", "Hyundai Sonata", "Kia K5",
    "Mazda6", "Volkswagen Jetta", "Volkswagen Passat", "BMW 3 Series",
    "BMW 5 Series", "Mercedes-Benz C-Class", "Mercedes-Benz E-Class",
    "Audi A4", "Audi A6", "Subaru Legacy",

    "Toyota RAV4", "Toyota Highlander", "Honda CR-V", "Honda Pilot",
    "Ford Explorer", "Ford Escape", "Chevrolet Equinox", "Chevrolet Tahoe",
    "Jeep Grand Cherokee", "Jeep Wrangler", "Hyundai Tucson",
    "Hyundai Santa Fe", "Kia Sportage", "Kia Sorento", "Nissan Rogue",
    "Mazda CX-5", "Subaru Outback", "Subaru Forester", "BMW X3", "BMW X5",
    "Audi Q5", "Volvo XC60",

    "Volkswagen Golf", "Honda Fit", "Ford Fiesta", "Mini Cooper",
    "Toyota Yaris", "Hyundai i20", "Kia Rio", "Fiat 500", "Suzuki Swift",
    "Chevrolet Spark",

    "Ford F-150", "Chevrolet Silverado", "Ram 1500", "Toyota Tacoma",
    "Toyota Tundra", "GMC Sierra", "Nissan Titan", "Honda Ridgeline",

    "Tesla Model 3", "Tesla Model S", "Tesla Model Y", "Tesla Model X",
    "Chevrolet Bolt", "Nissan Leaf", "Hyundai Ioniq 5", "Kia EV6",
    "Ford Mustang Mach-E", "Volkswagen ID.4", "BMW i4", "Audi e-tron",

    "Ford Mustang", "Chevrolet Camaro", "Chevrolet Corvette",
    "Porsche 911", "Porsche Cayenne", "Mercedes-Benz S-Class",
    "Lexus RX", "Lexus ES", "Jaguar F-Pace", "Land Rover Range Rover",
]

WD_SEARCH_URL = "https://www.wikidata.org/w/api.php"
WD_ENTITY_URL = "https://www.wikidata.org/wiki/Special:EntityData/{qid}.json"
COMMONS_FILEPATH = "https://commons.wikimedia.org/wiki/Special:FilePath/{filename}"
OUTPUT_CSV = "car_images.csv"

HEADERS = {
    "User-Agent": "CarDashboardImageFetcher/1.0 (personal project; contact: none)"
}

# Base delay between requests. Wikidata's public API rate-limits fairly
# aggressively if you go faster than this.
BASE_DELAY = 1.5
MAX_RETRIES = 5


def request_with_retry(url, params=None):
    """GET with retry+backoff on 429 (Too Many Requests) and 5xx errors."""
    delay = BASE_DELAY
    for attempt in range(1, MAX_RETRIES + 1):
        r = requests.get(url, params=params, headers=HEADERS, timeout=15)
        if r.status_code == 429:
            retry_after = r.headers.get("Retry-After")
            wait = float(retry_after) if retry_after else delay
            print(f"  (rate-limited, waiting {wait:.1f}s, attempt {attempt}/{MAX_RETRIES})")
            time.sleep(wait)
            delay *= 2
            continue
        if r.status_code >= 500:
            print(f"  (server error {r.status_code}, waiting {delay:.1f}s, attempt {attempt}/{MAX_RETRIES})")
            time.sleep(delay)
            delay *= 2
            continue
        r.raise_for_status()
        return r
    raise requests.RequestException(f"Failed after {MAX_RETRIES} retries: {url}")


def search_wikidata_id(name):
    params = {
        "action": "wbsearchentities",
        "search": name,
        "language": "en",
        "format": "json",
        "type": "item",
        "limit": 1,
    }
    r = request_with_retry(WD_SEARCH_URL, params=params)
    data = r.json()
    results = data.get("search", [])
    if not results:
        return None
    return results[0]["id"]


def get_image_filename(qid):
    r = request_with_retry(WD_ENTITY_URL.format(qid=qid))
    data = r.json()
    entity = data["entities"][qid]
    claims = entity.get("claims", {})
    p18 = claims.get("P18")
    if not p18:
        return None
    return p18[0]["mainsnak"]["datavalue"]["value"]


def build_commons_url(filename):
    filename_url = filename.replace(" ", "_")
    return COMMONS_FILEPATH.format(filename=requests.utils.quote(filename_url))


def load_existing_results():
    """Resume support: load any rows already fetched successfully."""
    if not os.path.exists(OUTPUT_CSV):
        return {}
    existing = {}
    with open(OUTPUT_CSV, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            existing[row["name"]] = row
    return existing


def main():
    existing = load_existing_results()
    results = dict(existing)  # start with what we already have

    todo = [name for name in CAR_NAMES if existing.get(name, {}).get("status") != "ok"]
    print(f"{len(existing)} rows already in {OUTPUT_CSV}, {len(todo)} left to fetch.\n")

    for i, name in enumerate(todo, 1):
        print(f"[{i}/{len(todo)}] {name} ...", end=" ")
        try:
            qid = search_wikidata_id(name)
            if not qid:
                print("no Wikidata match")
                results[name] = {"name": name, "wikidata_id": "", "image_url": "", "status": "not_found"}
                time.sleep(BASE_DELAY)
                continue

            filename = get_image_filename(qid)
            if not filename:
                print(f"found {qid}, but no image")
                results[name] = {"name": name, "wikidata_id": qid, "image_url": "", "status": "no_image"}
                time.sleep(BASE_DELAY)
                continue

            image_url = build_commons_url(filename)
            print(f"OK -> {qid}")
            results[name] = {"name": name, "wikidata_id": qid, "image_url": image_url, "status": "ok"}

        except requests.RequestException as e:
            print(f"request error: {e}")
            results[name] = {"name": name, "wikidata_id": "", "image_url": "", "status": f"error: {e}"}

        # save progress after every car, so a crash never loses work
        with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["name", "wikidata_id", "image_url", "status"])
            writer.writeheader()
            for n in CAR_NAMES:
                if n in results:
                    writer.writerow(results[n])

        time.sleep(BASE_DELAY)

    ok_count = sum(1 for n in CAR_NAMES if results.get(n, {}).get("status") == "ok")
    print(f"\nDone. {ok_count}/{len(CAR_NAMES)} cars have an image.")
    print(f"Saved to {OUTPUT_CSV}")


if __name__ == "__main__":
    main()