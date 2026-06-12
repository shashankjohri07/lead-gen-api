# Lead Gen API

Health insurance lead generation backend.
Filter leads by state, district, age, phone availability.

## Start karo (3 commands)

```bash
cd lead-gen-api
cp .env.example .env

# PostgreSQL + Redis start karo
docker-compose up -d db redis

# DB tables banao + 500 sample leads seed karo
source venv/bin/activate
python scripts/setup_db.py
python scripts/seed_sample.py

# API start karo
uvicorn app.main:app --reload
```

API ready: http://localhost:8000
Docs (Swagger): http://localhost:8000/docs

---

## Real Data Load karna

### 1. MCA Director Data (30 lakh+ directors, free)

1. Yahan jao: https://www.mca.gov.in/content/mca/global/en/data-and-reports/data-sets/company-master-data.html
2. "Director Master Data" ZIP download karo
3. Extract karo aur CSV upload karo:

```bash
python -m scrapers.mca_parser --file ./data/mca/director_master_data.csv
```

Ya API se upload karo:
```
POST /api/v1/ingest/mca
Body: form-data, key=file, value=director_master_data.csv
```

### 2. Voter Roll Data (age + address + district wise)

State CEO portals se PDF/CSV download karo:
- Maharashtra: https://ceomaharashtra.nic.in/
- Gujarat: https://ceo.gujarat.gov.in/
- Karnataka: https://ceo.karnataka.gov.in/
- Delhi: https://ceodelhi.gov.in/

```bash
python -m scrapers.voter_parser \
  --file voters_pune.pdf \
  --state Maharashtra \
  --district Pune
```

Ya API se:
```
POST /api/v1/ingest/voter?state=Maharashtra&district=Pune
Body: form-data, key=file
```

### 3. Google Maps (business phone numbers)

.env mein `GOOGLE_MAPS_API_KEY` set karo (free $200/month credit).

```bash
python -m scrapers.gmaps_scraper \
  --query "health insurance office" \
  --state Maharashtra \
  --district Pune
```

---

## API Examples

### Leads filter karo
```
GET /api/v1/leads?state=Maharashtra&district=Pune&age_min=30&age_max=55&has_phone=true
```

### Specific state ke districts dekho
```
GET /api/v1/leads/districts?state=Maharashtra
```

### Stats
```
GET /api/v1/leads/stats
```

### Phone enrich karo (Google Maps / Truecaller)
```
POST /api/v1/enrich/123/phone
```

### Bulk phone enrich (ek district ke sab leads)
```
POST /api/v1/enrich/bulk-phone?state=Maharashtra&district=Pune&limit=100
```

---

## API Response Format

```json
{
  "total": 15420,
  "page": 1,
  "limit": 50,
  "pages": 309,
  "data": [
    {
      "id": 1,
      "full_name": "Rahul Sharma",
      "gender": "M",
      "age": 42,
      "phone_primary": "+919876543210",
      "email": null,
      "address_line": "H.No 45, Gandhi Nagar, Pune",
      "area": "Gandhi Nagar",
      "city": "Pune",
      "district": "Pune",
      "state": "Maharashtra",
      "pincode": "411001",
      "source": "voter_roll",
      "voter_id": "MH1234567"
    }
  ]
}
```

---

## Production Deploy (Railway / Hetzner)

```bash
# .env mein production DB URL set karo
DATABASE_URL=postgresql://user:pass@your-db-host:5432/leadgen

# Docker se sab start karo
docker-compose up -d
```
