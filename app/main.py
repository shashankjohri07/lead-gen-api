from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base
from app.routers import leads, ingest, enrich

Base.metadata.create_all(bind=engine)

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


@app.get("/")
def root():
    return {
        "service": "Lead Gen API",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health")
def health():
    return {"status": "ok"}
