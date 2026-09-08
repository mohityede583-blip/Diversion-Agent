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
from langsmith.middleware import TracingMiddleware

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
    asyncio.create_task(periodic_snow_pull())

# Background task to periodically pull incidents (simulate ServiceNow webhook/polling)
async def periodic_snow_pull():
    while True:
        try:
            print("Running periodic ServiceNow incident sync...")
            new_incidents = servicenow_client.fetch_incidents_from_api()
            if new_incidents:
                print(f"Ingested {len(new_incidents)} new unassigned incident(s). Running diversion...")
                for incident in new_incidents:
                    diversion_engine.assign(incident)
        except Exception as e:
            print(f"Error in periodic ServiceNow sync: {e}")
        # Wait 60 seconds between sync checks
        await asyncio.sleep(90)


# API Endpoints
@app.get("/app")
def get_incidents(status: Optional[str] = None):
    return {"massage": "weelcome"}
