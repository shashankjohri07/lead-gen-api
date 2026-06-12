"""
Phone number lookup for enriching leads.

Priority:
1. If lead has company_name → try Google Maps business search
2. Truecaller Business API (if key configured)
3. Returns None if not found
"""
import requests
from app.config import settings


def lookup_phone(name: str, address: str = None, company: str = None) -> str | None:
    # Strategy 1: Google Maps (good for business/company leads)
    if company and settings.GOOGLE_MAPS_API_KEY:
        phone = _gmaps_phone(company, address)
        if phone:
            return phone

    # Strategy 2: Truecaller Business API
    if settings.TRUECALLER_API_KEY:
        phone = _truecaller_lookup(name)
        if phone:
            return phone

    return None


def _gmaps_phone(company: str, address: str = None) -> str | None:
    query = company
    if address:
        query = f"{company} {address}"
    try:
        resp = requests.get(
            "https://maps.googleapis.com/maps/api/place/findplacefromtext/json",
            params={
                "input": query,
                "inputtype": "textquery",
                "fields": "formatted_phone_number,name",
                "key": settings.GOOGLE_MAPS_API_KEY,
            },
            timeout=10,
        )
        candidates = resp.json().get("candidates", [])
        if candidates:
            return candidates[0].get("formatted_phone_number")
    except Exception:
        pass
    return None


def _truecaller_lookup(name: str) -> str | None:
    """
    Truecaller Business Search API.
    Docs: https://business.truecaller.com/documentation
    """
    try:
        resp = requests.get(
            "https://api4.truecaller.com/v1/default/search",
            params={"q": name, "countryCode": "IN", "type": 4},
            headers={
                "Authorization": f"Bearer {settings.TRUECALLER_API_KEY}",
            },
            timeout=10,
        )
        data = resp.json()
        # Truecaller returns phone in data.data[0].phones[0].e164Format
        phones = (
            data.get("data", [{}])[0].get("phones", [{}])[0].get("e164Format")
            if data.get("data")
            else None
        )
        return phones
    except Exception:
        pass
    return None
