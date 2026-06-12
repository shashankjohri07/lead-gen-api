"""
Scrapes business contacts from Google Maps Places API.
Useful for: clinics, hospitals, insurance offices, HR contacts.

Google Maps API free tier: $200 credit/month ≈ 40,000 Place Details calls.

Run:
  python -m scrapers.gmaps_scraper --query "health insurance office" --state Maharashtra --district Pune
"""
import argparse
import os
import sys
import time
import requests
from tqdm import tqdm

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.database import SessionLocal
from app.models import Lead, SourceType
from app.config import settings

BASE_URL = "https://maps.googleapis.com/maps/api/place"


def _text_search(query: str, location_bias: str, api_key: str) -> list[dict]:
    """Returns list of place results."""
    places = []
    url = f"{BASE_URL}/textsearch/json"
    params = {"query": query, "key": api_key}
    if location_bias:
        params["query"] = f"{query} {location_bias}"

    while True:
        resp = requests.get(url, params=params, timeout=15)
        data = resp.json()
        places.extend(data.get("results", []))

        next_token = data.get("next_page_token")
        if not next_token:
            break
        time.sleep(2)  # Google requires 2s delay before next_page_token is valid
        params = {"pagetoken": next_token, "key": api_key}

    return places


def _place_details(place_id: str, api_key: str) -> dict:
    resp = requests.get(
        f"{BASE_URL}/details/json",
        params={
            "place_id": place_id,
            "fields": "name,formatted_phone_number,international_phone_number,"
                      "formatted_address,address_components,website,rating",
            "key": api_key,
        },
        timeout=15,
    )
    return resp.json().get("result", {})


def _parse_address_components(components: list) -> dict:
    out = {"area": "", "city": "", "district": "", "state": "", "pincode": ""}
    for c in components:
        types = c.get("types", [])
        name = c.get("long_name", "")
        if "sublocality" in types or "neighborhood" in types:
            out["area"] = name
        elif "locality" in types:
            out["city"] = name
        elif "administrative_area_level_2" in types:
            out["district"] = name
        elif "administrative_area_level_1" in types:
            out["state"] = name
        elif "postal_code" in types:
            out["pincode"] = name
    return out


def scrape_and_load(
    query: str,
    state: str = "",
    district: str = "",
    api_key: str = None,
) -> int:
    api_key = api_key or settings.GOOGLE_MAPS_API_KEY
    if not api_key:
        print("ERROR: Set GOOGLE_MAPS_API_KEY in .env")
        return 0

    location_bias = f"{district} {state}".strip()
    print(f"Searching Google Maps: '{query}' in '{location_bias}'")
    places = _text_search(query, location_bias, api_key)
    print(f"Found {len(places)} places. Fetching details...")

    db = SessionLocal()
    loaded = 0

    for place in tqdm(places, desc="Enriching with details"):
        place_id = place.get("place_id")
        if not place_id:
            continue

        try:
            details = _place_details(place_id, api_key)
        except Exception as e:
            print(f"  Error for {place_id}: {e}")
            continue

        addr = _parse_address_components(details.get("address_components", []))
        phone = details.get("formatted_phone_number") or details.get("international_phone_number")
        name = details.get("name", "")

        if not name:
            continue

        lead = Lead(
            full_name=name,
            phone_primary=phone,
            address_line=details.get("formatted_address"),
            area=addr["area"] or None,
            city=addr["city"] or state or None,
            district=addr["district"] or district or None,
            state=addr["state"] or state or None,
            pincode=addr["pincode"] or None,
            source=SourceType.GOOGLE_MAPS,
            source_id=place_id,
            phone_verified=bool(phone),
        )
        db.add(lead)
        loaded += 1
        time.sleep(0.05)  # gentle rate limiting

    db.commit()
    db.close()
    print(f"Loaded {loaded} places from Google Maps.")
    return loaded


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--query", default="health insurance office")
    parser.add_argument("--state", default="")
    parser.add_argument("--district", default="")
    args = parser.parse_args()
    scrape_and_load(args.query, args.state, args.district)
