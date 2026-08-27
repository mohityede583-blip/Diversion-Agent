import json
from datetime import datetime, timedelta,timezone
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
            last_min = datetime.now(timezone.utc) - timedelta(minutes=1)
            current_time=datetime.now(timezone.utc)
            formatted_time_five = last_min.strftime("%Y-%m-%d %H:%M:%S")
            formatted_time_current = current_time.strftime("%Y-%m-%d %H:%M:%S")
            params = {
                "sysparm_limit": 20,
                "sysparm_query": f"opened_at>={formatted_time_five}^opened_at<={formatted_time_current}^assignment_groupISEMPTY^active=true",
                "sysparm_display_value": "true",
            }
            with httpx.Client(auth=(self.user, self.pwd), headers=headers, timeout=10.0) as client:
                resp = client.get(query_url, params=params)
                # print("RESPONSE JSON:\n",resp)
                if resp.status_code == 200:
                    results = resp.json().get("result", [])
                    # print("GET SNOW INCIDENT CALL:\n",json.dumps(results,indent=4))
                    print(f"pulled {len(results)} incidents from API which are created on last minute")
                    # MAP RESULTS
        except Exception as e:
            print(f"Failed to fetch from real ServiceNow API: {e}. Falling back to simulation...")


servicenow_client = ServiceNowClient()
