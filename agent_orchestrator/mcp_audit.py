"""MCP audit logging -- append-only JSONL with rotation.

Every MCP tool call is logged with timestamp, tool name, arguments,
caller identity, duration, result summary, and error info.

Two integration paths:
- FastMCP Middleware (AuditMiddleware) for the MCP stdio transport
- audit_cli_call() wrapper for the --cli subprocess path
"""
from __future__ import annotations

import json
import logging
import os
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Optional

_logger = logging.getLogger("mcp_audit")

# ---------------------------------------------------------------------------
# Reusable JSONL append helper
# ---------------------------------------------------------------------------
try:
    from module.base.jsonl import append_jsonl
except ImportError:
    # Fallback when ALAS is not importable (unit tests, standalone use).
    def append_jsonl(path, payload, rotate_bytes=None, error_callback=None):
        try:
            folder = os.path.dirname(path)
            if folder:
                os.makedirs(folder, exist_ok=True)
            if (
                rotate_bytes
                and os.path.exists(path)
                and os.path.getsize(path) >= rotate_bytes
            ):
                root, ext = os.path.splitext(path)
                ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
                os.replace(path, f"{root}.{ts}{ext or '.jsonl'}")
            with open(path, "a", encoding="utf-8") as f:
                f.write(json.dumps(payload, ensure_ascii=True) + "\n")
            return True
        except Exception as e:
            if error_callback:
                try:
                    error_callback(e)
                except Exception:
                    pass
            return False


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
_AUDIT_FILE = str(Path(__file__).parent / "mcp_audit.jsonl")
_ROTATE_BYTES = 20 * 1024 * 1024  # 20 MB
_debug_mode: bool = False


def configure(*, debug: bool = False, audit_path: Optional[str] = None):
    """Called once at startup to set module-level configuration."""
    global _debug_mode, _AUDIT_FILE
    _debug_mode = debug
    if audit_path:
        _AUDIT_FILE = audit_path


# ---------------------------------------------------------------------------
# Result summarization
# ---------------------------------------------------------------------------
def _summarize_result(result: Any) -> str:
    """Short human-readable summary. Never includes full base64 data."""
    # FastMCP ToolResult (has .content list of ContentBlock)
    if hasattr(result, "content") and isinstance(result.content, list):
        parts = []
        for block in result.content:
            block_type = getattr(block, "type", None)
            if block_type == "text":
                text = getattr(block, "text", "")
                parts.append(f"text: {text[:120]}" if len(text) > 120 else f"text: {text}")
            elif block_type == "image":
                mime = getattr(block, "mimeType", "image/unknown")
                data = getattr(block, "data", "")
                size_kb = (len(data) * 3 // 4) / 1024 if data else 0
                parts.append(f"image: {mime}, ~{size_kb:.0f}KB")
            else:
                parts.append(f"{block_type or 'unknown'}: ...")
        return "; ".join(parts) if parts else "<empty>"

    # Raw dict (CLI path or direct return)
    if isinstance(result, dict):
        if "content" in result and isinstance(result["content"], list):
            parts = []
            for item in result["content"]:
                if isinstance(item, dict):
                    if item.get("type") == "image":
                        mime = item.get("mimeType", "image/unknown")
                        data = item.get("data", "")
                        size_kb = (len(data) * 3 // 4) / 1024 if data else 0
                        parts.append(f"image: {mime}, ~{size_kb:.0f}KB")
                    elif item.get("type") == "text":
                        text = item.get("text", "")
                        parts.append(f"text: {text[:120]}")
            return "; ".join(parts) if parts else str(result)[:200]
        if "success" in result:
            state = result.get("observed_state") or result.get("expected_state")
            status = "ok" if result.get("success") else "fail"
            return f"{status}, state={state}"
        return str(result)[:200]

    if isinstance(result, list):
        return f"list[{len(result)} items]"

    if isinstance(result, str):
        return result[:200]

    return str(result)[:200]


# ---------------------------------------------------------------------------
# Argument sanitization
# ---------------------------------------------------------------------------
def _sanitize_arguments(arguments: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Strip large binary data and _caller from logged args."""
    if not arguments:
        return {}
    sanitized = {}
    for k, v in arguments.items():
        if k == "_caller":
            continue
        if isinstance(v, str) and len(v) > 500:
            sanitized[k] = f"<{len(v)} chars>"
        else:
            sanitized[k] = v
    return sanitized


# ---------------------------------------------------------------------------
# Caller identification
# ---------------------------------------------------------------------------
def _detect_caller(arguments: Optional[Dict[str, Any]]) -> str:
    """Extract caller identity from arguments, env, or heuristics."""
    if arguments and "_caller" in arguments:
        return str(arguments["_caller"])
    env_caller = os.environ.get("MCP_CALLER")
    if env_caller:
        return env_caller
    term = os.environ.get("TERM_PROGRAM", "")
    if "claude" in term.lower():
        return "claude-code"
    return "unknown"


# ---------------------------------------------------------------------------
# Record construction and writing
# ---------------------------------------------------------------------------
def _build_audit_record(
    *,
    tool_name: str,
    arguments: Optional[Dict[str, Any]],
    caller: str,
    duration_ms: float,
    status: str,
    error: Optional[str],
    result_summary: str,
    mode: str,
) -> Dict[str, Any]:
    return {
        "ts": datetime.now(timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z"),
        "tool": tool_name,
        "arguments": _sanitize_arguments(arguments),
        "caller": caller,
        "duration_ms": round(duration_ms, 2),
        "status": status,
        "error": error,
        "result_summary": result_summary,
        "pid": os.getpid(),
        "mode": mode,
    }


def _write_audit(record: Dict[str, Any]) -> None:
    """Write one audit record to JSONL and optionally to stderr."""
    append_jsonl(
        _AUDIT_FILE,
        record,
        rotate_bytes=_ROTATE_BYTES,
        error_callback=lambda e: _logger.warning(f"audit write failed: {e}"),
    )
    if _debug_mode:
        ts = record["ts"]
        tool = record["tool"]
        dur = record["duration_ms"]
        caller = record["caller"]
        status = record["status"]
        summary = record["result_summary"]
        err = record.get("error")
        line = f"[AUDIT] {ts} {tool} caller={caller} {dur:.1f}ms {status}"
        if err:
            line += f" ERROR: {err}"
        else:
            line += f" -> {summary}"
        print(line, file=sys.stderr)


# ---------------------------------------------------------------------------
# FastMCP Middleware
# ---------------------------------------------------------------------------
AuditMiddleware = None  # Will be set below if FastMCP is available

try:
    from fastmcp.server.middleware import Middleware, MiddlewareContext, CallNext
    from fastmcp.tools.tool import ToolResult as _ToolResult

    import mcp.types as _mt

    class _AuditMiddleware(Middleware):
        """Audit logging middleware for all MCP tool calls."""

        async def on_call_tool(
            self,
            context: MiddlewareContext[_mt.CallToolRequestParams],
            call_next: CallNext[_mt.CallToolRequestParams, _ToolResult],
        ) -> _ToolResult:
            tool_name = context.message.name
            arguments = dict(context.message.arguments or {})
            caller = _detect_caller(arguments)

            # Strip _caller before forwarding to real tool
            if "_caller" in arguments:
                clean_args = {k: v for k, v in arguments.items() if k != "_caller"}
                context = context.copy(
                    message=_mt.CallToolRequestParams(
                        name=tool_name,
                        arguments=clean_args,
                    )
                )

            start = time.perf_counter()
            error_msg = None
            status = "success"
            result_summary = ""

            try:
                result = await call_next(context)
                result_summary = _summarize_result(result)
                return result
            except Exception as e:
                status = "error"
                error_msg = f"{type(e).__name__}: {e}"
                if _debug_mode:
                    error_msg += "\n" + traceback.format_exc(limit=6)
                raise
            finally:
                duration_ms = (time.perf_counter() - start) * 1000
                record = _build_audit_record(
                    tool_name=tool_name,
                    arguments=arguments,
                    caller=caller,
                    duration_ms=duration_ms,
                    status=status,
                    error=error_msg,
                    result_summary=result_summary,
                    mode="mcp",
                )
                _write_audit(record)

    AuditMiddleware = _AuditMiddleware

except ImportError:
    pass  # FastMCP not installed; CLI path still works


# ---------------------------------------------------------------------------
# CLI path wrapper
# ---------------------------------------------------------------------------
def audit_cli_call(
    tool_name: str,
    arguments: Dict[str, Any],
    func: Callable,
) -> Any:
    """Wrap a CLI tool invocation with audit logging.

    Returns the raw result; raises on error (after logging).
    """
    caller = _detect_caller(arguments)
    clean_args = {k: v for k, v in arguments.items() if k != "_caller"}

    start = time.perf_counter()
    error_msg = None
    status = "success"
    result_summary = ""

    try:
        result = func(**clean_args)
        result_summary = _summarize_result(result)
        return result
    except Exception as e:
        status = "error"
        error_msg = f"{type(e).__name__}: {e}"
        if _debug_mode:
            error_msg += "\n" + traceback.format_exc(limit=6)
        raise
    finally:
        duration_ms = (time.perf_counter() - start) * 1000
        record = _build_audit_record(
            tool_name=tool_name,
            arguments=arguments,
            caller=caller,
            duration_ms=duration_ms,
            status=status,
            error=error_msg,
            result_summary=result_summary,
            mode="cli",
        )
        _write_audit(record)
