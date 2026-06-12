from fastapi import APIRouter, UploadFile, File, BackgroundTasks, HTTPException
from app.schemas import IngestStatusResponse
import uuid
import os
import tempfile

router = APIRouter(prefix="/api/v1/ingest", tags=["Data Ingestion"])

# track simple in-memory job status (use Redis for prod)
_jobs: dict = {}


def _run_mca(job_id: str, file_path: str):
    try:
        _jobs[job_id] = {"status": "running", "message": "Parsing MCA director CSV..."}
        from scrapers.mca_parser import parse_and_load
        count = parse_and_load(file_path)
        _jobs[job_id] = {"status": "done", "message": f"Loaded {count} directors"}
    except Exception as e:
        _jobs[job_id] = {"status": "error", "message": str(e)}


def _run_voter(job_id: str, file_path: str, state: str, district: str):
    try:
        _jobs[job_id] = {"status": "running", "message": "Parsing voter roll..."}
        from scrapers.voter_parser import parse_and_load
        count = parse_and_load(file_path, state=state, district=district)
        _jobs[job_id] = {"status": "done", "message": f"Loaded {count} voters"}
    except Exception as e:
        _jobs[job_id] = {"status": "error", "message": str(e)}


@router.post("/mca", response_model=IngestStatusResponse)
async def ingest_mca_directors(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="MCA director master CSV from mca.gov.in"),
):
    """
    Upload the MCA director master data CSV.
    Download from: https://www.mca.gov.in/content/mca/global/en/data-and-reports/data-sets/company-master-data.html
    File: director_master_data.zip → extract → upload CSV here.
    """
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Upload a CSV file")

    job_id = str(uuid.uuid4())
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".csv")
    tmp.write(await file.read())
    tmp.close()

    _jobs[job_id] = {"status": "queued", "message": "Queued"}
    background_tasks.add_task(_run_mca, job_id, tmp.name)

    return IngestStatusResponse(task_id=job_id, status="queued", message="MCA ingestion started")


@router.post("/voter", response_model=IngestStatusResponse)
async def ingest_voter_roll(
    background_tasks: BackgroundTasks,
    state: str,
    district: str,
    file: UploadFile = File(..., description="Voter roll PDF or CSV/Excel from state CEO portal"),
):
    """
    Upload voter roll file for a specific state + district.
    Download from your state's Chief Electoral Officer portal.
    Supports: PDF (auto-parsed), CSV, XLSX.
    """
    job_id = str(uuid.uuid4())
    suffix = os.path.splitext(file.filename)[1]
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tmp.write(await file.read())
    tmp.close()

    _jobs[job_id] = {"status": "queued", "message": "Queued"}
    background_tasks.add_task(_run_voter, job_id, tmp.name, state, district)

    return IngestStatusResponse(task_id=job_id, status="queued", message="Voter roll ingestion started")


@router.get("/status/{job_id}")
def get_job_status(job_id: str):
    if job_id not in _jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    return _jobs[job_id]
