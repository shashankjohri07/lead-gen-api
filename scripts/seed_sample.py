"""
Seeds 500 realistic sample leads so you can test the API immediately.
Usage: python scripts/seed_sample.py
"""
import sys
import os
import random
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.database import SessionLocal
from app.models import Lead, SourceType, GenderType

STATES = {
    "Maharashtra": ["Pune", "Mumbai", "Nashik", "Nagpur", "Aurangabad"],
    "Gujarat": ["Ahmedabad", "Surat", "Vadodara", "Rajkot", "Gandhinagar"],
    "Karnataka": ["Bengaluru Urban", "Mysuru", "Dharwad", "Belagavi", "Mangaluru"],
    "Rajasthan": ["Jaipur", "Jodhpur", "Udaipur", "Kota", "Ajmer"],
    "Delhi": ["Central Delhi", "South Delhi", "East Delhi", "West Delhi", "North Delhi"],
}

FIRST_NAMES = ["Rahul", "Priya", "Amit", "Sunita", "Vijay", "Kavita", "Rajesh", "Meena",
               "Suresh", "Anita", "Deepak", "Rekha", "Manoj", "Geeta", "Sanjay", "Pooja",
               "Arun", "Nisha", "Vikas", "Seema", "Ravi", "Asha", "Prakash", "Usha"]
LAST_NAMES = ["Sharma", "Patel", "Singh", "Gupta", "Kumar", "Shah", "Mehta", "Joshi",
              "Verma", "Agarwal", "Yadav", "Tiwari", "Pandey", "Dubey", "Mishra", "Srivastava"]
COMPANIES = ["Infosys Ltd", "Wipro Ltd", "TCS", "HCL Technologies", "Reliance Industries",
             "HDFC Bank", "ICICI Bank", "Mahindra & Mahindra", "Bajaj Auto", "Sun Pharma",
             None, None, None]


def random_phone():
    return f"+91{random.randint(7000000000, 9999999999)}"


def random_dob(age_min=25, age_max=65):
    days = random.randint(age_min * 365, age_max * 365)
    return date.today() - timedelta(days=days)


def seed(n: int = 500):
    db = SessionLocal()
    leads = []

    for i in range(n):
        state = random.choice(list(STATES.keys()))
        district = random.choice(STATES[state])
        first = random.choice(FIRST_NAMES)
        last = random.choice(LAST_NAMES)
        dob = random_dob()
        age = (date.today() - dob).days // 365
        gender = random.choice([GenderType.MALE, GenderType.FEMALE])
        has_phone = random.random() > 0.3
        source = random.choice([SourceType.MCA_DIRECTOR, SourceType.VOTER_ROLL])

        lead = Lead(
            full_name=f"{first} {last}",
            gender=gender,
            date_of_birth=dob,
            age=age,
            phone_primary=random_phone() if has_phone else None,
            email=f"{first.lower()}.{last.lower()}@example.com" if random.random() > 0.5 else None,
            address_line=f"H.No {random.randint(1,999)}, Main Road, {district}",
            area=f"Ward {random.randint(1,50)}",
            city=district,
            district=district,
            state=state,
            pincode=str(random.randint(400001, 999999)),
            source=source,
            company_name=random.choice(COMPANIES),
            designation="Director" if source == SourceType.MCA_DIRECTOR else None,
            voter_id=f"{''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ', k=3))}{random.randint(1000000, 9999999)}"
                     if source == SourceType.VOTER_ROLL else None,
        )
        leads.append(lead)

    db.bulk_save_objects(leads)
    db.commit()
    db.close()
    print(f"Seeded {n} sample leads.")


if __name__ == "__main__":
    seed(500)
