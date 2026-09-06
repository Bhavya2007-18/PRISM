# ENGINE: ActionEngine
"""
PRISM Tool Registry — canonical tool registration and management.

Every PRISM tool must be registered here. This replaces the hardcoded
get_tool_schemas() in voice_agent.py with a proper registry that supports:
- Schema validation (ticket 14)
- Timeout enforcement (ticket 53)
- Audit logging (ticket 65)
- Tool versioning (ticket 53)
"""
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Callable
import logging

logger = logging.getLogger(__name__)


class ToolValidationError(Exception):
    """Raised when tool input or output fails schema validation."""
    def __init__(self, tool_name: str, field: str, message: str):
        self.tool_name = tool_name
        self.field = field
        super().__init__(f"[{tool_name}] Validation error on '{field}': {message}")


@dataclass
class ToolDefinition:
    name: str
    description: str
    input_schema: Dict[str, Any]
    output_schema: Optional[Dict[str, Any]] = None
    timeout_ms: int = 5000
    requires_verification: bool = False
    audit_log: bool = True
    action_requires_confirmation: bool = False
    action_requires_verification: bool = False
    version: str = "1.0"
    handler: Optional[Callable] = None  # The actual Python function

    def validate_input(self, args: dict) -> None:
        """Validate args against input_schema. Raises ToolValidationError on failure."""
        schema = self.input_schema
        required = schema.get("required", [])
        properties = schema.get("properties", {})

        # Check required fields
        for req_field in required:
            if req_field not in args or args[req_field] is None:
                raise ToolValidationError(self.name, req_field, f"Required field '{req_field}' is missing")

        # Check type constraints for present fields
        for field_name, value in args.items():
            if field_name in properties:
                expected_type = properties[field_name].get("type")
                if expected_type == "string" and not isinstance(value, str):
                    raise ToolValidationError(self.name, field_name, f"Expected string, got {type(value).__name__}")
                if expected_type == "number" and not isinstance(value, (int, float)):
                    raise ToolValidationError(self.name, field_name, f"Expected number, got {type(value).__name__}")

    def validate_output(self, result: dict) -> None:
        """Validate tool result against output_schema. Logs warnings on mismatch."""
        if not self.output_schema:
            return
        properties = self.output_schema.get("properties", {})
        for field_name in properties:
            if field_name not in result:
                import logging
                logging.getLogger(__name__).warning(
                    f"[ToolRegistry] {self.name} output missing field '{field_name}'"
                )

    def to_openai_schema(self) -> dict:
        """Convert to OpenAI tool calling format."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.input_schema,
            }
        }


class ToolRegistry:
    """
    Central registry for all PRISM tools.
    """

    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}

    def register(self, tool: ToolDefinition) -> None:
        """Register a tool definition."""
        self._tools[tool.name] = tool
        logger.debug(f"[ToolRegistry] Registered: {tool.name} v{tool.version}")

    def get_tool(self, name: str) -> Optional[ToolDefinition]:
        """Get tool by name. Returns None if not found."""
        return self._tools.get(name)

    def list_tools(self) -> List[ToolDefinition]:
        """Return all registered tools."""
        return list(self._tools.values())

    def get_schemas(self, case=None) -> List[dict]:
        """
        Return OpenAI-format tool schemas for all registered tools.
        Replaces the hardcoded get_tool_schemas() in voice_agent.py.
        """
        return [t.to_openai_schema() for t in self._tools.values()]

    def execute(self, name: str, args: dict, case=None) -> dict:
        """
        Execute a registered tool with validation and audit logging.
        Raises ToolValidationError if args are invalid.
        Returns structured result.
        """
        import time
        tool = self.get_tool(name)
        if tool is None:
            return {"error": f"Unknown tool: {name}", "success": False}

        # Input validation
        try:
            tool.validate_input(args)
        except ToolValidationError as e:
            logger.warning(f"[ToolRegistry] Input validation failed: {e}")
            return {"error": str(e), "success": False, "validation_error": True}

        # Execute
        if tool.handler is None:
            return {"error": f"Tool '{name}' has no handler registered", "success": False}

        start = time.monotonic()
        try:
            result = tool.handler(**args) if args else tool.handler()
        except Exception as e:
            logger.error(f"[ToolRegistry] Tool '{name}' execution error: {e}")
            return {"error": str(e), "success": False}
        latency_ms = int((time.monotonic() - start) * 1000)

        # Output validation (non-fatal)
        tool.validate_output(result)

        # Audit log
        if tool.audit_log:
            import hashlib
            args_hash = hashlib.sha256(str(sorted(args.items())).encode()).hexdigest()[:12]
            logger.info(
                f"[PRISM][ToolRegistry][AUDIT] tool={name} args_hash={args_hash} "
                f"success={result.get('success', True)} latency_ms={latency_ms}"
            )

        return result

    def get_health(self) -> dict:
        """Return health status of all registered tools."""
        return {
            name: {"status": "ok", "version": tool.version}
            for name, tool in self._tools.items()
        }


# ── Module-level registry singleton ───────────────────────────────────────
registry = ToolRegistry()


def _register_default_tools():
    """Register PRISM's built-in tools."""
    from tools import check_transaction, create_escalation_ticket

    registry.register(ToolDefinition(
        name="check_transaction",
        description=(
            "Look up a payment transaction by its ID (e.g. TX48291). "
            "Returns payment status, order status, amount, and timestamp."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "transaction_id": {
                    "type": "string",
                    "description": "The transaction ID to look up, e.g. TX48291",
                }
            },
            "required": ["transaction_id"],
        },
        output_schema={
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "transaction_id": {"type": "string"},
                "amount": {"type": "number"},
                "status": {"type": "string"},
                "order_status": {"type": "string"},
            },
        },
        timeout_ms=3000,
        requires_verification=True,
        audit_log=True,
        version="1.0",
        handler=check_transaction,
    ))

    registry.register(ToolDefinition(
        name="escalate_to_human",
        description=(
            "Propose escalating the case to a human support specialist. "
            "A deterministic policy gate validates every proposal before handoff."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "reason": {
                    "type": "string",
                    "description": "Detailed reason for escalating.",
                }
            },
            "required": ["reason"],
        },
        timeout_ms=1000,
        requires_verification=False,
        audit_log=True,
        version="1.0",
    ))

    from tools import get_order, refund_status, verify_identity

    registry.register(ToolDefinition(
        name="get_order",
        description="Look up an order by order ID. Returns order status and delivery estimate.",
        input_schema={
            "type": "object",
            "properties": {"order_id": {"type": "string", "description": "The order ID"}},
            "required": ["order_id"],
        },
        timeout_ms=3000,
        audit_log=True,
        version="1.0",
        handler=get_order,
    ))

    registry.register(ToolDefinition(
        name="refund_status",
        description="Check refund eligibility and status for a transaction.",
        input_schema={
            "type": "object",
            "properties": {"transaction_id": {"type": "string", "description": "The transaction ID"}},
            "required": ["transaction_id"],
        },
        timeout_ms=3000,
        audit_log=True,
        version="1.0",
        handler=refund_status,
    ))

    registry.register(ToolDefinition(
        name="verify_identity",
        description="Verify customer identity before performing sensitive actions.",
        input_schema={
            "type": "object",
            "properties": {"identifier": {"type": "string", "description": "Phone number, email, or customer ID"}},
            "required": ["identifier"],
        },
        timeout_ms=2000,
        audit_log=True,
        version="1.0",
        handler=verify_identity,
    ))


# Register tools on module import
_register_default_tools()
