from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import os
from app.database import engine, Base
from app.routers import leads, ingest, enrich, capture

Base.metadata.create_all(bind=engine)

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")

app = FastAPI(
    title="Lead Gen API",
    description="Health insurance lead generation — filter by state, district, age, phone availability",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(leads.router)
app.include_router(ingest.router)
app.include_router(enrich.router)
app.include_router(capture.router)


@app.get("/")
def landing():
    """Public landing page — log yahan apni details bharte hain."""
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.get("/api")
def api_info():
    return {
        "service": "Lead Gen API",
        "landing_page": "/",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health")
def health():
    return {"status": "ok"}
