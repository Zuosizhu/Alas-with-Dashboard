import argparse
import base64
import io
import json
import sys
from typing import Any, Dict, Optional

from PIL import Image

from alas import AzurLaneAutoScript
from module.ui.page import Page


class _McpServer:
    def __init__(self, config_name: str):
        self.script = AzurLaneAutoScript(config_name=config_name)
        self._state_machine = self.script.state_machine

    def _result(self, request_id: Any, result: Any) -> Dict[str, Any]:
        return {"jsonrpc": "2.0", "id": request_id, "result": result}

    def _error(self, request_id: Any, code: int, message: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        err: Dict[str, Any] = {"code": code, "message": message}
        if data is not None:
            err["data"] = data
        return {"jsonrpc": "2.0", "id": request_id, "error": err}

    def _tool_specs(self):
        tools = [
            {
                "name": "adb.screenshot",
                "description": "Take a screenshot from the connected emulator/device.",
                "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
            },
            {
                "name": "adb.tap",
                "description": "Tap a coordinate using ADB input tap.",
                "inputSchema": {
                    "type": "object",
                    "properties": {"x": {"type": "integer"}, "y": {"type": "integer"}},
                    "required": ["x", "y"],
                    "additionalProperties": False,
                },
            },
            {
                "name": "adb.swipe",
                "description": "Swipe between coordinates using ADB input swipe.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "x1": {"type": "integer"},
                        "y1": {"type": "integer"},
                        "x2": {"type": "integer"},
                        "y2": {"type": "integer"},
                        "duration_ms": {"type": "integer"},
                    },
                    "required": ["x1", "y1", "x2", "y2"],
                    "additionalProperties": False,
                },
            },
            {
                "name": "alas.get_current_state",
                "description": "Return the current ALAS UI Page name.",
                "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
            },
            {
                "name": "alas.goto",
                "description": "Navigate to a target ALAS UI Page by name (e.g. page_main).",
                "inputSchema": {
                    "type": "object",
                    "properties": {"page": {"type": "string"}},
                    "required": ["page"],
                    "additionalProperties": False,
                },
            },
            {
                "name": "alas.list_tools",
                "description": "List deterministic ALAS tools registered in the state machine.",
                "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
            },
            {
                "name": "alas.call_tool",
                "description": "Invoke a deterministic ALAS tool by name.",
                "inputSchema": {
                    "type": "object",
                    "properties": {"name": {"type": "string"}, "arguments": {"type": "object"}},
                    "required": ["name"],
                    "additionalProperties": False,
                },
            },
        ]
        return tools

    def _encode_screenshot_png_base64(self) -> str:
        image = self.script.device.screenshot()
        if getattr(image, "shape", None) is not None and len(image.shape) == 3 and image.shape[2] == 3:
            img = Image.fromarray(image[:, :, ::-1])
        else:
            img = Image.fromarray(image)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode("ascii")

    def _handle_tools_call(self, name: str, arguments: Dict[str, Any]):
        if name == "adb.screenshot":
            data = self._encode_screenshot_png_base64()
            return {
                "content": [
                    {"type": "image", "mimeType": "image/png", "data": data}
                ]
            }

        if name == "adb.tap":
            x = int(arguments["x"])
            y = int(arguments["y"])
            self.script.device.click_adb(x, y)
            return {"content": [{"type": "text", "text": f"tapped {x},{y}"}]}

        if name == "adb.swipe":
            x1 = int(arguments["x1"])
            y1 = int(arguments["y1"])
            x2 = int(arguments["x2"])
            y2 = int(arguments["y2"])
            duration_ms = arguments.get("duration_ms")
            duration = 0.1 if duration_ms is None else (int(duration_ms) / 1000.0)
            self.script.device.swipe_adb((x1, y1), (x2, y2), duration=duration)
            return {"content": [{"type": "text", "text": f"swiped {x1},{y1}->{x2},{y2}"}]}

        if name == "alas.get_current_state":
            page = self._state_machine.get_current_state()
            return {"content": [{"type": "text", "text": str(page)}]}

        if name == "alas.goto":
            page_name = arguments["page"]
            destination = Page.all_pages.get(page_name)
            if destination is None:
                raise KeyError(f"unknown page: {page_name}")
            self._state_machine.transition(destination)
            return {"content": [{"type": "text", "text": f"navigated to {page_name}"}]}

        if name == "alas.list_tools":
            tools = [
                {"name": t.name, "description": t.description, "parameters": t.parameters}
                for t in self._state_machine.get_all_tools()
            ]
            return {"content": [{"type": "text", "text": json.dumps(tools, ensure_ascii=False)}]}

        if name == "alas.call_tool":
            tool_name = arguments["name"]
            tool_args = arguments.get("arguments") or {}
            result = self._state_machine.call_tool(tool_name, **tool_args)
            return {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False, default=str)}]}

        raise KeyError(f"unknown tool: {name}")

    def handle(self, request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if "id" not in request:
            return None

        request_id = request.get("id")
        method = request.get("method")
        params = request.get("params") or {}

        try:
            if method == "initialize":
                return self._result(
                    request_id,
                    {
                        "protocolVersion": "2024-11-05",
                        "serverInfo": {"name": "alas-mcp", "version": "0.1.0"},
                        "capabilities": {"tools": {}},
                    },
                )

            if method == "tools/list":
                return self._result(request_id, {"tools": self._tool_specs()})

            if method == "tools/call":
                name = params.get("name")
                arguments = params.get("arguments") or {}
                if not name:
                    return self._error(request_id, -32602, "Missing tool name")
                result = self._handle_tools_call(name, arguments)
                return self._result(request_id, result)

            if method == "ping":
                return self._result(request_id, {})

            return self._error(request_id, -32601, f"Method not found: {method}")
        except Exception as e:
            return self._error(
                request_id,
                -32000,
                "Server error",
                data={"type": type(e).__name__, "message": str(e)},
            )


def _read_json_line() -> Optional[Dict[str, Any]]:
    line = sys.stdin.readline()
    if not line:
        return None
    line = line.strip()
    if not line:
        return {}
    return json.loads(line)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="alas")
    args = parser.parse_args()

    server = _McpServer(config_name=args.config)
    while True:
        msg = _read_json_line()
        if msg is None:
            break
        if not msg:
            continue
        resp = server.handle(msg)
        if resp is None:
            continue
        sys.stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
