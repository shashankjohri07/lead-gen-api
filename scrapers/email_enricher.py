"""
Email lookup using Hunter.io (free tier: 25 searches/month, paid: 500+).
Docs: https://hunter.io/api-documentation
"""
import requests
from app.config import settings


def lookup_email(name: str, company: str = None) -> str | None:
    if not settings.HUNTER_API_KEY or not company:
        return None

    # Step 1: find domain from company name
    domain = _find_domain(company)
    if not domain:
        return None

    # Step 2: find email for person at that domain
    return _find_email(name, domain)


def _find_domain(company: str) -> str | None:
    try:
        resp = requests.get(
            "https://api.hunter.io/v2/domain-search",
            params={
                "company": company,
                "api_key": settings.HUNTER_API_KEY,
                "limit": 1,
            },
            timeout=10,
        )
        return resp.json().get("data", {}).get("domain")
    except Exception:
        return None


def _find_email(full_name: str, domain: str) -> str | None:
    parts = full_name.strip().split()
    if len(parts) < 2:
        return None
    first, last = parts[0], parts[-1]
    try:
        resp = requests.get(
            "https://api.hunter.io/v2/email-finder",
            params={
                "domain": domain,
                "first_name": first,
                "last_name": last,
                "api_key": settings.HUNTER_API_KEY,
            },
            timeout=10,
        )
        data = resp.json().get("data", {})
        if data.get("score", 0) >= 50:
            return data.get("email")
    except Exception:
        pass
    return None
