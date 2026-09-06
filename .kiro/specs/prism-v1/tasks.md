# Implementation Plan: PRISM v1 Final

## Tasks

- [x] 1. Clean agent architecture
  - Remove misleading naming (no Pipecat references in comments or docs)
  - Establish canonical 7-engine module structure in code comments: VoiceEngine, IntelligenceEngine, ActionEngine, PolicyEngine, HumanSupportEngine, PlatformEngine, CoreOrchestrator
  - Document each engine boundary inside the relevant Python files
  - Add engine header comments to voice_agent.py, policy.py, decision.py, confidence.py, tools.py
  - _Requirements: Phase 0.1, Phase 1.7_

- [x] 2. Canonical PrismState
  - Extend prism_state.py with all 14 states: IDLE, CONNECTING, LISTENING, UNDERSTANDING, THINKING, PLANNING, ACTING, VERIFYING, SPEAKING, ESCALATING, HUMAN_CONNECTED, RESOLVED, FAILED, ENDED
  - Update derive_voice_state() to handle PLANNING, VERIFYING, RESOLVED, FAILED, ENDED
  - Update frontend/src/config/prismState.js to mirror all 14 states with labels and icons
  - Add voice-orb CSS classes for new states in index.css
  - _Requirements: Phase 0.2_

- [x] 3. Agora session lifecycle
  - Add reconnection handling in /session/start with retry logic
  - Add connection_state field to CaseState tracking CONNECTING/CONNECTED/RECONNECTING/DISCONNECTED
  - Add AGORA_IDLE_TIMEOUT env var defaulting to 60
  - Add graceful session cleanup on disconnect
  - Add /session/status/{channel} endpoint returning current connection state
  - _Requirements: Phase 1.1_

- [x] 4. Realtime audio pipeline
  - Create backend/audio_pipeline.py as single entry point for audio processing
  - Wire: AudioCapture to VAD to TurnDetection to STT to TranscriptEvent
  - Add AudioPipelineConfig dataclass: sample_rate, chunk_size, silence_threshold_ms, min_speech_ms, max_utterance_ms
  - Add pipeline health check to /health endpoint
  - _Requirements: Phase 1.2_

- [x] 5. VAD and turn detection
  - Enhance vad_service.py VADProcessor with configurable silence_duration_ms=480, min_speech_duration_ms=150, max_utterance_duration_ms=15000
  - Add turn_complete event when max_utterance exceeded
  - Add noise_floor calibration on session start
  - Add barge_in_detected event type
  - Ensure reset() is called on new session start
  - _Requirements: Phase 1.2_

- [x] 6. Real Agora transcript events
  - Update /llm-proxy to extract final user transcript from Agora payload and persist to case.conversation_history immediately
  - Add /transcript/{channel} SSE endpoint streaming new transcript lines as they arrive
  - Add partial_transcript field to CaseState
  - Include transcript field with incremental index in /state/{channel} response
  - _Requirements: Phase 1.3_

- [x] 7. Partial transcript UI
  - Update TranscriptConsole.jsx to connect to /transcript/{channel} SSE when in voice mode
  - Show partial text with blinking cursor as it arrives
  - Animate final line entry with blur-to-sharp transition
  - Fall back to polling /state/{channel} if SSE unavailable
  - _Requirements: Phase 1.3_

- [x] 8. Final transcript pipeline
  - Add transcript_complete event to CaseState with full turn text
  - Ensure conversation_history updated atomically after each complete turn
  - Add transcript_index counter to CaseState for incremental frontend sync
  - Persist timestamps on each transcript entry: role, content, timestamp
  - _Requirements: Phase 1.3_

- [x] 9. Conversation context engine
  - Create backend/context_engine.py with ContextManager class
  - ContextManager assembles: SystemPrompt + ConversationWindow last 12 turns + CaseContext + ToolResults + PolicyState
  - Replace inline context assembly in voice_agent.py with ContextManager.build_context()
  - Add sliding window: keep last 12 turns only, never send full unbounded history to LLM
  - Add context_tokens_estimate() method
  - _Requirements: Phase 1.5, Phase 3.3_

- [x] 10. Intent extraction
  - Create backend/intent_engine.py with IntentEngine class
  - Move _pre_extract() regex logic from voice_agent.py into IntentEngine
  - Add intent_confidence score 0.0-1.0 separate from overall confidence
  - Support intents: payment_issue, refund_request, delivery_issue, order_status, account_issue, general_inquiry
  - Add detect_language() returning primary language and confidence
  - _Requirements: Phase 1.4, Phase 1.5_

- [x] 11. Missing information engine
  - Create backend/missing_info.py with MissingInfoEngine class
  - Move missing-info detection from decision.py into MissingInfoEngine.get_missing_fields(case)
  - Return list of: field_name, priority, question_template in English and Hindi
  - Add smart question selection: ask highest-priority missing field first
  - Integrate with voice_agent.py ASK path
  - _Requirements: Phase 1.5_

- [x] 12. LLM planning
  - Add Plan dataclass to backend/planning.py: goal, steps, current_step, status
  - Add Planner class generating a plan from intent and case_state
  - Example plan: resolve_payment_issue has steps [identify_transaction, check_transaction, verify_result, determine_resolution]
  - Store current plan on CaseState.current_plan
  - Expose plan steps via _build_ai_state() as safe plan_summary (high-level only)
  - Add PLANNING state to derive_voice_state() when plan is being built
  - _Requirements: Phase 1.8_

- [x] 13. Tool registry
  - Create backend/tool_registry.py with ToolRegistry class
  - Register tools with: name, description, input_schema, output_schema, timeout_ms, requires_verification, audit_log flag
  - Migrate check_transaction and escalate_to_human to registry
  - Add get_tool(name) and list_tools() methods
  - Replace hardcoded get_tool_schemas() in voice_agent.py with registry.get_schemas()
  - _Requirements: Phase 1.9_

- [x] 14. Tool schema validation
  - Add input validation to ToolRegistry before execution validating args against JSON schema
  - Add output validation verifying tool result matches expected schema
  - Add ToolValidationError exception type
  - Log validation failures to audit trail
  - Return structured error to LLM on validation failure
  - _Requirements: Phase 1.10_

- [x] 15. Policy deterministic gate
  - Enhance policy.py PolicyDecision with approved_actions, denied_actions, modification_reason fields
  - Add policy rule: confidence below 60 AND tool not yet run forces TOOL_CALL not ESCALATE
  - Add policy rule: user_requested_human ALWAYS ESCALATES regardless of confidence
  - Add policy audit log entry on every gate evaluation
  - Add get_policy_summary() for safe frontend exposure
  - _Requirements: Phase 0.3, Phase 1.10_

- [x] 16. Transaction tool
  - Add get_order() tool to tools.py alongside check_transaction()
  - Add refund_status() tool stub
  - Add verify_identity() tool stub
  - Expand MOCK_TRANSACTIONS to 10 entries covering: SUCCESS+CONFIRMED, SUCCESS+NOT_CONFIRMED, FAILED, PENDING, DUPLICATE scenarios
  - Register all tools in ToolRegistry
  - _Requirements: Phase 1.9, Phase 4.2_

- [x] 17. Verification engine
  - Create backend/verification.py with VerificationEngine class
  - Add verify_tool_result(tool_name, result, case) method
  - Verification checks: result has required fields, amounts match without silent None to 0.0, status is valid enum value
  - Update CaseState to track verification_status per tool call
  - Add VERIFYING state to derive_voice_state() after tool completes before response
  - _Requirements: Phase 1.12_

- [x] 18. Numeric confidence
  - Replace FieldConfidence three-bucket system with per-field float scores 0.0-1.0
  - intent_confidence from IntentEngine
  - transaction_confidence from tool verification result
  - resolution_confidence composite of all verified fields
  - overall_confidence weighted average: intent 20%, transaction 40%, resolution 40%
  - Keep display_score as int(overall times 100)
  - Define thresholds: RESOLVE_THRESHOLD=0.85, CONTINUE_THRESHOLD=0.60, ESCALATE_BELOW=0.60
  - _Requirements: Phase 1.11_

- [x] 19. Response generation
  - Create backend/response_generator.py with ResponseGenerator class
  - Add generate_response(reply_text, case, policy) with post-processing: trim, language check, length limit
  - Add sentence_segment(text) for TTS streaming preparation
  - Add language_match_check(response, case.language) warning if response language differs from user
  - Add SPEAKING state update before response is sent
  - _Requirements: Phase 1.13_

- [x] 20. Streaming TTS
  - Update /llm-proxy SSE response to support sentence-level streaming chunks
  - Add sentence segmentation before streaming: split response at . ! ? boundaries
  - Stream each sentence as separate SSE chunk for lower perceived latency
  - Add Content-Type validation so Agora receives correct streaming format
  - Document TTS vendor config in .env.example
  - _Requirements: Phase 1.13_

- [x] 21. Barge-in
  - Add barge_in_active field to CaseState
  - When VAD fires speech_start during SPEAKING state: set barge_in_active=True, emit barge_in event on /state/{channel}
  - Frontend: on barge_in event, update PrismCore to LISTENING state immediately
  - Add cancel_tts event type to /transcript SSE stream
  - Document that Agora Conversational AI handles audio-level interruption natively
  - _Requirements: Phase 1.6_

- [x] 22. Interruption handling
  - Add interrupted field to CaseState
  - On interruption: truncate current plan to current_step, reset speaking state, transition to LISTENING
  - Add interruption_count to CaseState for analytics
  - Handle mid-stream interruption in _streaming_response with early termination marker
  - _Requirements: Phase 1.6_

- [x] 23. Voice error recovery
  - Add ErrorRecoveryEngine class to backend/error_recovery.py
  - Implement recovery paths: STT_FAILURE asks repeat, LLM_FAILURE uses fallback_response, TOOL_FAILURE retries once then escalates, TTS_FAILURE uses text_fallback, AGORA_FAILURE reconnects
  - Update voice_agent.run_agent_turn() to use ErrorRecoveryEngine on each exception
  - Add FAILED state handling in derive_voice_state()
  - Add /session/recover/{channel} endpoint to reset to safe LISTENING state
  - _Requirements: Phase 1.14_

- [x] 24. End-to-end voice test
  - Create backend/test_e2e_voice.py
  - Test full pipeline: mock audio to VAD to STT to context to LLM to policy to tool to verify to response
  - Test interruption path: speaking to barge-in to listening
  - Test escalation path: low confidence to policy to ESCALATE to case created
  - Test recovery path: tool failure to retry to escalate
  - All tests use mocked Agora requiring no real credentials
  - _Requirements: Phase 1.15_

- [x] 25. Authentication
  - Add JWT-based authentication middleware to main.py using python-jose
  - Add POST /auth/token endpoint returning JWT from username and password
  - Add GET /auth/me endpoint
  - Gate /debug/case and /chat/test behind ENABLE_DEBUG_ENDPOINTS=true env flag immediately
  - Add auth dependency to protected endpoints: /cases, /cases/{id}/takeover, /active-state
  - _Requirements: Phase 2.1_

- [x] 26. Authorization RBAC
  - Define roles: USER, AGENT, SUPERVISOR, ADMIN, OWNER
  - Add role field to JWT claims
  - Add require_role(role) dependency for endpoints
  - AGENT role required for /cases and /cases/{id}/takeover
  - ADMIN role required for /debug/case, /chat/test, /session/reset
  - _Requirements: Phase 2.2_

- [x] 27. API security
  - Add request body size limit: 10MB max for /asr, 100KB for /chat
  - Add X-Request-ID header generation and logging
  - Add channel parameter validation regex as reusable dependency
  - Add /llm-proxy shared-secret validation via X-Agora-Signature header check
  - _Requirements: Phase 2.3_

- [x] 28. Rate limiting
  - Install slowapi and configure in main.py
  - Add rate limit decorators: /chat 30/min, /asr 20/min, /llm-proxy 60/min, /token 10/min per IP
  - Add rate limit error handler returning 429 with Retry-After header
  - _Requirements: Phase 2.3_

- [x] 29. Secret management
  - Remove str(e) from all token error responses, replace with sanitize_error(e) helper
  - Update .env.example with all required vars documented
  - Add startup validation logging WARNING if AGORA_APP_ID or LLM_API_KEY not set
  - Add startup banner logging all configured services and their status
  - _Requirements: Phase 2.4_

- [x] 30. Database
  - Add SQLite via SQLModel for persistence
  - Create tables: cases, sessions, messages, escalations, tool_executions
  - Migrate in-memory cases dict to database-backed CaseRepository
  - Migrate escalated_cases dict to database
  - Add database health check to /health endpoint so session state survives restart
  - _Requirements: Phase 2.6_

- [ ] 31. Redis
  - Add Redis connection via redis-py with graceful fallback if not configured
  - Use Redis for: rate limit counters, session lock, short-term context cache
  - Add REDIS_URL env var defaulting to None meaning Redis disabled
  - Add redis health check to /health endpoint
  - _Requirements: Phase 2.7_

- [ ] 32. Audit logging
  - Create backend/audit_log.py with AuditLogger class
  - Log events: session_start, session_end, tool_executed, policy_decision, escalation_created, takeover, auth_success, auth_failure
  - Each entry: timestamp, event_type, channel, case_id, user_role, details, outcome
  - Persist audit logs to database audit_logs table
  - Expose GET /audit/logs (ADMIN only) with pagination
  - _Requirements: Phase 2.8_

- [ ] 33. Error monitoring
  - Add structured error logging format: [PRISM][module][level] message
  - Add error_id (uuid) to every caught exception
  - Add /errors/recent endpoint (ADMIN only) returning last 50 errors
  - Add Sentry integration optional via SENTRY_DSN env var
  - _Requirements: Phase 2.8_

- [ ] 34. Metrics
  - Create backend/metrics.py with MetricsCollector class
  - Track: sessions_started, sessions_ended, tool_calls_total, tool_calls_failed, escalations_total, avg_response_latency_ms, avg_confidence_score
  - Add GET /metrics endpoint (ADMIN only)
  - Track per-session latency: STT_latency, LLM_latency, tool_latency, TTS_latency
  - _Requirements: Phase 2.8_

- [ ] 35. Tracing
  - Add request tracing with X-Trace-ID propagated through all internal calls
  - Log trace_id on every log line within a request context
  - Add trace_id to all API response headers
  - Add timing spans: voice_agent_turn_ms, tool_execution_ms, policy_evaluation_ms
  - _Requirements: Phase 2.8_

- [ ] 36. Staging environment
  - Add staging service to render.yaml with name prism-backend-staging
  - Add ENVIRONMENT env var: development, staging, production
  - Gate debug endpoints on ENVIRONMENT not equal to production
  - _Requirements: Phase 2.9_

- [ ] 37. Production environment
  - Update render.yaml startCommand with --workers 2 --timeout-keep-alive 75
  - Add healthCheckPath /health to render.yaml
  - Add production startup validation aborting if required env vars missing
  - Add Whisper warmup call on startup via FastAPI lifespan event
  - _Requirements: Phase 2.9_

- [ ] 38. Docker
  - Create backend/Dockerfile with multi-stage build
  - Create frontend/Dockerfile
  - Fix docker-compose.yml: correct ports, env vars, health checks, volume mounts
  - Add .dockerignore files for both services
  - _Requirements: Phase 2.10_

- [ ] 39. Render hardening
  - Add graceful shutdown handler for SIGTERM to main.py
  - Add GET /ready endpoint returning 503 until Whisper model loads
  - Update /health to return degraded status when optional services unavailable
  - _Requirements: Phase 2.10_

- [ ] 40. Vercel hardening
  - Add vercel.json rewrites for React Router (all paths to index.html)
  - Add security headers in vercel.json: X-Content-Type-Options, X-Frame-Options, Referrer-Policy
  - Add VITE_API_URL validation on frontend startup
  - _Requirements: Phase 2.10_

- [ ] 41. Health and readiness
  - Extend /health to return: status, version, uptime_seconds, services object with db, redis, whisper, agora, llm each having status and latency_ms
  - Add /ready endpoint returning 200 only when all critical services initialized
  - Add /version endpoint returning build info
  - _Requirements: Phase 2.10_

- [ ] 42. Backup and recovery
  - Add database backup script at backend/scripts/backup_db.py exporting to JSON
  - Add /admin/export endpoint (ADMIN only) for on-demand export
  - Add database migration versioning with Alembic
  - _Requirements: Phase 2.10_

- [x] 43. Short-term memory
  - Add short_term_memory dict to CaseState
  - Add MemoryManager class with remember(case, key, value, source) and recall(case, key) methods
  - ContextManager uses short_term_memory when building LLM context
  - Memory cleared on session end
  - _Requirements: Phase 3.1_

- [x] 44. Long-term memory
  - Create backend/memory_store.py with LongTermMemory class
  - Store in database: channel, key, value, created_at, expires_at
  - Add remember_long_term(), recall_long_term(), forget(), forget_all() methods
  - _Requirements: Phase 3.2_

- [x] 45. Memory retrieval
  - Add MemoryManager.get_relevant_context(case, query) searching both short and long-term
  - Returns top-3 relevant memories ranked by recency
  - Integrate into ContextManager.build_context()
  - _Requirements: Phase 3.2_

- [x] 46. Memory permissions
  - Add memory_consent field to CaseState defaulting to False
  - Only store long-term memory when consent is True
  - Add POST /memory/consent/{channel} endpoint
  - Add GET /memory/{channel} endpoint returning keys only for privacy
  - Add DELETE /memory/{channel} endpoint
  - _Requirements: Phase 3.2_

- [x] 47. Knowledge base
  - Create backend/knowledge_base.py with KnowledgeBase class
  - Add load_documents(path) loading text files from backend/knowledge/
  - Create backend/knowledge/ directory with faq.txt, refund_policy.txt, payment_policy.txt
  - Add search(query, top_k=3) returning relevant passages
  - _Requirements: Phase 3.4_

- [x] 48. Document ingestion
  - Add document chunking: split docs into 500 token chunks with 50 token overlap
  - Add metadata to each chunk: source, chunk_index, created_at
  - Store chunks in database documents table
  - Add POST /admin/knowledge/upload endpoint (ADMIN only)
  - _Requirements: Phase 3.5_

- [x] 49. Embeddings
  - Add embedding generation using sentence-transformers paraphrase-multilingual-MiniLM-L12-v2
  - Embed all knowledge base chunks on ingestion
  - Store embeddings in database as JSON blob
  - Add EMBEDDING_MODEL env var
  - _Requirements: Phase 3.5_

- [x] 50. Vector search
  - Implement cosine similarity search over stored embeddings
  - Add KnowledgeBase.semantic_search(query_text, top_k=3)
  - Return tuples of chunk_text, similarity_score, source
  - _Requirements: Phase 3.5_

- [x] 51. RAG
  - Integrate KnowledgeBase into ContextManager adding retrieved_knowledge to built context
  - Add ENABLE_RAG env var defaulting to False
  - When enabled: search knowledge base on every turn, add top-2 results to LLM context
  - Add rag_citations to _build_ai_state()
  - _Requirements: Phase 3.5_

- [x] 52. Search retrieval pipeline
  - Add GET /knowledge/search endpoint (AGENT+ role)
  - Returns query, results list each with text, source, score
  - Add search_latency_ms to metrics
  - _Requirements: Phase 3.4_

- [ ] 53. Tool registry production version
  - Promote tool_registry.py to full production registry with all tools registered
  - Add tool versioning: each tool has a version field
  - Add GET /tools/health endpoint returning each tool availability
  - Add tool execution timeout enforcement via asyncio.wait_for
  - Add tool result caching: same args within same session returns cached result
  - _Requirements: Phase 4.1_

- [ ] 54. API adapters
  - Create backend/adapters/ directory
  - Create backend/adapters/payment_adapter.py with PaymentProvider interface
  - Create backend/adapters/order_adapter.py with OrderProvider interface
  - Both implement mock versions wired to MOCK_TRANSACTIONS
  - Add PAYMENT_PROVIDER env var defaulting to mock
  - _Requirements: Phase 4.3_

- [ ] 55. External actions
  - Add to tool registry: create_case(), update_case(), notify_agent()
  - Add action_requires_confirmation flag per tool
  - Add action_requires_verification flag per tool
  - Dangerous actions always require confirmation=True
  - _Requirements: Phase 4.4_

- [ ] 56. Communication tools
  - Add notify_human_agent(case_id, message) tool that logs
  - Add send_sms_stub(phone, message) that logs only
  - Add send_email_stub(email, subject, body) that logs only
  - Register all in ToolRegistry
  - _Requirements: Phase 4.3_

- [ ] 57. Email
  - Implement send_email using SMTP or SendGrid configurable via EMAIL_PROVIDER env var
  - Default is stub logging only
  - When configured: send actual escalation notification email to agent
  - Add backend/templates/escalation_notification.txt template
  - _Requirements: Phase 4.3_

- [ ] 58. SMS
  - Implement send_sms using Twilio configurable via SMS_PROVIDER env var
  - Default is stub logging only
  - When configured: send SMS notification to agent on escalation
  - _Requirements: Phase 4.3_

- [ ] 59. CRM
  - Add CRMAdapter interface in backend/adapters/crm_adapter.py
  - Implement MockCRMAdapter storing contacts in memory
  - Add get_customer(), create_contact(), update_contact() methods
  - Register as tool: get_customer_history
  - _Requirements: Phase 4.3_

- [ ] 60. Payment actions
  - Add initiate_refund(transaction_id, amount, reason) to payment adapter as stub
  - Requires confidence above 90%, policy approval, audit log entry
  - Add cancel_order(order_id, reason) stub
  - Both require action_requires_confirmation=True
  - _Requirements: Phase 4.4_

- [ ] 61. Action permissions
  - Add ActionPermissionEngine to policy.py
  - Check: role has permission, confidence threshold met, case state valid
  - Block refund if: not AGENT role, confidence below 90%, no verification
  - _Requirements: Phase 4.4_

- [ ] 62. Confirmation policies
  - Add user_confirmation_required field to ToolRegistry entries
  - When True: send confirmation request to frontend via /state SSE before executing
  - Action only executes after user_confirmed=True on CaseState
  - _Requirements: Phase 4.4_

- [ ] 63. Verification action
  - After any state-changing action: call VerificationEngine.verify_action_result()
  - On verification failure: add to case.unverified, set VERIFYING state
  - Add VERIFYING state display in IntelligencePanel timeline
  - _Requirements: Phase 1.12, Phase 4.4_

- [ ] 64. Rollback compensation
  - Add compensating_action field to ToolRegistry: what to do if verification fails
  - If refund verification fails: log, alert ADMIN, set case status to NEEDS_REVIEW
  - Add /admin/cases/needs-review endpoint
  - _Requirements: Phase 4.4_

- [ ] 65. Tool audit trail
  - Every tool execution writes to audit_logs: tool_name, args_hash (not values), result_status, latency_ms, verified
  - Add GET /audit/tools (ADMIN only)
  - Integrate with AuditLogger from ticket 32
  - _Requirements: Phase 4.1_

- [ ] 66. Case management
  - Implement full case lifecycle in database: NEW, AI_HANDLING, WAITING, ESCALATED, HUMAN_ACTIVE, RESOLVED, CLOSED
  - Add PATCH /cases/{id}/status endpoint
  - Add case_status field to CaseState and database with auto-transitions
  - Add case search: GET /cases with status and intent query params
  - _Requirements: Phase 5.1_

- [ ] 67. Agent management
  - Create Agent database table: id, name, email, role, status, active_case_count
  - Add POST /agents endpoint (ADMIN)
  - Add GET /agents/available returning online agents with capacity
  - Add agent presence: POST /agents/{id}/presence with status body
  - _Requirements: Phase 5.1_

- [ ] 68. Dynamic channels
  - Fix hardcoded CHANNEL=prism-demo in VoiceInterface.jsx
  - Generate unique channel per session: prism- plus 12 hex chars
  - Store channel in session state and pass to all polling endpoints
  - Fix Agent.jsx hardcoded polling of wrong channels for voice sessions
  - _Requirements: Phase 5.5_

- [ ] 69. Agent presence
  - Add agent heartbeat: frontend sends POST /agents/{id}/heartbeat every 30s
  - Agent status auto-set to OFFLINE if no heartbeat for 90s
  - Add agent status to sidebar in Agent.jsx
  - Show available agent count on Escalations page
  - _Requirements: Phase 5.1_

- [ ] 70. Queue
  - Add escalation queue: when no agent available case goes to WAITING status
  - Queue ordered by escalation_priority CRITICAL first then created_at
  - Add GET /queue endpoint returning pending cases
  - Add queue_position to case state
  - _Requirements: Phase 5.1_

- [ ] 71. Assignment
  - Add auto-assignment: on escalation assign to least-loaded available AGENT
  - Add manual assignment: PATCH /cases/{id}/assign with agent_id body
  - Add assigned_agent_id to case state
  - _Requirements: Phase 5.1_

- [ ] 72. Human takeover
  - Enhance /cases/{id}/takeover to record agent_id, timestamp, joined_channel
  - Update case status to HUMAN_ACTIVE
  - Emit HUMAN_CONNECTED state to all listeners on /state/{channel}
  - _Requirements: Phase 5.2_

- [ ] 73. Context transfer
  - Ensure escalation ticket includes: intent, full transcript, language, transaction details, tool results, actions taken, confidence score, escalation reason, recommended_next_action
  - Add recommended_next_action field generated by policy engine
  - Add context_transfer_complete flag set when agent joins
  - Frontend shows Context transferred 100% indicator
  - _Requirements: Phase 5.3_

- [ ] 74. Agent notes
  - Add POST /cases/{id}/notes endpoint with agent_id, note_text, note_type fields
  - Store notes in database case_notes table
  - Include notes in GET /cases/{id} response
  - Show notes in Agent.jsx case intelligence panel
  - _Requirements: Phase 5.4_

- [ ] 75. Transfer between agents
  - Add POST /cases/{id}/transfer with from_agent_id, to_agent_id, reason body
  - Update case assigned_agent_id
  - Log transfer in audit_logs
  - _Requirements: Phase 5.4_

- [ ] 76. Supervisor view
  - Add SUPERVISOR role to RBAC
  - Add GET /supervisor/dashboard: all_cases, active_agents, queue_depth, avg_resolution_time
  - Expose supervisor view tab in Agent.jsx visible to SUPERVISOR+ roles
  - _Requirements: Phase 5.4_

- [ ] 77. Case resolution
  - Add POST /cases/{id}/resolve with resolution_text and resolution_type body
  - Update case status to RESOLVED and set resolved_at timestamp
  - Auto-close after 24h with no activity
  - Emit RESOLVED state via /state/{channel}
  - _Requirements: Phase 5.1_

- [ ] 78. Analytics
  - Create backend/analytics.py with AnalyticsEngine
  - Compute from database: total_sessions, ai_resolution_rate, human_escalation_rate, avg_resolution_time_ms, avg_confidence, tool_success_rate
  - Add GET /analytics/summary endpoint (SUPERVISOR+)
  - Add GET /analytics/sessions with from and to query params
  - Update AnalyticsPage.jsx to fetch from real /analytics/summary
  - _Requirements: Phase 8_

- [ ] 79. Advanced languages
  - Add language detection confidence threshold: if below 0.7 ask user to clarify
  - Add ta-IN and bn-IN to language config stubs
  - Add language routing detected_language to appropriate ASR language code
  - Add multilingual fallback response in _generate_human_fallback_reply() for Hindi
  - _Requirements: Phase 7_

- [ ] 80. Multimodal input
  - Add POST /input/image endpoint accepting image upload
  - Return extracted_text, detected_entities, confidence
  - Stub implementation returns placeholder response
  - Add image_context field to CaseState
  - _Requirements: Phase 6_

- [ ] 81. Image understanding
  - Implement image_understanding using base64 encoding plus vision-capable LLM
  - Extract: transaction_id, amount, error_message, merchant_name from payment screenshots
  - Merge extracted data into CaseState via update_case_from_extract()
  - _Requirements: Phase 6_

- [ ] 82. Document understanding
  - Add POST /input/document accepting PDF and text upload
  - Extract text using pdfminer or plain text read
  - Chunk and add to session context
  - _Requirements: Phase 6_

- [ ] 83. Customer feedback
  - Add POST /feedback endpoint with session_id, rating 1-5, comment fields
  - Store in database feedback table
  - Include feedback in analytics
  - Add feedback prompt in frontend after session ends
  - _Requirements: Phase 8_

- [ ] 84. CSAT
  - Compute CSAT score: percentage of sessions with rating >= 4
  - Add csat_score to /analytics/summary
  - Show CSAT in AnalyticsPage.jsx
  - _Requirements: Phase 8_

- [ ] 85. Notifications
  - Add SSE endpoint GET /agents/{id}/events for real-time agent notifications
  - Events: new_case_assigned, case_updated, escalation_received, message
  - Add notification bell count to TopBar.jsx
  - _Requirements: Phase 5.4_

- [ ] 86. Billing plans
  - Add organization and plan tables to database
  - Plans: FREE 100 sessions/mo, PRO 1000 sessions/mo, ENTERPRISE unlimited
  - Add session_count tracking per organization
  - Add GET /billing/usage endpoint
  - _Requirements: Phase 9_

- [ ] 87. Organization workspaces
  - Add organization_id to all database tables
  - Multi-tenant data isolation: all queries filtered by organization_id
  - Add organization registration: POST /organizations
  - _Requirements: Phase 9_

- [ ] 88. API access
  - Add API key management: POST /api-keys, DELETE /api-keys/{id}
  - Support API key auth as alternative to JWT for programmatic access
  - Add rate limits per API key
  - _Requirements: Phase 9_

- [ ] 89. Webhooks
  - Add webhook registration: POST /webhooks with url, events list, secret fields
  - Fire webhooks on: session_start, session_end, escalation, resolution
  - HMAC-sign webhook payloads
  - Add webhook delivery log and retry on failure 3 attempts
  - _Requirements: Phase 9_

- [ ] 90. Developer platform
  - Enhance FastAPI auto-docs with response examples and descriptions
  - Add developer sandbox mode: SANDBOX=true returns mock responses
  - Document all endpoints in README
  - _Requirements: Phase 9_

- [ ] 91. New design system
  - Consolidate all CSS tokens into versioned design system in index.css
  - Document token usage: when to use font-display vs font-sans
  - Add design system documentation file: frontend/DESIGN_SYSTEM.md
  - Ensure all components use only design tokens with no hardcoded colors
  - _Requirements: Phase 10_

- [ ] 92. Typography system
  - Verify DM Serif Display loads with font-display: swap in Google Fonts URL
  - Verify all display typography used in: hero headings, major metrics, AI state labels, empty states
  - Fix any FOUT on initial load
  - _Requirements: Phase 10_

- [ ] 93. Monochrome theme
  - Audit all components for any non-monochromatic colors outside ok/warn/danger semantics
  - Remove any remaining purple/blue/neon values
  - Verify PRISM_STATE_CONFIG colors in prismState.js are updated to monochrome
  - _Requirements: Phase 10_

- [ ] 94. PRISM Core
  - Enhance PrismCore.jsx PLANNING state animation: multi-layer orbital motion
  - Enhance VERIFYING state animation: precise mechanical scan
  - Enhance RESOLVED state animation: settled stable breathing
  - Enhance FAILED state animation: static stark
  - Enhance ENDED state animation: graceful fade-out
  - Add all 14 states to PrismCore CSS in index.css
  - _Requirements: Phase 10_

- [ ] 95. Realtime animations
  - Add PLANNING, VERIFYING, RESOLVED, FAILED, ENDED to IntelligencePanel timeline
  - Update state-label transition animations for all 14 states
  - Add plan_steps visualization in IntelligencePanel showing current plan step
  - Add verification step indicator between ACTING and SPEAKING
  - _Requirements: Phase 10_

- [ ] 96. Physical cards
  - Apply PhysicalCard to: transaction cards in CasePanel, escalation summary cards
  - Add pointer-tracking tilt to MetricCards on Overview page
  - Add press animation to Take over conversation button
  - _Requirements: Phase 10_

- [ ] 97. AI state visualization
  - Update IntelligencePanel to show all 14 states in the pipeline
  - Add plan visualization: show current goal and step
  - Add verification status per tool call
  - Show confidence per field as progress bars (numeric from ticket 18)
  - _Requirements: Phase 10_

- [ ] 98. Agent workspace
  - Redesign Agent.jsx CasesPage with agent controls bar: Take over, Resolve, Add note, Transfer
  - Add agent_notes panel in case intelligence column
  - Add resolution input form
  - Add HUMAN ACTIVE state indicator when agent is live
  - _Requirements: Phase 10_

- [ ] 99. Case workspace
  - Redesign case detail view with: full transcript, tool execution timeline, confidence chart
  - Add case timeline showing all state transitions
  - Show escalation reason prominently
  - Add case action history
  - _Requirements: Phase 10_

- [ ] 100. Mobile experience
  - Implement responsive mobile layout with bottom navigation
  - PrismCore full-screen on mobile
  - Bottom sheet for intelligence panel on mobile
  - PWA manifest and service worker for offline capability
  - _Requirements: Phase 11_

- [ ] 101. Accessibility
  - Add ARIA labels to PrismCore (role=button, aria-label with current state)
  - Add keyboard navigation to sidebar
  - Add focus indicators to all interactive elements
  - Add screen reader announcements for state changes
  - _Requirements: Phase 10_

- [ ] 102. Performance polish
  - Measure and log per-request latency breakdown: STT, LLM, tool, TTS
  - Add performance budget: LLM response under 3s, tool under 1s, total turn under 5s
  - Add lazy loading for Agent.jsx sub-pages
  - Add React.memo to TranscriptConsole, IntelligencePanel, PrismCore
  - _Requirements: Phase 12_
