from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from app.config import settings
from app.rag_engine import rag_engine


# LangChain Ollama LLM instance
llm = ChatOllama(
    model=settings.OLLAMA_TEXT_MODEL,
    base_url=settings.OLLAMA_BASE_URL,
)

# Prompt template for incident analysis with RAG context
INCIDENT_ANALYSIS_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are an expert IT Service Management analyst. "
        "You are given a new ServiceNow incident and up to 3 historically resolved "
        "incidents that are similar. Analyse the new incident using the context from "
        "the resolved incidents.\n\n"
        "First, determine the root cause, a recommended assignment group, and a confidence score (0-100) for your analysis.\n\n"
        "Your final response MUST perfectly match this exact template:\n\n"
        "Not an HIP Issue\n\n"
        "**Root-Cause**:\n"
        "- [Bullet point 1 with perfect grammar and spelling]\n"
        "- [Bullet point 2 with perfect grammar and spelling]\n\n"
        "**Recommended Assignment Group**: [Group Name], (Confidence Score: [Score]%)\n"
        "----------------------------------------------------\n\n"
        "CRITICAL INSTRUCTIONS:\n"
        "- Output EXACTLY the template above.\n"
        "- DO NOT output duplicate sections or repeat the template.\n"
        "- DO NOT use numbering (e.g., no '1.' or '2.').\n"
        "- DO NOT add any extra introductory or concluding conversational text."
    ),
    (
        "human",
        "=== NEW INCIDENT ===\n"
        "Short Description: {short_description}\n"
        "Description: {description}\n"
        "Work Notes: {work_notes}\n\n"
        "=== SIMILAR RESOLVED INCIDENTS ===\n"
        "{resolved_incidents_context}\n\n"
        "Please provide your analysis."
    ),
])

# Chain: prompt → LLM → parse string output
analysis_chain = INCIDENT_ANALYSIS_PROMPT | llm | StrOutputParser()


def analyse_incident(short_description: str, description: str, work_notes: str) -> dict:
    """
    1. Fetch top-3 similar resolved incidents from ChromaDB.
    2. Build a prompt embedding the new incident + resolved incidents.
    3. Send to the local Ollama LLM via LangChain.

    Returns:
        dict with keys: 'analysis' (LLM response text) and
        'matched_incidents' (list of matched INC numbers with scores).
    """
    query = f"{short_description} {description}".strip()

    # --- Step 1: RAG retrieval ---
    top_results = rag_engine.get_top_related_incs(query, k=3)

    # --- Step 2: Format resolved incidents context ---
    if top_results:
        context_parts = []
        matched_incidents = []
        for idx, (doc, score) in enumerate(top_results, start=1):
            inc_number = doc.metadata.get("inc_number", "N/A")
            matched_incidents.append({
                "inc_number": inc_number,
                "distance_score": round(score, 4),
            })
            context_parts.append(
                f"--- Resolved Incident #{idx} ({inc_number}) "
                f"[distance: {score:.4f}] ---\n{doc.page_content.strip()}"
            )
        resolved_context = "\n\n".join(context_parts)
    else:
        resolved_context = "No similar resolved incidents found in the knowledge base."
        matched_incidents = []

    # --- Step 3: Invoke LLM ---
    print(f"[LLM] Sending analysis prompt for: {short_description[:80]}...")
    llm_response = analysis_chain.invoke({
        "short_description": short_description,
        "description": description or "N/A",
        "work_notes": work_notes or "N/A",
        "resolved_incidents_context": resolved_context,
    })

    print(f"[LLM] Analysis complete.")
    return {
        "analysis": llm_response,
        "matched_incidents": matched_incidents,
    }
