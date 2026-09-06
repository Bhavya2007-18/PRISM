"""
PRISM Backend — FastAPI application
Main entry point with all API endpoints.
"""
import hashlib
import hmac
import os
import sys
import base64
import json
import re
import time
import uuid
import asyncio
import logging

# Make sibling modules importable whether launched as `uvicorn backend.main:app`
# (from the repo root, per render.yaml) or `uvicorn main:app` (from backend/).
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, HTTPException, Request, Query, WebSocket, WebSocketDisconnect, UploadFile, File, Form, Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
import httpx
from dotenv import load_dotenv

load_dotenv(override=True)

logger = logging.getLogger("prism.main")

# ── Auth configuration ────────────────────────────────────────────────────
# For demo/development: simple shared credentials
# In production: replace with a real auth provider (Clerk, Auth0, Supabase)
DEMO_AGENT_USERNAME = os.getenv("AGENT_USERNAME", "agent")
DEMO_AGENT_PASSWORD = os.getenv("AGENT_PASSWORD", "prism2024")
SECRET_KEY = os.getenv("JWT_SECRET", "prism-dev-secret-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 8  # 8 hours

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token", auto_error=False)


def create_access_token(data: dict) -> str:
    """Create a JWT access token."""
    try:
        from jose import jwt
        from datetime import datetime, timedelta
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode.update({"exp": expire})
        return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    except ImportError:
        # python-jose not installed — return a simple token for demo
        return base64.b64encode(json.dumps(data).encode()).decode()


def get_current_user(token: str = Depends(oauth2_scheme)) -> Optional[dict]:
    """Decode and validate JWT. Returns user dict or None if invalid."""
    if not token:
        return None
    try:
        from jose import jwt, JWTError
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except Exception:
        # Fall back to base64 demo token
        try:
            data = json.loads(base64.b64decode(token).decode())
            return data
        except Exception:
            return None


def require_auth(user: Optional[dict] = Depends(get_current_user)) -> dict:
    """Dependency that requires authentication. Raises 401 if not authenticated."""
    if user is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


# ── RBAC roles ────────────────────────────────────────────────────────────
class UserRole:
    USER       = "USER"
    AGENT      = "AGENT"
    SUPERVISOR = "SUPERVISOR"
    ADMIN      = "ADMIN"
    OWNER      = "OWNER"

ROLE_HIERARCHY = {
    UserRole.USER:       0,
    UserRole.AGENT:      1,
    UserRole.SUPERVISOR: 2,
    UserRole.ADMIN:      3,
    UserRole.OWNER:      4,
}


def require_role(min_role: str):
    """
    Dependency factory: require the authenticated user to have at least min_role.
    Usage: Depends(require_role(UserRole.AGENT))
    """
    def _checker(user: Optional[dict] = Depends(get_current_user)) -> dict:
        if user is None:
            raise HTTPException(status_code=401, detail="Authentication required")
        user_role = user.get("role", UserRole.USER)
        if ROLE_HIERARCHY.get(user_role, 0) < ROLE_HIERARCHY.get(min_role, 0):
            raise HTTPException(
                status_code=403,
                detail=f"Requires {min_role} role, but user has {user_role}"
            )
        return user
    return _checker


import re as _re

_CHANNEL_PATTERN = _re.compile(r'^[a-zA-Z0-9_-]{1,64}$')

def validate_channel(channel: str) -> str:
    """Dependency: validate channel name format."""
    if not _CHANNEL_PATTERN.match(channel):
        raise HTTPException(
            status_code=400,
            detail="Invalid channel name. Use only letters, numbers, hyphens and underscores (max 64 chars)."
        )
    return channel


def sanitize_error(e: Exception) -> str:
    """
    Return a safe error message string.
    Strips file paths, credentials, and internal details from exception messages.
    Never expose: API keys, file paths, stack traces, internal module names.
    """
    msg = str(e)
    # Remove file path patterns
    msg = _re.sub(r'[A-Za-z]:\\[^\s"\']+', '[path]', msg)
    msg = _re.sub(r'/[a-zA-Z0-9_\-./]+\.py', '[module]', msg)
    # Remove anything that looks like an API key (long alphanumeric strings)
    msg = _re.sub(r'\b[A-Za-z0-9]{32,}\b', '[redacted]', msg)
    # Truncate to 200 chars
    return msg[:200]


app = FastAPI(title="PRISM Backend", version="1.0.0")

@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Add X-Request-ID header to every request and response."""
    request_id = request.headers.get("X-Request-ID", uuid.uuid4().hex[:12])
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response

frontend_url = os.getenv("FRONTEND_URL", "")
allowed_origins = [
    "http://localhost:5173",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "http://localhost:4173",
]
if frontend_url:
    for origin in frontend_url.split(","):
        origin_clean = origin.strip().rstrip("/")
        if origin_clean and origin_clean not in allowed_origins:
            allowed_origins.append(origin_clean)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins if "*" not in allowed_origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Rate limiting ─────────────────────────────────────────────────────────
try:
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.util import get_remote_address
    from slowapi.errors import RateLimitExceeded

    limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    _RATE_LIMITING_ENABLED = True
except ImportError:
    limiter = None
    _RATE_LIMITING_ENABLED = False


def _rate_limit(limit: str):
    """Returns a rate limit decorator if slowapi is available, else no-op."""
    if limiter is not None:
        return limiter.limit(limit)
    # No-op decorator when slowapi not installed
    def _noop(func):
        return func
    return _noop


@app.on_event("startup")
async def startup_checks():
    """Validate environment and log service status on startup."""
    import logging
    startup_logger = logging.getLogger("prism.startup")

    checks = {
        "AGORA_APP_ID":           bool(os.getenv("AGORA_APP_ID")),
        "LLM_API_KEY":            bool(os.getenv("LLM_API_KEY")),
        "AGORA_CUSTOMER_ID":      bool(os.getenv("AGORA_CUSTOMER_ID")),
        "JWT_SECRET_custom":      os.getenv("JWT_SECRET", "") not in ("", "prism-dev-secret-change-in-production"),
        "DEBUG_ENDPOINTS_off":    os.getenv("ENABLE_DEBUG_ENDPOINTS", "false").lower() != "true",
    }

    startup_logger.info("=" * 60)
    startup_logger.info("PRISM Backend starting up")
    startup_logger.info("=" * 60)
    for key, ok in checks.items():
        status = "OK" if ok else "WARN"
        startup_logger.info(f"  [{status}] {key}")

    if not checks["AGORA_APP_ID"]:
        startup_logger.warning("  AGORA_APP_ID not set — voice sessions will use demo mode")
    if not checks["LLM_API_KEY"]:
        startup_logger.warning("  LLM_API_KEY not set — AI responses will use fallback")
    if not checks["JWT_SECRET_custom"]:
        startup_logger.warning("  JWT_SECRET is default dev value — change before production!")

    # Initialize database if available
    try:
        from database import get_engine, _create_tables_sql
        if get_engine() is not None:
            _create_tables_sql()
            startup_logger.info("  [OK] Database initialized")
        else:
            startup_logger.warning("  [WARN] Database unavailable — data will not persist")
    except Exception as db_e:
        startup_logger.warning(f"  [WARN] Database init: {sanitize_error(db_e)}")

    # Initialize knowledge base (RAG)
    enable_rag = os.getenv("ENABLE_RAG", "false").lower() == "true"
    try:
        from knowledge_base import get_knowledge_base
        kb = get_knowledge_base()
        if enable_rag:
            chunk_count = kb.load_from_disk()
            status = kb.status()
            startup_logger.info(
                f"  [OK] Knowledge base loaded: {chunk_count} chunks "
                f"({status['embedding_model'] if status['embeddings_available'] else 'keyword search only'})"
            )
        else:
            startup_logger.info("  [--] Knowledge base ENABLE_RAG=false — passively available")
    except Exception as kb_e:
        startup_logger.warning(f"  [WARN] Knowledge base init: {sanitize_error(kb_e)}")

    startup_logger.info("=" * 60)


# ── Module-level state ────────────────────────────────────────────────
# Active Agora agent sessions: channel -> agent_id
active_sessions: dict[str, str] = {}

# Default LLM model — matches llm_service.get_llm_config() and .env.example
DEFAULT_LLM_MODEL = "openai/gpt-oss-20b"


# ── Pydantic models ───────────────────────────────────────────────────

class SessionStartRequest(BaseModel):
    channel: str
    user_uid: int
    language: Optional[str] = None
    locale: Optional[str] = None

class SessionStopRequest(BaseModel):
    agent_id: str
    channel: str

class ChatRequest(BaseModel):
    message: str
    channel: str = "prism-text"
    language: Optional[str] = None
    locale: Optional[str] = None


# ── /health ───────────────────────────────────────────────────────────

@app.get("/health")
def health():
    from audio_pipeline import get_pipeline_health
    from database import get_db_health
    pipeline = get_pipeline_health()
    db_health = get_db_health()
    return {
        "status": "ok",
        "service": "prism-backend",
        "pipeline": pipeline,
        "database": db_health,
    }


# ── /auth ─────────────────────────────────────────────────────────────

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    role: str


@app.post("/auth/token", response_model=TokenResponse)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """Authenticate and return a JWT access token."""
    # Demo: single hardcoded agent credential
    # In production: query user database
    if (form_data.username == DEMO_AGENT_USERNAME and
            form_data.password == DEMO_AGENT_PASSWORD):
        token = create_access_token({
            "sub": form_data.username,
            "role": "AGENT",
            "username": form_data.username,
        })
        return TokenResponse(access_token=token, token_type="bearer", role="AGENT")
    raise HTTPException(status_code=401, detail="Invalid credentials")


@app.get("/auth/me")
async def get_me(user: dict = Depends(require_auth)):
    """Return current authenticated user info."""
    return {"username": user.get("username"), "role": user.get("role")}


@app.get("/chat/test")
async def chat_test():
    """Debug endpoint — tests LLM connectivity and returns basic connectivity status."""
    if os.getenv("ENABLE_DEBUG_ENDPOINTS", "false").lower() != "true":
        raise HTTPException(status_code=404, detail="Not found")
    llm_base_url = os.getenv("LLM_BASE_URL", "")
    llm_api_key = os.getenv("LLM_API_KEY", "")
    llm_model = os.getenv("LLM_MODEL", DEFAULT_LLM_MODEL)

    result = {
        "llm_base_url": llm_base_url,
        "llm_model": llm_model,
        "api_key_configured": bool(llm_api_key),
    }

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(
                f"{llm_base_url}/chat/completions",
                headers={"Authorization": f"Bearer {llm_api_key}", "Content-Type": "application/json"},
                json={
                    "model": llm_model,
                    "messages": [{"role": "user", "content": "Say: hello"}],
                    "stream": False,
                    "max_tokens": 20,
                }
            )
        result["status_code"] = resp.status_code
        if resp.status_code == 200:
            result["success"] = True
        else:
            result["success"] = False
    except Exception as e:
        result["success"] = False
        result["error"] = "Failed to connect to LLM service"

    return result


# ── /token ────────────────────────────────────────────────────────────

@app.get("/token")
@_rate_limit("10/minute")
async def get_token(request: Request, channel: str = Query(...), uid: int = Query(...)):
    """Generate an Agora RTC token for the given channel and UID."""
    app_id = os.getenv("AGORA_APP_ID", "")
    app_cert = os.getenv("AGORA_APP_CERTIFICATE", "")

    if not app_id or not app_cert:
        return {
            "token": "demo-token-no-credentials",
            "channel": channel,
            "uid": uid,
            "app_id": app_id or "demo",
            "warning": "No Agora credentials configured — demo mode"
        }

    try:
        from agora_token_builder import RtcTokenBuilder
        expiry = int(time.time()) + 3600
        token = RtcTokenBuilder.buildTokenWithUid(
            app_id, app_cert, channel, uid, 1, expiry
        )
        return {"token": token, "channel": channel, "uid": uid, "app_id": app_id}
    except Exception as e:
        return {
            "token": "error-generating-token",
            "channel": channel,
            "uid": uid,
            "app_id": app_id,
            "error": sanitize_error(e)
        }


# ── /session/start ────────────────────────────────────────────────────

@app.post("/session/start")
async def start_session(req: SessionStartRequest):
    """Start an Agora Conversational AI agent in the channel."""
    app_id = os.getenv("AGORA_APP_ID", "")
    app_cert = os.getenv("AGORA_APP_CERTIFICATE", "")
    customer_id = os.getenv("AGORA_CUSTOMER_ID", "")
    customer_secret = os.getenv("AGORA_CUSTOMER_SECRET", "")
    backend_url = os.getenv("BACKEND_PUBLIC_URL", "http://localhost:8001")
    llm_key = os.getenv("LLM_API_KEY", "")
    llm_model = os.getenv("LLM_MODEL", DEFAULT_LLM_MODEL)
    # Ensure case state exists for this channel
    from context import get_or_create_case, cases as _cases
    # If previous session was escalated or taken over, start fresh
    existing = _cases.get(req.channel)
    if existing and (existing.escalated or existing.taken_over):
        del _cases[req.channel]
    case = get_or_create_case(req.channel)
    case.connection_state = "CONNECTING"
    case.agora_channel = req.channel
    case.voice_mode = "agora_rtc"
    if req.locale:
        case.locale = req.locale
    if req.language and req.language not in case.language:
        case.language.append(req.language)

    if not app_id or not customer_id or not customer_secret:
        mock_id = f"demo-agent-{uuid.uuid4().hex[:8]}"
        active_sessions[req.channel] = mock_id
        case.connection_state = "CONNECTED"
        case.agora_agent_id = mock_id
        return {
            "agent_id": mock_id,
            "mode": "demo",
            "warning": "No Agora credentials — demo mode active"
        }

    AGENT_UID = 12345
    try:
        from agora_token_builder import RtcTokenBuilder
        expiry = int(time.time()) + 7200
        agent_token = RtcTokenBuilder.buildTokenWithUid(
            app_id, app_cert, req.channel, AGENT_UID, 1, expiry
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Token generation failed: {e}")

    # Agora forwards each turn to /llm-proxy, which runs the PRISM voice agent.
    # We pass the same system prompt + tool schemas the agent itself uses so the
    # Agora agent config is consistent with the live brain.
    from voice_agent import PRISM_VOICE_ASSISTANT_SYSTEM_PROMPT, get_tool_schemas

    # LLM proxy URL — Agora will POST to this endpoint for each conversation turn
    llm_proxy_url = f"{backend_url}/llm-proxy?channel={req.channel}"

    payload = {
        "name": f"prism-{req.channel}-{uuid.uuid4().hex[:6]}",
        "properties": {
            "channel": req.channel,
            "token": agent_token,
            "agent_rtc_uid": str(AGENT_UID),
            "remote_rtc_uids": [str(req.user_uid)],
            "idle_timeout": int(os.getenv("AGORA_IDLE_TIMEOUT", "60")),
            "llm": {
                "url": llm_proxy_url,
                "api_key": llm_key,
                "model": llm_model,
                "stream": True,
                "greeting_message": "Namaste! Main PRISM hoon. Aap kaise help kar sakta hoon?",
                "max_tokens": 200,
                "temperature": 0.7,
                "system_messages": [{"role": "system", "content": PRISM_VOICE_ASSISTANT_SYSTEM_PROMPT}],
                "tools": get_tool_schemas(case),
            },
            "tts": {
                "vendor": "agora",
                "params": {
                    "voice_id": "female-south-asian-en",
                },
            },
            "asr": {
                "language": "hi-IN,en-US",
            },
            "vad": {
                "silence_duration_ms": 480,
                "speech_duration_ms": 150,
                "interrupt_duration_ms": 160,
            },
        }
    }

    auth = base64.b64encode(f"{customer_id}:{customer_secret}".encode()).decode()

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"https://api.agora.io/api/conversational-ai/v2/projects/{app_id}/agents/start",
            headers={
                "Authorization": f"Basic {auth}",
                "Content-Type": "application/json",
            },
            json=payload,
        )

    if resp.status_code not in (200, 201):
        raise HTTPException(
            status_code=502,
            detail=f"Agora agent start failed [{resp.status_code}]: {resp.text}"
        )

    data = resp.json()
    agent_id = data.get("agent_id", "")
    active_sessions[req.channel] = agent_id
    case.connection_state = "CONNECTED"
    case.agora_agent_id = agent_id
    return {"agent_id": agent_id, "state": data.get("state", "RUNNING"), "channel": req.channel}


# ── /session/stop ─────────────────────────────────────────────────────

@app.post("/session/stop")
async def stop_session(req: SessionStopRequest):
    """Stop the Agora Conversational AI agent."""
    app_id = os.getenv("AGORA_APP_ID", "")
    customer_id = os.getenv("AGORA_CUSTOMER_ID", "")
    customer_secret = os.getenv("AGORA_CUSTOMER_SECRET", "")

    active_sessions.pop(req.channel, None)

    from context import cases
    if req.channel in cases:
        cases[req.channel].connection_state = "DISCONNECTED"
        cases[req.channel].session_ended = True

    if not app_id or req.agent_id.startswith("demo-"):
        return {"status": "stopped", "mode": "demo"}

    auth = base64.b64encode(f"{customer_id}:{customer_secret}".encode()).decode()

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(
            f"https://api.agora.io/api/conversational-ai/v2/projects/{app_id}/agents/{req.agent_id}/stop",
            headers={"Authorization": f"Basic {auth}"},
        )

    return {"status": "stopped", "agora_status": resp.status_code}


# ── /session/status/{channel} ─────────────────────────────────────────

@app.get("/session/status/{channel}")
async def session_status(channel: str):
    """Return current connection and session state for a channel."""
    from context import cases
    from prism_state import derive_voice_state, PrismState

    if channel not in cases:
        return {
            "channel": channel,
            "connection_state": "DISCONNECTED",
            "voice_state": PrismState.IDLE.value,
            "active": False,
            "agent_id": active_sessions.get(channel),
        }

    case = cases[channel]
    return {
        "channel": channel,
        "connection_state": getattr(case, "connection_state", "UNKNOWN"),
        "voice_state": derive_voice_state(case),
        "active": not case.escalated and not getattr(case, "session_ended", False),
        "agent_id": active_sessions.get(channel),
        "reconnect_attempts": getattr(case, "reconnect_attempts", 0),
    }


# ── /mock/transaction/{tx_id} ─────────────────────────────────────────

@app.get("/mock/transaction/{tx_id}")
async def mock_transaction(tx_id: str):
    """Mock transaction lookup — standalone REST endpoint."""
    from tools import check_transaction
    return check_transaction(tx_id)


# ── /llm-proxy ────────────────────────────────────────────────────────

@app.post("/llm-proxy")
async def llm_proxy(request: Request, channel: str = Query(default="prism-demo")):
    """
    Voice turn handler. Agora's Conversational AI agent POSTs each turn here as an
    OpenAI-style chat completion request; PRISM runs the voice agent (LLM tool
    calling + deterministic policy gate) and streams back the reply as SSE.
    """
    from voice_agent import run_agent_turn

    # Validate Agora shared secret if configured
    agora_secret = os.getenv("AGORA_LLM_PROXY_SECRET", "")
    if agora_secret:
        sig_header = request.headers.get("X-Agora-Signature", "")
        if not sig_header:
            raise HTTPException(status_code=401, detail="Missing X-Agora-Signature header")
        # Agora signs the request body with HMAC-SHA256
        body_bytes = await request.body()
        expected = hmac.new(agora_secret.encode(), body_bytes, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig_header, expected):
            raise HTTPException(status_code=401, detail="Invalid signature")

    try:
        body = await request.json()
    except Exception:
        body = {}

    messages: list = body.get("messages", [])
    model: str = body.get("model", os.getenv("LLM_MODEL", DEFAULT_LLM_MODEL))

    result = await run_agent_turn(channel, messages)

    reply_content = result.get("content", "")
    return _streaming_response(model, reply_content)


# ── Helper functions ──────────────────────────────────────────────────


def _build_ai_state(case, action, reason: str, tool_executed=None, tool_result=None, tool_status=None) -> dict:
    """
    Build structured ai_state for frontend consumption.
    Represents PRISM's current operational state -- not internal reasoning.
    Safe to expose. Never exposes API keys, prompts, or chain-of-thought.
    """
    from confidence import get_confidence_report

    report = get_confidence_report(case)

    phase_map = {
        "ASK": "THINKING", "CONFIRM": "THINKING",
        "TOOL_CALL": "ACTING", "RESOLVE": "SPEAKING", "ESCALATE": "ESCALATING",
        "FAILED": "FAILED",
    }
    action_label_map = {
        "ASK": "ASK_CLARIFICATION", "CONFIRM": "CONFIRM_INFORMATION",
        "TOOL_CALL": "VERIFY_TRANSACTION", "RESOLVE": "RESOLVE_CASE",
        "ESCALATE": "ESCALATE_TO_HUMAN",
    }

    action_val = action.value if hasattr(action, "value") else str(action)
    phase = phase_map.get(action_val, "THINKING")
    action_label = action_label_map.get(action_val, "UNDERSTAND_REQUEST")

    if tool_status == "running":
        phase = "ACTING"
    elif tool_status == "completed" and action_val != "ESCALATE":
        phase = "SPEAKING"
    elif tool_status == "failed":
        phase = "ESCALATING"
    if case.taken_over:
        phase = "HUMAN_CONNECTED"

    safe_tool_result = None
    if tool_result and isinstance(tool_result, dict) and tool_result.get("success"):
        safe_tool_result = {
            k: v for k, v in tool_result.items()
            if k in ("transaction_id", "amount", "status", "order_status", "merchant")
        }

    return {
        "phase": phase,
        "intent": case.intent,
        "language": list(case.language) if case.language else [],
        "confidence": report.display_score,
        "confidence_label": report.overall_label,
        "confidence_fields": {k: round(float(v), 2) if isinstance(v, float) else str(v) for k, v in report.fields.items()},
        "action": action_label,
        "verified": list(case.verified),
        "unverified": list(case.unverified),
        "tool": tool_executed,
        "tool_status": tool_status,
        "tool_result": safe_tool_result,
        "blocking_fields": report.blocking_fields,
        # ── RAG citations (sources used to answer this turn) ────────────
        "rag_citations": getattr(case, "rag_citations", []),
        # ── Memory consent & summary ────────────────────────────────────
        "memory_consent": getattr(case, "memory_consent", False),
        "short_term_memory_keys": list(getattr(case, "short_term_memory", {}).keys()),
        # ── Deterministic policy gate (PRISM's escalation authority) ──────
        "policy_decision": case.policy_decision,
        "policy_reason": case.policy_reason,
    }


def _safe_transcript(case) -> list:
    """Return the user/assistant turns as a safe transcript for the live UI."""
    out = []
    for m in case.conversation_history:
        role = m.get("role")
        content = m.get("content")
        if role in ("user", "assistant") and content:
            out.append({"role": role, "content": content})
    return out


def _streaming_response(model: str, content: str, original: dict = None) -> StreamingResponse:
    """
    Return content as an SSE streaming response.
    Splits response at sentence boundaries for lower perceived TTS latency.
    Agora expects OpenAI streaming format.
    """
    from response_generator import sentence_segment

    resp_id = (original or {}).get("id", f"chatcmpl-{uuid.uuid4().hex[:8]}")
    created = (original or {}).get("created", int(time.time()))

    # Split into sentences for streaming — Agora can start TTS on first sentence
    # while the rest is still being sent
    sentences = sentence_segment(content) if content else [""]
    if not sentences:
        sentences = [content or ""]

    async def event_stream():
        for i, sentence in enumerate(sentences):
            chunk = json.dumps({
                "id": resp_id,
                "object": "chat.completion.chunk",
                "created": created,
                "model": model,
                "choices": [{
                    "index": 0,
                    "delta": {
                        "role": "assistant" if i == 0 else None,
                        "content": sentence + (" " if i < len(sentences) - 1 else ""),
                    },
                    "finish_reason": None,
                }]
            })
            yield f"data: {chunk}\n\n"

        done_chunk = json.dumps({
            "id": resp_id,
            "object": "chat.completion.chunk",
            "created": created,
            "model": model,
            "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]
        })
        yield f"data: {done_chunk}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        }
    )


# ── /chat (text mode) ─────────────────────────────────────────────────

@app.post("/chat")
@_rate_limit("30/minute")
async def chat(request: Request, req: ChatRequest):
    """
    Text-mode chat endpoint. Runs the same PRISM voice agent as the voice path
    (LLM tool calling + deterministic policy gate), so text and voice behave
    identically.
    """
    from voice_agent import run_agent_turn
    from context import get_or_create_case

    channel = req.channel
    case = get_or_create_case(channel)
    if req.language and req.language not in case.language:
        case.language.append(req.language)

    incoming_messages = list(case.conversation_history) + [{"role": "user", "content": req.message}]
    result = await run_agent_turn(channel, incoming_messages)

    reply_text = result.get("content", "")
    tool_executed = result.get("tool_executed")

    action_val = "ESCALATE" if case.escalated else ("TOOL_CALL" if tool_executed else "RESOLVE")
    tool_status = "completed" if tool_executed else None

    return {
        "reply": reply_text,
        "escalated": case.escalated,
        "case_id": case.case_id if case.escalated else None,
        "action": action_val,
        "reason_for_escalation": (case.escalation_reason if case.escalated else None),
        "policy_decision": case.policy_decision,
        "turn_id": f"turn_{uuid.uuid4().hex[:8]}",
        "ai_state": _build_ai_state(case, action_val, case.escalation_reason or "", tool_executed=tool_executed, tool_status=tool_status),
    }


# ── /cases ────────────────────────────────────────────────────────────

@app.get("/cases")
async def get_cases():
    """Return all escalated cases for the human agent dashboard."""
    from context import escalated_cases
    return {"cases": list(escalated_cases.values())}


@app.get("/cases/{case_id}")
async def get_case(case_id: str):
    """Return a specific escalated case."""
    from context import escalated_cases
    if case_id not in escalated_cases:
        raise HTTPException(status_code=404, detail="Case not found")
    return escalated_cases[case_id]


@app.post("/cases/{case_id}/takeover")
async def takeover_case(case_id: str):
    """Mark a case as taken over by a human agent."""
    from context import escalated_cases, cases

    if case_id not in escalated_cases:
        raise HTTPException(status_code=404, detail="Case not found")

    escalated_cases[case_id]["taken_over"] = True
    escalated_cases[case_id]["status"] = "TAKEN_OVER"

    # Update the live case state too
    for channel, case in cases.items():
        if case.case_id == case_id:
            case.taken_over = True
            break

    # Persist takeover to database
    try:
        from database import get_case_repository
        repo = get_case_repository()
        repo.save_session(case_id, case_id, "TAKEN_OVER")
    except Exception:
        pass

    print(f"[PRISM] ✅ Human agent took over case {case_id}")
    return {"status": "taken_over", "case_id": case_id}


# ── /debug/case (dev only) ────────────────────────────────────────────

@app.get("/debug/case/{channel}")
async def debug_case(channel: str):
    """Return current case state for a channel (dev/demo use)."""
    if os.getenv("ENABLE_DEBUG_ENDPOINTS", "false").lower() != "true":
        raise HTTPException(status_code=404, detail="Not found")
    from context import cases
    from confidence import get_confidence_report
    from decision import decide
    from prism_state import derive_voice_state
    if channel not in cases:
        return {"error": "no case for this channel"}
    case = cases[channel]
    report = get_confidence_report(case)
    action, reason = decide(case)

    return {
        "case": {
            "case_id": case.case_id,
            "intent": case.intent,
            "transaction_id": case.transaction_id,
            "amount": case.amount,
            "payment_status": case.payment_status,
            "order_status": case.order_status,
            "duplicate_charge": case.duplicate_charge,
            "language": case.language,
            "locale": case.locale,
            "voice_mode": case.voice_mode,
            "verified": case.verified,
            "unverified": case.unverified,
            "escalated": case.escalated,
            "escalation_reason": case.escalation_reason,
            "policy_decision": case.policy_decision,
            "policy_reason": case.policy_reason,
            "taken_over": case.taken_over,
            "last_user_text": case.last_user_text,
        },
        "confidence": {
            "fields": {k: round(float(v), 2) if isinstance(v, float) else str(v) for k, v in report.fields.items()},
            "display_score": report.display_score,
            "label": report.overall_label,
            "blocking_fields": report.blocking_fields,
        },
        "next_action": action.value,
        "next_reason": reason,
        "voice_state": derive_voice_state(case),
        "ai_state": _build_ai_state(case, action, reason),
    }


# ── /state/{channel} — lightweight realtime state polling ────────────────

@app.get("/state/{channel}")
async def get_channel_state(channel: str):
    """
    Lightweight real-time state for frontend ThinkingPanel polling + live
    transcript. Returns only safe operational state -- no internal data.
    """
    from context import cases
    from decision import decide
    from prism_state import derive_voice_state, PrismState

    if channel not in cases:
        return {
            "channel": channel,
            "voice_state": PrismState.IDLE.value,
            "ai_state": None,
            "escalated": False,
            "taken_over": False,
            "transcript": [],
        }

    case = cases[channel]
    action, reason = decide(case)

    return {
        "channel": channel,
        "case_id": case.case_id,
        "voice_state": derive_voice_state(case),
        "ai_state": _build_ai_state(case, action, reason),
        "escalated": case.escalated,
        "taken_over": case.taken_over,
        "transcript": _safe_transcript(case),
        "barge_in": getattr(case, 'barge_in_active', False),
    }


# ── /active-state — the most recently active channel (voice or text) ─────

@app.get("/active-state")
async def get_active_state():
    """
    Return the state of the most recently active channel so the agent dashboard
    follows whichever channel the customer is actually on (voice or text),
    instead of being pinned to a hard-coded channel.
    """
    from context import cases
    from decision import decide
    from prism_state import derive_voice_state, PrismState

    if not cases:
        return {
            "channel": None,
            "voice_state": PrismState.IDLE.value,
            "ai_state": None,
            "escalated": False,
            "taken_over": False,
            "transcript": [],
        }

    channel, case = max(cases.items(), key=lambda kv: kv[1].last_activity_at or "")
    action, reason = decide(case)

    return {
        "channel": channel,
        "case_id": case.case_id,
        "voice_state": derive_voice_state(case),
        "ai_state": _build_ai_state(case, action, reason),
        "escalated": case.escalated,
        "taken_over": case.taken_over,
        "transcript": _safe_transcript(case),
    }


# ── /ws/vad — Silero VAD WebSocket ───────────────────────────────────

@app.websocket("/ws/vad")
async def vad_websocket(websocket: WebSocket):
    """
    WebSocket for real-time Voice Activity Detection.
    Client sends: raw 16kHz 16-bit PCM audio bytes
    Server sends: {"event": "speech_start"} / {"event": "speech_end"} / {"event": "vad_ready"}
    Frontend uses this to stop TTS when user starts speaking (barge-in).
    """
    await websocket.accept()
    try:
        from vad_service import get_vad_model, VADProcessor
        model = get_vad_model()
        if model is None:
            await websocket.send_text(json.dumps({"event": "error", "message": "VAD model unavailable — pip install silero-vad torch"}))
            await websocket.close()
            return
        processor = VADProcessor(model)
        await websocket.send_text(json.dumps({"event": "vad_ready"}))
        while True:
            data = await websocket.receive_bytes()
            for event in processor.process_chunk(data):
                await websocket.send_text(json.dumps(event))
    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_text(json.dumps({"event": "error", "message": str(e)}))
        except Exception:
            pass


# ── /asr — Faster Whisper speech-to-text ─────────────────────────────

@app.post("/asr")
@_rate_limit("20/minute")
async def transcribe(
    request: Request,
    audio: UploadFile = File(...),
    language: Optional[str] = Form(default=None),
):
    """
    Transcribe audio to text using Faster Whisper.
    Supports Hindi, English, Hinglish (auto-detected).

    Form: audio (webm/wav/mp3), language (optional: 'hi', 'en', 'hi-IN')
    Returns: {text, language, confidence, error}
    """
    from asr_service import transcribe_audio

    audio_bytes = await audio.read()
    content_type = audio.content_type or ""
    filename = audio.filename or "audio.webm"

    if "webm" in content_type or filename.endswith(".webm"):
        fmt = "webm"
    elif "wav" in content_type or filename.endswith(".wav"):
        fmt = "wav"
    elif "mp3" in content_type or filename.endswith(".mp3"):
        fmt = "mp3"
    elif "ogg" in content_type or filename.endswith(".ogg"):
        fmt = "ogg"
    else:
        fmt = "webm"

    result = transcribe_audio(audio_bytes, language=language, audio_format=fmt)
    print(f"[PRISM ASR] '{result.get('text','')[:80]}' [{result.get('language')} {result.get('confidence',0):.0%}]")
    return result


@app.get("/asr/status")
async def asr_status():
    """Check if Faster Whisper ASR is loaded and ready."""
    from asr_service import get_whisper_model
    model, error = get_whisper_model()
    return {
        "available": model is not None,
        "model_size": os.getenv("WHISPER_MODEL_SIZE", "medium"),
        "error": error,
    }


# ── /session/reset/{channel} — start fresh ───────────────────────────

@app.post("/session/reset/{channel}")
async def reset_session(channel: str):
    """Clear case state for a channel so the next message starts a fresh conversation."""
    from context import cases, escalated_cases
    if channel in cases:
        old_case_id = cases[channel].case_id
        del cases[channel]
        print(f"[PRISM] 🔄 Session reset for channel: {channel}")
        return {"status": "reset", "channel": channel, "old_case_id": old_case_id}
    return {"status": "no_case", "channel": channel}


@app.post("/session/recover/{channel}")
async def recover_session(channel: str):
    """Reset a channel to safe LISTENING state after an error."""
    from context import cases
    from prism_state import PrismState

    if channel not in cases:
        return {"status": "no_case", "channel": channel}

    case = cases[channel]
    case.failed = False
    case.tool_failed = False
    case.verifying = False
    case.barge_in_active = False
    case.planning = False
    case.connection_state = "CONNECTED"

    logger.info(f"[PRISM] Session recovered for channel: {channel}")
    return {"status": "recovered", "channel": channel, "voice_state": PrismState.LISTENING.value}


# ═══════════════════════════════════════════════════════════════════════════
# PHASE 2: MEMORY ENDPOINTS — consent + management
# ═══════════════════════════════════════════════════════════════════════════

class MemoryConsentRequest(BaseModel):
    consent: bool


@app.post("/memory/consent/{channel}")
async def set_memory_consent(channel: str, req: MemoryConsentRequest):
    """
    Set user consent for long-term memory storage.
    By default consent=False — long-term memory is never stored without explicit opt-in.
    """
    from context import get_or_create_case
    from memory_manager import get_memory_manager

    case = get_or_create_case(channel)
    case.memory_consent = req.consent
    mm = get_memory_manager()

    # If consent was revoked, delete ALL long-term memories for this channel
    if not req.consent:
        deleted = mm.forget_all_long_term(case)
        logger.info(f"[Memory] Consent revoked — deleted {deleted} long-term memories for {channel}")

    logger.info(f"[Memory] Consent set to {req.consent} for channel: {channel}")
    return {
        "channel": channel,
        "consent": req.consent,
        "long_term_keys": mm.list_long_term_keys(case),
    }


@app.get("/memory/{channel}")
async def get_memory_status(channel: str):
    """
    Privacy-safe memory status endpoint.
    Returns only keys (not values) and consent status.
    """
    from context import cases
    from memory_manager import get_memory_manager

    if channel not in cases:
        return {
            "channel": channel,
            "consent": False,
            "short_term_keys": [],
            "long_term_keys": [],
        }

    case = cases[channel]
    mm = get_memory_manager()
    return {
        "channel": channel,
        "consent": case.memory_consent,
        "short_term_keys": list(case.short_term_memory.keys()),
        "long_term_keys": mm.list_long_term_keys(case),
    }


@app.delete("/memory/{channel}")
async def delete_memory(channel: str):
    """
    Delete ALL memory for a channel.
    Clears short-term memory and all persisted long-term memories.
    """
    from context import cases
    from memory_manager import get_memory_manager

    mm = get_memory_manager()
    result = {
        "channel": channel,
        "short_term_cleared": False,
        "long_term_deleted": 0,
    }

    if channel in cases:
        case = cases[channel]
        mm.clear_short_term(case)
        result["short_term_cleared"] = True
        result["long_term_deleted"] = mm.forget_all_long_term(case)

    logger.info(f"[Memory] Full wipe for {channel}: {result}")
    return result


# ═══════════════════════════════════════════════════════════════════════════
# PHASE 2: KNOWLEDGE / SEARCH ENDPOINTS — RAG pipeline
# ═══════════════════════════════════════════════════════════════════════════

@app.get("/knowledge/search")
async def knowledge_search(
    query: str = Query(..., min_length=2, max_length=500),
    top_k: int = Query(default=3, ge=1, le=10),
    user: dict = Depends(require_role(UserRole.AGENT)),
):
    """
    Search the knowledge base. Requires AGENT+ role.

    Returns:
      query: the original query
      results: [{text, source, score}] — sorted by highest score first
      search_latency_ms: time taken
      search_mode: "semantic" (embeddings) or "keyword" (fallback)
    """
    from knowledge_base import get_knowledge_base
    import time as _time

    start = _time.perf_counter()
    kb = get_knowledge_base()
    kb.ensure_loaded()
    results = kb.search(query, top_k=top_k)
    latency_ms = int((_time.perf_counter() - start) * 1000)

    status = kb.status()
    mode = "semantic" if status["embeddings_available"] else "keyword"

    return {
        "query": query,
        "search_mode": mode,
        "search_latency_ms": latency_ms,
        "top_k": len(results),
        "results": [
            {"text": text, "source": source, "score": round(float(score), 4)}
            for text, score, source in results
        ],
    }


@app.get("/knowledge/status")
async def knowledge_status(user: dict = Depends(require_role(UserRole.AGENT))):
    """
    Return the knowledge base status: chunk counts, sources, embedding availability.
    """
    from knowledge_base import get_knowledge_base
    kb = get_knowledge_base()
    kb.ensure_loaded()
    return kb.status()


@app.post("/admin/knowledge/upload")
async def knowledge_upload(
    source_name: str = Form(..., min_length=2, max_length=120),
    reindex: bool = Form(default=False),
    document: UploadFile = File(...),
    user: dict = Depends(require_role(UserRole.ADMIN)),
):
    """
    Admin-only: upload and ingest a document into the knowledge base.
    Supports .txt and .md files; text is extracted, chunked, embedded, and stored.

    - source_name: logical name for the source (e.g. "refund_policy_v2")
    - reindex: if True, remove existing chunks for source_name before ingesting
    - document: the file upload
    """
    from knowledge_base import get_knowledge_base

    kb = get_knowledge_base()
    try:
        raw_bytes = await document.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not read upload: {sanitize_error(e)}")

    # Decode as UTF-8 (tolerant)
    try:
        text = raw_bytes.decode("utf-8", errors="replace")
    except Exception:
        raise HTTPException(status_code=400, detail="File encoding not supported")

    if len(text.strip()) < 50:
        raise HTTPException(status_code=400, detail="Document is too short (min 50 chars)")

    try:
        chunks = kb.ingest_document(source_name, text, reindex=reindex)
    except Exception as e:
        logger.error(f"[Knowledge] Upload failed for {source_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {sanitize_error(e)}")

    status = kb.status()
    logger.info(f"[Knowledge] Admin upload by {user.get('username')}: {source_name} -> {chunks} chunks")
    return {
        "source": source_name,
        "chunks_indexed": chunks,
        "reindexed": reindex,
        "kb_status": status,
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8001))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
