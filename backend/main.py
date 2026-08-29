"""
PRISM Backend — FastAPI application
Main entry point with all API endpoints.
"""
import os
import base64
import json
import re
import time
import uuid
import asyncio

from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
import httpx
from dotenv import load_dotenv

load_dotenv(override=True)

app = FastAPI(title="PRISM Backend", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Module-level state ────────────────────────────────────────────────
# Active Agora agent sessions: channel -> agent_id
active_sessions: dict[str, str] = {}


# ── Pydantic models ───────────────────────────────────────────────────

class SessionStartRequest(BaseModel):
    channel: str
    user_uid: int

class SessionStopRequest(BaseModel):
    agent_id: str
    channel: str

class ChatRequest(BaseModel):
    message: str
    channel: str = "prism-text"


# ── /health ───────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "service": "PRISM Backend", "version": "1.0.0"}


@app.get("/chat/test")
async def chat_test():
    """Debug endpoint — tests LLM connectivity and returns the raw result or error."""
    import traceback
    llm_base_url = os.getenv("LLM_BASE_URL", "")
    llm_api_key = os.getenv("LLM_API_KEY", "")
    llm_model = os.getenv("LLM_MODEL", "")
    
    result = {
        "llm_base_url": llm_base_url,
        "llm_model": llm_model,
        "api_key_set": bool(llm_api_key),
        "api_key_prefix": llm_api_key[:8] if llm_api_key else "EMPTY",
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
        result["response_preview"] = resp.text[:300]
        if resp.status_code == 200:
            result["success"] = True
            result["content"] = resp.json()["choices"][0]["message"].get("content")
        else:
            result["success"] = False
    except Exception as e:
        result["success"] = False
        result["exception"] = str(e)
        result["traceback"] = traceback.format_exc()
    
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
    backend_url = os.getenv("BACKEND_PUBLIC_URL", "http://localhost:8000")
    llm_key = os.getenv("LLM_API_KEY", "")
    llm_model = os.getenv("LLM_MODEL", "gpt-4o-mini")
    # Ensure case state exists for this channel
    from context import get_or_create_case
    get_or_create_case(req.channel)

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

    from agent import PRISM_SYSTEM_PROMPT
    from tools import ALL_TOOLS

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
                "system_messages": [{"role": "system", "content": PRISM_SYSTEM_PROMPT}],
                "tools": ALL_TOOLS,
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
    The heart of PRISM.

    Receives OpenAI-format chat completion requests from Agora.
    Steps:
    1. Get or create case state for this channel
    2. Run decision engine (pure Python, no LLM)
    3. Inject PRISM system prompt + case context + directive into messages
    4. Forward to real LLM
    5. If tool_calls in response: execute tool, update case state, re-call LLM
    6. Strip <EXTRACT> blocks and parse them to update case state
    7. If decision engine says ESCALATE: trigger escalation
    8. Return streaming SSE response to Agora
    """
    from agent import PRISM_SYSTEM_PROMPT, build_case_context_message
    from context import get_or_create_case, update_case_from_extract, escalated_cases
    from decision import decide, Action
    from tools import check_transaction, create_escalation_ticket, ALL_TOOLS

    llm_base_url = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
    llm_api_key = os.getenv("LLM_API_KEY", "")
    llm_model = os.getenv("LLM_MODEL", "gpt-4o-mini")

    try:
        body = await request.json()
    except Exception:
        body = {}

    messages: list = body.get("messages", [])
    model: str = body.get("model", llm_model)

    # ── 1. Case state ─────────────────────────────────────────────────
    case = get_or_create_case(channel)

    # ── 2. Decision engine ────────────────────────────────────────────
    action, reason = decide(case)

    # ── 3. Build augmented message list ──────────────────────────────
    # Separate existing system messages from the rest
    existing_system = [m for m in messages if m.get("role") == "system"]
    non_system = [m for m in messages if m.get("role") != "system"]

    # Build system message block
    system_block = []

    # 3a. PRISM base prompt (add if not already present)
    if not any(PRISM_SYSTEM_PROMPT[:100] in m.get("content", "") for m in existing_system):
        system_block.append({"role": "system", "content": PRISM_SYSTEM_PROMPT})

    system_block.extend(existing_system)

    # 3b. Case context injection
    case_context_content = build_case_context_message(
        case.to_prompt_summary(), action.value, reason
    )
    system_block.append({"role": "system", "content": case_context_content})

    # 3c. Escalation directive (if ESCALATE and not yet escalated)
    if action == Action.ESCALATE and not case.escalated:
        system_block.append({
            "role": "system",
            "content": (
                "URGENT DIRECTIVE: You must escalate this case now. "
                f"Reason: {reason}. "
                "Tell the user warmly but clearly: you've found the transaction details, "
                "but you cannot confidently determine whether a duplicate charge occurred. "
                "Say you're connecting them with a specialist who can investigate properly. "
                "Do NOT guess or make up an answer. Keep it under 3 sentences. Be honest and warm."
            )
        })

    final_messages = system_block + non_system

    # ── 4. Call LLM (non-streaming so we can intercept tool calls) ────
    llm_headers = {
        "Authorization": f"Bearer {llm_api_key}",
        "Content-Type": "application/json",
    }

    llm_payload = {
        **{k: v for k, v in body.items() if k not in ("messages", "stream", "tools")},
        "model": model,
        "messages": final_messages,
        "tools": ALL_TOOLS,
        "tool_choice": "auto",
        "stream": False,
        "max_tokens": body.get("max_tokens", 200),
    }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{llm_base_url}/chat/completions",
                headers=llm_headers,
                json=llm_payload,
            )
        if resp.status_code != 200:
            raise ValueError(f"LLM error {resp.status_code}: {resp.text[:200]}")
        llm_data = resp.json()
    except Exception as e:
        print(f"[PRISM] LLM call failed: {e}")
        fallback_msg = "Main abhi aapki madad karne mein kuch takleef ho rahi hai. Please thodi der baad dobara try karein."
        return _streaming_response(model, fallback_msg)

    choice = llm_data.get("choices", [{}])[0]
    message = choice.get("message", {})

    # ── 5. Tool call interception ─────────────────────────────────────
    if message.get("tool_calls"):
        tool_call = message["tool_calls"][0]
        fn_name = tool_call["function"]["name"]
        try:
            fn_args = json.loads(tool_call["function"]["arguments"])
        except json.JSONDecodeError:
            fn_args = {}

        print(f"[PRISM] Tool call: {fn_name}({fn_args})")

        tool_result = {}
        if fn_name == "check_transaction":
            tx_id = fn_args.get("transaction_id", "")
            tool_result = check_transaction(tx_id)
            print(f"[PRISM] Tool result: {tool_result}")

            if tool_result.get("success"):
                # Update case state with verified tool data
                case.payment_status = tool_result["status"]
                case.order_status = tool_result["order_status"]
                case.amount = float(tool_result["amount"])
                for field in ["payment_status", "order_status", "amount", "transaction_id"]:
                    if field not in case.verified:
                        case.verified.append(field)
                case.unverified = [f for f in case.unverified if f not in case.verified]
            else:
                case.tool_failed = True

        # Re-evaluate after tool execution
        action_after, reason_after = decide(case)
        print(f"[PRISM] Decision after tool: {action_after} — {reason_after}")

        # Build follow-up messages with tool result
        follow_up_messages = final_messages + [
            {"role": "assistant", "tool_calls": message["tool_calls"], "content": None},
            {
                "role": "tool",
                "tool_call_id": tool_call["id"],
                "content": json.dumps(tool_result),
            }
        ]

        # Add post-tool directive
        if action_after == Action.ESCALATE and not case.escalated:
            follow_up_messages.append({
                "role": "system",
                "content": (
                    "DIRECTIVE: Based on the transaction data you just retrieved, you must now escalate. "
                    f"Reason: {reason_after}. "
                    "Tell the user specifically: you can see the ₹1,499 payment was successful, "
                    "but the order was not confirmed, and you cannot determine if there was a duplicate charge. "
                    "Say you're connecting them with a specialist. "
                    "Do not invent information. Be warm, honest, and brief (2-3 sentences max)."
                )
            })

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                follow_resp = await client.post(
                    f"{llm_base_url}/chat/completions",
                    headers=llm_headers,
                    json={
                        **{k: v for k, v in body.items() if k not in ("messages", "stream", "tools")},
                        "model": model,
                        "messages": follow_up_messages,
                        "stream": False,
                        "max_tokens": body.get("max_tokens", 200),
                    },
                )
            follow_data = follow_resp.json()
            raw_content = follow_data["choices"][0]["message"].get("content") or ""
        except Exception as e:
            print(f"[PRISM] Follow-up LLM call failed: {e}")
            raw_content = (
                f"Maine aapka ₹{int(case.amount or 0)} ka transaction dekha — "
                "payment successful hai lekin order confirm nahi hua. "
                "Duplicate charge ke baare mein main confident nahi hoon, "
                "isliye main aapko ek specialist se connect kar raha hoon."
            )

        clean_content, extracted = _extract_and_strip(raw_content)
        if extracted:
            update_case_from_extract(channel, extracted)

        if action_after == Action.ESCALATE and not case.escalated:
            _trigger_escalation(case, reason_after)

        return _streaming_response(model, clean_content, llm_data)

    # ── 6. Normal response (no tool call) ────────────────────────────
    raw_content = message.get("content") or ""
    clean_content, extracted = _extract_and_strip(raw_content)

    if extracted:
        update_case_from_extract(channel, extracted)

    # Re-evaluate after extract update
    action_final, reason_final = decide(case)
    print(f"[PRISM] Decision: {action_final} — {reason_final} | Case: {case.to_prompt_summary()}")

    if action_final == Action.ESCALATE and not case.escalated:
        _trigger_escalation(case, reason_final)

    return _streaming_response(model, clean_content, llm_data)


# ── Helper functions ──────────────────────────────────────────────────

def _extract_and_strip(content: str) -> tuple[str, dict | None]:
    """Remove <EXTRACT>...</EXTRACT> from LLM response and parse the JSON."""
    pattern = r'<EXTRACT>(.*?)</EXTRACT>'
    match = re.search(pattern, content, re.DOTALL)
    extracted = None
    if match:
        try:
            extracted = json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            pass
        content = re.sub(pattern, '', content, flags=re.DOTALL).strip()
    return content, extracted


def _trigger_escalation(case, reason: str) -> None:
    """Mark case as escalated, create ticket, store in escalated_cases."""
    from tools import create_escalation_ticket
    from context import escalated_cases

    case.escalated = True
    case.escalation_reason = reason

    summary = create_escalation_ticket(case, reason)
    case.escalation_summary = summary
    escalated_cases[case.case_id] = summary

    print(f"[PRISM] 🔴 ESCALATED — {case.case_id} | Reason: {reason}")


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
    Text-mode chat endpoint.
    Runs the same PRISM logic as /llm-proxy but accepts plain text
    and returns a plain text response. No Agora required.
    """
    from agent import PRISM_SYSTEM_PROMPT, build_case_context_message
    from context import get_or_create_case, update_case_from_extract, escalated_cases
    from decision import decide, Action
    from tools import check_transaction, ALL_TOOLS

    llm_base_url = os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1")
    llm_api_key = os.getenv("LLM_API_KEY", "")
    llm_model = os.getenv("LLM_MODEL", "openai/gpt-oss-20b")

    channel = req.channel
    case = get_or_create_case(channel)

    # Append user message to conversation history
    case.conversation_history.append({"role": "user", "content": req.message})

    # Decision engine
    action, reason = decide(case)

    # Build messages
    system_block = [
        {"role": "system", "content": PRISM_SYSTEM_PROMPT},
        {"role": "system", "content": build_case_context_message(
            case.to_prompt_summary(), action.value, reason
        )},
    ]

    if action == Action.ESCALATE and not case.escalated:
        system_block.append({
            "role": "system",
            "content": (
                "URGENT DIRECTIVE: Escalate this case now. "
                f"Reason: {reason}. "
                "Tell the user warmly that you cannot confidently resolve this "
                "and are connecting them with a specialist. Under 3 sentences."
            )
        })

    final_messages = system_block + case.conversation_history

    llm_headers = {
        "Authorization": f"Bearer {llm_api_key}",
        "Content-Type": "application/json",
    }

    llm_payload = {
        "model": llm_model,
        "messages": final_messages,
        "tools": ALL_TOOLS,
        "tool_choice": "auto",
        "stream": False,
        "max_tokens": 250,
        "temperature": 0.7,
    }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{llm_base_url}/chat/completions",
                headers=llm_headers,
                json=llm_payload,
            )
        if resp.status_code != 200:
            raise ValueError(f"LLM error {resp.status_code}: {resp.text[:200]}")
        llm_data = resp.json()
    except Exception as e:
        import traceback
        err_detail = traceback.format_exc()
        print(f"[PRISM/chat] LLM error: {e}\n{err_detail}")
        return {"reply": f"LLM Error: {str(e)}", "escalated": False, "debug_error": str(e)}

    choice = llm_data.get("choices", [{}])[0]
    message = choice.get("message", {})

    # ── Tool call interception ────────────────────────────────────────
    if message.get("tool_calls"):
        tool_call = message["tool_calls"][0]
        fn_name = tool_call["function"]["name"]
        try:
            fn_args = json.loads(tool_call["function"]["arguments"])
        except json.JSONDecodeError:
            fn_args = {}

        print(f"[PRISM/chat] Tool call: {fn_name}({fn_args})")

        tool_result = {}
        if fn_name == "check_transaction":
            tx_id = fn_args.get("transaction_id", "")
            tool_result = check_transaction(tx_id)
            print(f"[PRISM/chat] Tool result: {tool_result}")

            if tool_result.get("success"):
                case.payment_status = tool_result["status"]
                case.order_status = tool_result["order_status"]
                case.amount = float(tool_result["amount"])
                for field in ["payment_status", "order_status", "amount", "transaction_id"]:
                    if field not in case.verified:
                        case.verified.append(field)
                case.unverified = [f for f in case.unverified if f not in case.verified]
            else:
                case.tool_failed = True

        action_after, reason_after = decide(case)

        follow_messages = final_messages + [
            {"role": "assistant", "tool_calls": message["tool_calls"], "content": None},
            {"role": "tool", "tool_call_id": tool_call["id"], "content": json.dumps(tool_result)},
        ]

        if action_after == Action.ESCALATE and not case.escalated:
            follow_messages.append({
                "role": "system",
                "content": (
                    "DIRECTIVE: Escalate now. "
                    f"Reason: {reason_after}. "
                    "Tell the user what you found (transaction details), "
                    "then say you cannot determine the duplicate charge status "
                    "and are connecting them with a specialist. Be warm and brief."
                )
            })

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                follow_resp = await client.post(
                    f"{llm_base_url}/chat/completions",
                    headers=llm_headers,
                    json={
                        "model": llm_model,
                        "messages": follow_messages,
                        "stream": False,
                        "max_tokens": 250,
                    },
                )
            follow_data = follow_resp.json()
            raw_content = follow_data["choices"][0]["message"].get("content") or ""
        except Exception as e:
            print(f"[PRISM/chat] Follow-up LLM error: {e}")
            raw_content = f"Maine aapka ₹{int(case.amount or 0)} ka transaction check kiya. Aapko ek specialist se connect kar raha hoon."

        clean_content, extracted = _extract_and_strip(raw_content)
        if extracted:
            update_case_from_extract(channel, extracted)
        if action_after == Action.ESCALATE and not case.escalated:
            _trigger_escalation(case, reason_after)

        case.conversation_history.append({"role": "assistant", "content": clean_content})
        return {
            "reply": clean_content,
            "escalated": case.escalated,
            "case_id": case.case_id if case.escalated else None,
            "action": action_after.value,
        }

    # ── Normal response ───────────────────────────────────────────────
    raw_content = message.get("content") or ""
    clean_content, extracted = _extract_and_strip(raw_content)

    if extracted:
        update_case_from_extract(channel, extracted)

    action_final, reason_final = decide(case)
    print(f"[PRISM/chat] Decision: {action_final} | {case.to_prompt_summary()}")

    if action_final == Action.ESCALATE and not case.escalated:
        _trigger_escalation(case, reason_final)

    case.conversation_history.append({"role": "assistant", "content": clean_content})

    return {
        "reply": clean_content,
        "escalated": case.escalated,
        "case_id": case.case_id if case.escalated else None,
        "action": action_final.value,
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
            "verified": case.verified,
            "unverified": case.unverified,
            "escalated": case.escalated,
            "escalation_reason": case.escalation_reason,
        },
        "confidence": {
            "fields": {k: v.value for k, v in report.fields.items()},
            "display_score": report.display_score,
            "label": report.overall_label,
        },
        "next_action": action.value,
        "next_reason": reason,
    }
