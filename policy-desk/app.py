import hmac
import logging
import os
from typing import Annotated

from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, StringConstraints

from corpus import ROOT, SNAPSHOT
from rag import chat_graph

load_dotenv(ROOT / ".env")
app = FastAPI(title="Policy Desk")
logger = logging.getLogger(__name__)
Question = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1200)]


class ChatRequest(BaseModel):
    question: Question
    previous_question: Question | None = None


@app.get("/", include_in_schema=False)
def home():
    return FileResponse(ROOT / "web" / "index.html")


@app.get("/api/status")
def status():
    store = os.getenv("POLICY_STORE", "local")
    ready = (all(os.getenv(key) for key in ("SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY", "EMBED_MODEL", "EMBED_API_KEY"))
             if store == "supabase" else SNAPSHOT.is_file())
    return {"store": store, "generation": bool(os.getenv("CHAT_MODEL")),
            "snapshot_ready": ready,
            "access_code_required": bool(os.getenv("DEMO_ACCESS_CODE"))}


@app.post("/api/chat")
def chat(payload: ChatRequest, x_demo_access: Annotated[str, Header()] = ""):
    code = os.getenv("DEMO_ACCESS_CODE", "")
    if os.getenv("VERCEL") and (not code or os.getenv("POLICY_STORE") != "supabase"):
        raise HTTPException(503, "The hosted demo needs a Supabase store and an access code.")
    if code and not hmac.compare_digest(code.encode(), x_demo_access.encode()):
        raise HTTPException(401, "Enter the demo access code and try again.")
    if os.getenv("POLICY_STORE", "local") == "local" and not SNAPSHOT.is_file():
        raise HTTPException(503, "The handbook snapshot is missing. Run python corpus.py first.")
    try:
        state = chat_graph.invoke(payload.model_dump(exclude_none=True))
        return state["response"]
    except Exception as error:
        logger.error("Policy request failed: %s", type(error).__name__)
        raise HTTPException(503, "Policy search is unavailable. Check the server configuration.") from None


app.mount("/assets", StaticFiles(directory=ROOT / "web"), name="assets")
