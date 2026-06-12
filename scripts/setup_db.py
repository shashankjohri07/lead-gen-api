"""
Creates all DB tables. Run once before starting the API.
Usage: python scripts/setup_db.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.database import engine, Base
import app.models  # noqa: ensure models are registered

Base.metadata.create_all(bind=engine)
print("Database tables created successfully.")
