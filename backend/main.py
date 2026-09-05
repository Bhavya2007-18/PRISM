"""
PRISM Backend — FastAPI application
Main entry point with all API endpoints.
"""
import os
import sys
import base64
import json
import re
import time
import uuid
import asyncio

# Make sibling modules importable whether launched as `uvicorn backend.main:app`
# (from the repo root, per render.yaml) or `uvicorn main:app` (from backend/).
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, HTTPException, Request, Query, WebSocket, WebSocketDisconnect, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
import httpx
from dotenv import load_dotenv

load_dotenv(override=True)

app = FastAPI(title="PRISM Backend", version="1.0.0")

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
    return {
        "status": "ok",
        "service": "prism-backend"
    }


@app.get("/chat/test")
async def chat_test():
    """Debug endpoint — tests LLM connectivity and returns basic connectivity status."""
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
async def get_token(channel: str = Query(...), uid: int = Query(...)):
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
            "error": str(e)
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
    case.agora_channel = req.channel
    case.voice_mode = "agora_rtc"
    if req.locale:
        case.locale = req.locale
    if req.language and req.language not in case.language:
        case.language.append(req.language)

    if not app_id or not customer_id or not customer_secret:
        mock_id = f"demo-agent-{uuid.uuid4().hex[:8]}"
        active_sessions[req.channel] = mock_id
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
            "idle_timeout": 60,
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
    return {"agent_id": agent_id, "state": data.get("state", "RUNNING"), "channel": req.channel}


# ── /session/stop ─────────────────────────────────────────────────────

@app.post("/session/stop")
async def stop_session(req: SessionStopRequest):
    """Stop the Agora Conversational AI agent."""
    app_id = os.getenv("AGORA_APP_ID", "")
    customer_id = os.getenv("AGORA_CUSTOMER_ID", "")
    customer_secret = os.getenv("AGORA_CUSTOMER_SECRET", "")

    active_sessions.pop(req.channel, None)

    if not app_id or req.agent_id.startswith("demo-"):
        return {"status": "stopped", "mode": "demo"}

    auth = base64.b64encode(f"{customer_id}:{customer_secret}".encode()).decode()

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(
            f"https://api.agora.io/api/conversational-ai/v2/projects/{app_id}/agents/{req.agent_id}/stop",
            headers={"Authorization": f"Basic {auth}"},
        )

    return {"status": "stopped", "agora_status": resp.status_code}


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
        "confidence_fields": {k: v.value for k, v in report.fields.items()},
        "action": action_label,
        "verified": list(case.verified),
        "unverified": list(case.unverified),
        "tool": tool_executed,
        "tool_status": tool_status,
        "tool_result": safe_tool_result,
        "blocking_fields": report.blocking_fields,
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
    """Return content as an SSE streaming response (Agora expects this format)."""
    resp_id = (original or {}).get("id", f"chatcmpl-{uuid.uuid4().hex[:8]}")
    created = (original or {}).get("created", int(time.time()))

    delta_chunk = json.dumps({
        "id": resp_id,
        "object": "chat.completion.chunk",
        "created": created,
        "model": model,
        "choices": [{
            "index": 0,
            "delta": {"role": "assistant", "content": content},
            "finish_reason": None,
        }]
    })

    done_chunk = json.dumps({
        "id": resp_id,
        "object": "chat.completion.chunk",
        "created": created,
        "model": model,
        "choices": [{
            "index": 0,
            "delta": {},
            "finish_reason": "stop",
        }]
    })

    async def event_stream():
        yield f"data: {delta_chunk}\n\n"
        yield f"data: {done_chunk}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


# ── /chat (text mode) ─────────────────────────────────────────────────

@app.post("/chat")
async def chat(req: ChatRequest):
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

    print(f"[PRISM] ✅ Human agent took over case {case_id}")
    return {"status": "taken_over", "case_id": case_id}


# ── /debug/case (dev only) ────────────────────────────────────────────

@app.get("/debug/case/{channel}")
async def debug_case(channel: str):
    """Return current case state for a channel (dev/demo use)."""
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
            "fields": {k: v.value for k, v in report.fields.items()},
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
async def transcribe(
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


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8001))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
