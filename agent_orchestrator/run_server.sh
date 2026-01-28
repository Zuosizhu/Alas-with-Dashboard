#!/bin/bash
cd "$(dirname "$0")"
export PYTHONIOENCODING=utf-8
uv run alas_mcp_server.py --config "${1:-alas}"
