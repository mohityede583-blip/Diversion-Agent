import asyncio
import json
from datetime import datetime
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

# pydantic-settings in backend.config reads .env automatically,
# so we import settings first and then load_dotenv() as a backup
# for any plain os.getenv() callers elsewhere in the app.
from dotenv import load_dotenv
load_dotenv()

from app.config import settings
from app.servicenow_client import servicenow_client
from app.rag_engine import rag_engine
from app.diversion_engine import diversion_engine
from app.llm_service import analyse_incident
from langsmith.middleware import TracingMiddleware


# ──────────────────────────────────────────────
# Request / Response schemas
# ──────────────────────────────────────────────

class IncidentRequest(BaseModel):
    """Request body matching the ServiceNow incident schema."""
    number: str
    short_description: str
    description: Optional[str] = None
    work_notes: Optional[str] = None
    category: Optional[str] = None
    priority: Optional[str] = None
    urgency: Optional[str] = None
    impact: Optional[str] = None
    severity: Optional[str] = None
    incident_state: Optional[str] = None
    sys_id: Optional[str] = None
    sys_class_name: Optional[str] = "incident"
    assignment_group: Optional[str] = None
    assigned_to: Optional[str] = None
    caller_id: Optional[str] = None
    opened_by: Optional[str] = None
    opened_at: Optional[str] = None
    resolved_at: Optional[str] = None
    closed_at: Optional[str] = None
    close_code: Optional[str] = None
    close_notes: Optional[str] = None
    subcategory: Optional[str] = None
    made_sla: Optional[str] = None
    hold_reason: Optional[str] = None
    reassignment_count: Optional[int] = 0
    reopen_count: Optional[int] = 0
    sla_due: Optional[str] = None
    activity_due: Optional[str] = None
    sys_mod_count: Optional[int] = 0
    sys_updated_on: Optional[str] = None
    sys_updated_by: Optional[str] = None


# ──────────────────────────────────────────────
# App initialisation
# ──────────────────────────────────────────────

# Initialize FastAPI App
app = FastAPI(title=settings.APP_NAME, version="1.0.0")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For local development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# adding Langsmith middleware
app.add_middleware(TracingMiddleware)

# Startup event
@app.on_event("startup")
async def startup_event():
    # Bootstrap the RAG knowledge base in ChromaDB with the historical seed list
    rag_engine.seed_historical_incidents()
    # asyncio.create_task(periodic_snow_pull())

# Background task to periodically pull incidents (simulate ServiceNow webhook/polling)
async def periodic_snow_pull():
    while True:
        try:
            print("Running periodic ServiceNow incident sync...")
            new_incidents = servicenow_client.fetch_incidents_from_api()
            if new_incidents:
                print(f"Ingested {len(new_incidents)} new unassigned incident(s). Running diversion...")
                for incident in new_incidents:
                    if incident.get("number") in servicenow_client.checked_inc:
                        print(f"We have already check {incident.get('number')}. Hence ignored...")
                        continue
                    diversion_engine.assign(incident)
                    servicenow_client.checked_inc.add(incident.get("number"))
        except Exception as e:
            print(f"Error in periodic ServiceNow sync: {e}")
        # Wait 60 seconds between sync checks
        await asyncio.sleep(30)


@app.get("/app")
def get_incidents(status: Optional[str] = None):
    return {"massage": "weelcome"}


@app.post("/api/incidents/analyse")
def analyse_incident_endpoint(incident: IncidentRequest):
    """
    Accepts an incident, fetches top-3 similar resolved incidents from
    ChromaDB, builds a RAG-augmented prompt, and returns the LLM analysis.
    """
    try:
        result = analyse_incident(
            short_description=incident.short_description,
            description=incident.description or "",
            work_notes=incident.work_notes or "",
        )
        return {
            "incident_number": incident.number,
            "analysis": result["analysis"],
            "matched_incidents": result["matched_incidents"],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e}")
