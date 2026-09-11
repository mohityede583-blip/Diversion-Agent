import json
import httpx
from app.rag_engine import rag_engine
from app.config import settings


# Threshold for raw distance score from Chroma.
# Lower distance = higher similarity.
# Incidents with distance < this value are considered a strong match.
SIMILARITY_THRESHOLD = 0.8

# HIP assignment agent endpoint
HIP_PUSH_URL = "http://localhost:8001/api/incidents/push"


class DiversionEngine:

    def assign(self, incident: dict) -> None:
        """
        Diversion logic for a single unassigned incident.

        1. Build a search query from the incident's short_description + description.
        2. Query the vector DB for the most relevant resolved incident.
        3. If the raw distance score is < 0.5 (strong match):
             → Auto-assign the incident to the matched assignment group in ServiceNow.
        4. Else (weak / no match — treated as a HIP incident):
             → Push the incident to the HIP assignment agent at localhost:8000.
             → Update work notes: "This is HIP incident hence, diverting to assignment agent".
        """
        # Lazy import to avoid circular dependency
        # (servicenow_client imports at module level; diversion_engine is imported by main)
        from app.servicenow_client import servicenow_client

        sys_id = incident.get("sys_id", "")
        number = incident.get("number", "unknown")
        short_desc = incident.get("short_description", "")
        description = incident.get("description", "")

        query = f"{short_desc} {description}".strip()
        if not query:
            print(f"[DIVERSION] Incident {number} has no description; skipping.")
            return

        print(f"[DIVERSION] Processing incident {number} ...")

        # --- Step 1: Similarity search ---
        result = rag_engine.get_related_inc(query)

        if result is not None:
            doc, score = result
            print(f"[DIVERSION] Incident {number} | raw distance score: {score}")

            if score < SIMILARITY_THRESHOLD:
                # --- Strong match → auto-assign ---
                # Extract assignment group from the matched document's content.
                # The seeded document text contains a line like:
                #   "Assignment Group: <group_name>"
                assignment_group = self._extract_assignment_group(doc.page_content)
                matched_inc = doc.metadata.get("inc_number", "N/A")

                work_notes = (
                    f"[Auto-Assigned by Diversion Agent]\n"
                    f"Matched resolved incident: {matched_inc}\n"
                    f"Distance score: {score:.4f}\n"
                    f"Assignment group: {assignment_group}"
                )

                print(f"[DIVERSION] Assigning {number} → '{assignment_group}' (matched {matched_inc})")
                servicenow_client.assign_incident(sys_id, assignment_group, work_notes)
                return

        # --- Weak / no match → HIP incident ---
        print(f"[DIVERSION] Incident {number} has no strong match; pushing to HIP agent.")

        if incident.get("number") in servicenow_client.checked_inc:
            return
        servicenow_client.update_work_notes(sys_id,"This is HIP incident hence, diverting to assignment agent")
        self._push_to_hip_agent(incident)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_assignment_group(doc_content: str) -> str:
        """
        Parse 'Assignment Group: <value>' from the seeded document text.
        Falls back to 'Unassigned' if the line is missing.
        """
        for line in doc_content.splitlines():
            stripped = line.strip()
            if stripped.lower().startswith("assignment group:"):
                return stripped.split(":", 1)[1].strip()
        return "Unassigned"

    @staticmethod
    def _push_to_hip_agent(incident: dict) -> None:
        """
        POST the incident to the HIP assignment agent running on localhost:8000.
        Maps ServiceNow incident fields to the PushIncidentRequest schema.
        """
        payload = {
            "number": str(incident.get("number", "")),
            "short_description": str(incident.get("short_description", "")),
            "description": str(incident.get("description")),
            "category": str(incident.get("category", "L1 Support")),
            "priority": str(incident.get("priority", "3")),
            "urgency": str(incident.get("urgency", "3")),
            "sla_limit": str(incident.get("sla_due")),
            "status": "Unassigned",
            "assigned_to": str(incident.get("assigned_to")),
            "assigned_at": None,
            "created_at": str(incident.get("opened_at")),
            "rejection_count": 0,
            "rejected_associates": "[]",
            "sys_id": str(incident.get("sys_id")),
            "sys_class_name": str(incident.get("sys_class_name", "incident")),
            "sys_mod_count": int(incident.get("sys_mod_count", 0)),
            "sys_updated_on": str(incident.get("sys_updated_on")),
            "sys_updated_by": str(incident.get("sys_updated_by", "manual_push")),
            "incident_state": str(incident.get("incident_state", "1")),
            "impact": str(incident.get("impact", "3")),
            "severity": str(incident.get("severity", "3")),
            "subcategory": str(incident.get("subcategory")),
            "close_code": str(incident.get("close_code")),
            "close_notes": str(incident.get("close_notes")),
            "made_sla": str(incident.get("made_sla")),
            "hold_reason": str(incident.get("hold_reason")),
            "reassignment_count": int(incident.get("reassignment_count", 0)),
            "reopen_count": int(incident.get("reopen_count", 0)),
            "opened_at": str(incident.get("opened_at")),
            "resolved_at": str(incident.get("resolved_at")),
            "closed_at": str(incident.get("closed_at")),
            "sla_due": str(incident.get("sla_due")),
            "activity_due": str(incident.get("activity_due")),
            "opened_by_ref": str(incident.get("opened_by")),
            "caller_id_ref": str(incident.get("caller_id")),
            "assignment_group_ref": str(incident.get("assignment_group")),
            "assigned_to_ref": str(incident.get("assigned_to")),
            "raw_payload": None,
        }
        print('push payload',json.dumps(payload))

        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.post(HIP_PUSH_URL, json=payload)
                if resp.status_code in (200, 201):
                    print(f"[HIP] Incident {payload['number']} pushed to HIP agent successfully.")
                else:
                    print(
                        f"[HIP] Failed to push incident {payload['number']}: "
                        f"{resp.status_code} {resp.text}"
                    )
        except Exception as e:
            print(f"[HIP] Error pushing incident {payload['number']} to HIP agent: {e}")


diversion_engine = DiversionEngine()