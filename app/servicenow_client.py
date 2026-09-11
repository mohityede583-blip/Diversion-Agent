import json
from datetime import datetime, timedelta, timezone
import httpx
from app.config import settings


class ServiceNowClient:
    def __init__(self):
        self.url = settings.SERVICENOW_URL
        self.user = settings.SERVICENOW_USER
        self.pwd = settings.SERVICENOW_PASSWORD

    def fetch_incidents_from_api(self) -> list:
        """
        Simulates call to real ServiceNow Table API:
        GET /api/now/table/incident?sysparm_query=assignment_groupISEMPTY^active=true
        """
        try:
            # Real API call
            headers = {"Accept": "application/json"}
            query_url = f"{self.url}/api/now/table/incident"
            
            last_2_min = datetime.now(timezone.utc) - timedelta(minutes=5)
            two_mins_ago = last_2_min.strftime("%Y-%m-%d %H:%M:%S")
            group_name = "HIP Global"

            params = {
                "sysparm_limit": 20,
                "sysparm_query": f"assignment_group.name={group_name}^sys_updated_on>={two_mins_ago}^active=true",
                "sysparm_display_value": "true",
            }
            with httpx.Client(auth=(self.user, self.pwd), headers=headers, timeout=10.0) as client:
                resp = client.get(query_url, params=params)
                if resp.status_code == 200:
                    results = resp.json().get("result", [])
                    print(f"pulled {len(results)} incidents from API which are created on last minute")
                    return results
            return []
        except Exception as e:
            print(f"Failed to fetch from real ServiceNow API: {e}. Falling back to simulation...")
            return []

    def update_work_notes(self, sys_id: str, work_notes: str) -> bool:
        """
        Update work_notes on an existing incident via ServiceNow Table API.
        PATCH /api/now/table/incident/{sys_id}
        """
        try:
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
            patch_url = f"{self.url}/api/now/table/incident/{sys_id}"
            payload = {"work_notes": work_notes}
            with httpx.Client(auth=(self.user, self.pwd), headers=headers, timeout=10.0) as client:
                resp = client.patch(patch_url, json=payload)
                if resp.status_code == 200:
                    print(f"[SNOW] Work notes updated for incident {sys_id}")
                    return True
                else:
                    print(f"[SNOW] Failed to update work notes for {sys_id}: {resp.status_code} {resp.text}")
                    return False
        except Exception as e:
            print(f"[SNOW] Error updating work notes for {sys_id}: {e}")
            return False

    def assign_incident(self, sys_id: str, assignment_group: str, work_notes: str) -> bool:
        """
        Assign an incident to a specific assignment group and add work notes.
        PATCH /api/now/table/incident/{sys_id}

        Uses sysparm_input_display_value=true so display names (e.g. 'Network Team')
        can be sent directly without a sys_id lookup.
        """
        try:
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
            patch_url = f"{self.url}/api/now/table/incident/{sys_id}"
            params = {"sysparm_input_display_value": "true"}
            payload = {
                "assignment_group": assignment_group,
                "work_notes": work_notes,
            }
            with httpx.Client(auth=(self.user, self.pwd), headers=headers, timeout=10.0) as client:
                resp = client.patch(patch_url, json=payload, params=params)
                if resp.status_code == 200:
                    print(f"[SNOW] Incident {sys_id} assigned to '{assignment_group}'")
                    return True
                else:
                    print(f"[SNOW] Failed to assign incident {sys_id}: {resp.status_code} {resp.text}")
                    return False
        except Exception as e:
            print(f"[SNOW] Error assigning incident {sys_id}: {e}")
            return False


servicenow_client = ServiceNowClient()

