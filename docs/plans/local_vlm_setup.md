# Local VLM Setup: Technical Primer & Phase Plan

> **Status**: Plan (not started)
> **Hardware**: NVIDIA GeForce RTX 5090 (32 GB GDDR7)
> **Target**: Real-time game screenshot analysis for ALAS bot
> **Last updated**: 2026-02-17

---

## 1. Executive Summary

ALAS currently relies on two vision approaches:
1. **Legacy CV** — deterministic template matching, OCR, and pixel/mask detection (fast, reliable, brittle)
2. **Cloud VLM** — Gemini Flash for recovery and annotation tasks (capable, but adds latency and API cost)

A **local VLM** served on our GeForce 5090 would:
- Eliminate API costs for vision tasks during development and autonomous operation
- Enable always-on vision without network dependency
- Reduce latency below cloud round-trip times (target: <3 seconds per screenshot analysis)
- Support the Stage B "Annotate" pipeline (NORTH_STAR.md) where the agent plays screen-by-screen
- Serve as the primary vision layer for the Phase II Gemini orchestrator's vision router

The 5090's 32 GB VRAM and 1,792 GB/s memory bandwidth make it uniquely suited for this role — it can run high-quality 7B–32B vision models at interactive speeds.

---

## 2. Hardware: GeForce RTX 5090

### Specifications

| Spec | Value |
|------|-------|
| Architecture | Blackwell (GB202) |
| CUDA Cores | 21,760 |
| Tensor Cores | 680 (5th gen) |
| VRAM | 32 GB GDDR7 |
| Memory Bandwidth | 1,792 GB/s |
| Memory Bus Width | 512-bit |
| VRAM Speed | 28 Gbps |
| PCIe | Gen 5 x16 |
| TDP | 575W |
| FP16 TFLOPS | 209.5 |
| AI TOPS (INT8) | 838 |
| Launch | January 30, 2025 |
| MSRP | $1,999 |

### LLM Inference Characteristics

The RTX 5090 is **bandwidth-bound** for LLM inference (token generation is limited by how fast weights can be read from VRAM). Key performance expectations based on published benchmarks:

| Model Size | Quant | Approx. tok/s (5090) | Approx. tok/s (4090) | Improvement |
|------------|-------|----------------------|----------------------|-------------|
| 3B | Q4_K_M | ~340 | ~180 | ~90% |
| 7–8B | Q4_K_M | ~210 | ~120 | ~75% |
| 14B | Q4_K_M | ~130 | ~78 | ~67% |
| 32B | Q4_K_M | ~61 | ~38 | ~60% |

*Sources: Puget Systems, NeevCloud, nikolasent benchmarks (Ollama, Q4_K_M, 8k context).*

### VRAM Budget

With 32 GB total, we must budget for:
- **Model weights**: Varies by model and quantization
- **KV cache**: Grows with context length (~0.5–2 GB at 4k–8k context)
- **Vision encoder + mmproj**: Typically 0.5–1.5 GB additional
- **Overhead**: ~1 GB for CUDA runtime and framework

Rule of thumb: target **≤28 GB total** to leave headroom.

---

## 3. Model Selection

### Evaluation Criteria for ALAS

Our use case has specific requirements:
1. **OCR accuracy** — reading game text (English, some CJK), numbers, button labels
2. **UI element recognition** — identifying buttons, menus, dialogs, game states
3. **Spatial understanding** — where on screen are elements located
4. **Speed** — response within 2–3 seconds for real-time, 5–10 seconds for recovery
5. **Structured output** — ability to return JSON describing game state

### Top Candidate Models

#### Tier 1: Primary Recommendations

##### 1. Qwen3-VL-8B (Released October 2025)

The latest in the Qwen VL family. Dense 8B parameter model with state-of-the-art vision capabilities.

| Property | Value |
|----------|-------|
| Parameters | 8.77B |
| Architecture | Dense transformer + ViT |
| Context Window | 256K tokens |
| Ollama Size (Q4_K_M) | 6.1 GB |
| VRAM (Q4_K_M, 8k ctx) | ~8–10 GB |
| VRAM (Q8_0) | ~12–14 GB |
| VRAM (FP16) | ~18–20 GB |
| Expected tok/s (5090, Q4_K_M) | ~180–210 |
| OCR | Excellent (multilingual, structured) |
| Spatial Reasoning | Yes (2D/3D grounding) |
| License | Apache 2.0 |

**Why**: Best balance of speed and capability. Qwen VL models have exceptional OCR and spatial understanding. The 8B size fits comfortably in 32 GB VRAM even at FP16, leaving room for large contexts. At Q4_K_M, it should generate ~180+ tok/s on the 5090 — meaning a 100-token game state description takes ~0.5 seconds of generation time.

```bash
# Ollama
ollama run qwen3-vl:8b

# llama.cpp
llama-server -hf ggml-org/Qwen3-VL-8B-Instruct-GGUF
```

##### 2. MiniCPM-V 4.5 / MiniCPM-o 4.5 (Released 2025)

Built on Qwen3-8B + SigLIP2 vision encoder. 8–9B parameters but achieves scores rivaling 72B models on vision benchmarks. State-of-the-art OCR.

| Property | Value |
|----------|-------|
| Parameters | 8–9B |
| Architecture | Qwen3-8B + SigLIP2-400M |
| Context Window | High-res images up to 1.8M pixels |
| Ollama Size (default) | ~6 GB |
| VRAM (Q4_K_M, 8k ctx) | ~8–10 GB |
| Expected tok/s (5090, Q4_K_M) | ~180–210 |
| OCR | State-of-the-art (OCRBench leader) |
| OpenCompass Score | 77.0–77.6 (surpasses GPT-4o) |
| License | Apache 2.0 |

**Why**: If OCR accuracy is the primary concern (reading game text, numbers, button labels), MiniCPM-V 4.5 is the best sub-10B model available. It beats GPT-4o-latest and Qwen2.5-VL-72B on OpenCompass despite being only 8B. Excellent for document and UI text extraction.

```bash
# Ollama
ollama run openbmb/minicpm-v4.5

# llama.cpp (requires mmproj)
llama-server -m MiniCPM-V-4_5-Q4_K_M.gguf --mmproj mmproj-model-f16.gguf
```

##### 3. Qwen3-VL-32B (Released October 2025)

The dense 32B model pushes capability significantly at the cost of speed — but still fits within the 5090's 32 GB VRAM at Q4_K_M.

| Property | Value |
|----------|-------|
| Parameters | 33B |
| Architecture | Dense transformer + ViT |
| Context Window | 256K tokens |
| Ollama Size (Q4_K_M) | 21 GB |
| VRAM (Q4_K_M, 8k ctx) | ~23–25 GB |
| VRAM (Q8_0) | Would not fit (>32 GB) |
| Expected tok/s (5090, Q4_K_M) | ~55–65 |
| OCR | Excellent+ |
| Spatial/Reasoning | Strong reasoning and spatial understanding |
| License | Apache 2.0 |

**Why**: When accuracy matters more than speed (recovery mode, annotation pipeline). At ~60 tok/s, a 100-token response takes ~1.7 seconds — still within our 5-second recovery budget. This is the maximum quality model that fits in a single 5090.

```bash
# Ollama
ollama run qwen3-vl:32b

# llama.cpp
llama-server -hf ggml-org/Qwen3-VL-32B-Instruct-GGUF
```

#### Tier 2: Strong Alternatives

##### 4. Gemma 3 27B (Released March 2025)

Google's multimodal model. Well-supported in both llama.cpp and Ollama. Known for strong general reasoning.

| Property | Value |
|----------|-------|
| Parameters | 27B |
| Context Window | 128K tokens |
| VRAM (Q4_0) | ~21 GB (model only) |
| VRAM (Q4_0, 8k ctx, vision) | ~24–26 GB |
| VRAM (Q4_0, 82k ctx, vision) | ~30 GB |
| Expected tok/s (5090, Q4_K_M) | ~65–75 |
| License | Gemma Terms of Use (permissive) |

**Why**: Google's QAT (Quantization-Aware Training) means Q4 quantized Gemma models lose less quality than standard post-training quantization. Well-tested ecosystem. Good fallback if Qwen models have issues.

```bash
# Ollama
ollama run gemma3:27b

# llama.cpp
llama-server -hf ggml-org/gemma-3-27b-it-GGUF
```

##### 5. Qwen3-VL-30B-A3B (MoE, Released October 2025)

A Mixture-of-Experts model: 30B total parameters but only 3B active per token. Extremely fast inference while maintaining strong capability.

| Property | Value |
|----------|-------|
| Parameters | 30B total / 3B active |
| Architecture | MoE (128 experts, 8 active) |
| Context Window | 256K tokens |
| Ollama Size | 20 GB |
| VRAM (Q4_K_M, 8k ctx) | ~22–24 GB |
| Expected tok/s (5090) | ~150–200+ (only 3B active) |
| License | Apache 2.0 |

**Why**: MoE gives high capability with near-3B inference speed. If it fits in VRAM (it does at Q4), it could be the fastest high-quality option. Trade-off is higher VRAM for model weights despite fast generation.

```bash
# Ollama
ollama run qwen3-vl:30b

# llama.cpp
llama-server -hf unsloth/Qwen3-VL-30B-A3B-Instruct-GGUF
```

### Model Selection Matrix

| Model | VRAM (Q4) | Speed (tok/s) | OCR Quality | UI Understanding | Recommended Use |
|-------|-----------|---------------|-------------|------------------|-----------------|
| **Qwen3-VL-8B** | ~8–10 GB | ~200 | ★★★★☆ | ★★★★☆ | **Primary: real-time bot** |
| **MiniCPM-V 4.5** | ~8–10 GB | ~200 | ★★★★★ | ★★★★☆ | **Primary: OCR-heavy tasks** |
| **Qwen3-VL-32B** | ~23–25 GB | ~60 | ★★★★★ | ★★★★★ | **Recovery / annotation** |
| Gemma 3 27B | ~24–26 GB | ~70 | ★★★★☆ | ★★★★☆ | Alternative large model |
| Qwen3-VL-30B-A3B | ~22–24 GB | ~170 | ★★★★☆ | ★★★★☆ | Speed+quality hybrid |

### Recommended Strategy

**Dual-model approach**:
1. **Fast model** (Qwen3-VL-8B or MiniCPM-V 4.5, Q4_K_M): For real-time 1 FPS screenshot analysis. ~200 tok/s, <1 second for a typical game state response.
2. **Quality model** (Qwen3-VL-32B, Q4_K_M): For recovery analysis, annotation pipeline, and complex reasoning. ~60 tok/s, 2–5 seconds per response.

Both cannot be loaded simultaneously (combined VRAM exceeds 32 GB). The server would load/unload models on demand, or default to the fast model and swap to quality when needed. Ollama handles this automatically with model unloading.

### Quantization Recommendations

For **vision tasks** (OCR, UI recognition), quantization impact differs from pure text generation:

| Quantization | Quality Impact | VRAM Ratio | Speed | Recommendation |
|-------------|----------------|------------|-------|----------------|
| **FP16** | Baseline | 1.0x | Slowest | Not needed — VRAM limited |
| **Q8_0** | ~<1% loss | 0.5x | Moderate | Best quality if VRAM permits |
| **Q6_K** | ~1–2% loss | 0.4x | Good | Code/precision-sensitive tasks |
| **Q5_K_M** | ~2–3% loss | 0.35x | Good | Excellent balance |
| **Q4_K_M** | ~5% loss | 0.3x | Fast | **Recommended default** — sweet spot |
| **Q3_K_M** | ~10–15% loss | 0.25x | Fastest | Not recommended for vision |

**Key insight**: Vision quality degrades more gracefully with quantization than coding/math tasks. OCR and UI recognition remain strong at Q4_K_M because the visual encoder (typically kept at FP16) does the heavy lifting, while the language model just needs to describe what was seen.

**Important**: The `mmproj` (multimodal projector) file should always be kept at **FP16** regardless of language model quantization. This preserves vision encoding quality.

---

## 4. Serving Options

### Option A: Ollama

Ollama provides the simplest path to serving VLMs locally with an OpenAI-compatible API.

#### Setup

```powershell
# Install Ollama (Windows)
winget install Ollama.Ollama

# Or download from https://ollama.com/download

# Pull a vision model
ollama pull qwen3-vl:8b

# Verify
ollama list
```

#### Running the Server

```powershell
# Ollama runs as a service automatically after install
# Default API endpoint: http://localhost:11434

# Test with a vision model
ollama run qwen3-vl:8b "Describe this image" --images screenshot.png
```

#### API Configuration

Ollama exposes an OpenAI-compatible `/v1/chat/completions` endpoint:

```python
import base64
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama",  # Required but ignored
)

# Encode screenshot as base64
with open("screenshot.png", "rb") as f:
    image_b64 = base64.b64encode(f.read()).decode()

response = client.chat.completions.create(
    model="qwen3-vl:8b",
    messages=[
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "Analyze this Azur Lane screenshot. What screen/page is shown? List all visible UI elements, buttons, and any text. Return JSON."
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{image_b64}"
                    }
                }
            ]
        }
    ],
    max_tokens=500,
    temperature=0.1,
)

print(response.choices[0].message.content)
```

#### Ollama Configuration

```powershell
# Environment variables for tuning
$env:OLLAMA_NUM_PARALLEL = "1"          # Single request at a time (bot is sequential)
$env:OLLAMA_MAX_LOADED_MODELS = "1"     # Keep one model loaded
$env:OLLAMA_KEEP_ALIVE = "24h"          # Keep model in VRAM (bot runs continuously)
$env:OLLAMA_FLASH_ATTENTION = "1"       # Enable flash attention
```

Model-specific settings via Modelfile or API:
```
# Modelfile for game analysis
FROM qwen3-vl:8b
PARAMETER temperature 0.1
PARAMETER top_p 0.8
PARAMETER top_k 20
PARAMETER num_ctx 4096
PARAMETER num_predict 512
```

#### Pros & Cons

| Pros | Cons |
|------|------|
| Easiest setup (single binary) | Less control over quantization |
| Automatic model management | Model naming inconsistencies |
| Built-in OpenAI compatibility | May lag behind llama.cpp features |
| Auto GPU detection | Default context/predict settings can cause issues |
| Windows native support | New multimodal engine (May 2025) still maturing |

### Option B: llama.cpp (llama-server)

llama.cpp provides the most control and often the best raw performance. As of May 2025, it has full multimodal support via the `libmtmd` library.

#### Setup

```powershell
# Option 1: Install via package manager
# (If available — check winget or scoop)

# Option 2: Download pre-built binaries
# Visit: https://github.com/ggml-org/llama.cpp/releases
# Download the CUDA build for Windows (e.g., llama-bxxxx-bin-win-cuda-cu12.x-x64.zip)
# Extract to a directory, e.g., C:\tools\llama-cpp\

# Option 3: Build from source with CUDA
git clone https://github.com/ggml-org/llama.cpp
cd llama.cpp
cmake -B build -DGGML_CUDA=ON
cmake --build build --config Release
```

#### Download Models

```powershell
# Using Hugging Face CLI
pip install huggingface-hub

# Qwen3-VL-8B (Q4_K_M)
huggingface-cli download ggml-org/Qwen3-VL-8B-Instruct-GGUF `
    --local-dir models/qwen3-vl-8b `
    --include "*.gguf"

# Qwen2.5-VL-32B (Q4_K_M) — alternative
huggingface-cli download Mungert/Qwen2.5-VL-32B-Instruct-GGUF `
    --local-dir models/qwen2.5-vl-32b `
    --include "*Q4_K_M*" "*mmproj*"
```

#### Running the Server

```powershell
# Simple: auto-download from HuggingFace
llama-server.exe -hf ggml-org/Qwen3-VL-8B-Instruct-GGUF `
    --host 127.0.0.1 --port 8080 `
    -ngl 999 `          # Offload all layers to GPU
    --flash-attn `      # Enable flash attention
    -c 4096             # Context size

# Manual: specify model and mmproj files
llama-server.exe `
    -m models/qwen3-vl-8b/Qwen3-VL-8B-Instruct-Q4_K_M.gguf `
    --mmproj models/qwen3-vl-8b/mmproj-Qwen3-VL-8B-Instruct-F16.gguf `
    --host 127.0.0.1 --port 8080 `
    -ngl 999 `
    --flash-attn `
    -c 4096

# For the larger 32B model
llama-server.exe -hf ggml-org/Qwen3-VL-32B-Instruct-GGUF `
    --host 127.0.0.1 --port 8080 `
    -ngl 999 `
    --flash-attn `
    -c 4096
```

#### API Usage

llama-server provides an OpenAI-compatible endpoint at `http://localhost:8080/v1/chat/completions`:

```python
import base64
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8080/v1",
    api_key="not-needed",
)

with open("screenshot.png", "rb") as f:
    image_b64 = base64.b64encode(f.read()).decode()

response = client.chat.completions.create(
    model="qwen3-vl-8b",  # Model name (informational for llama-server)
    messages=[
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "What game screen is this? Return JSON with: page_name, visible_buttons, visible_text, notable_elements"},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_b64}"}}
            ]
        }
    ],
    max_tokens=500,
    temperature=0.1,
)
```

#### Pros & Cons

| Pros | Cons |
|------|------|
| Best raw performance | More setup required |
| Full quantization control | Must manage model files yourself |
| Latest model support (fastest to add) | No automatic model management |
| Flash attention, KV cache quantization | Windows build can be finicky |
| Detailed performance metrics | Manual mmproj file management |

### Comparison: Ollama vs llama.cpp

| Feature | Ollama | llama.cpp |
|---------|--------|-----------|
| **Setup Difficulty** | Easy (1 command) | Moderate (build or download binaries) |
| **Vision Model Support** | Yes (since May 2025 engine) | Yes (since May 2025 libmtmd) |
| **OpenAI API Compat** | `/v1/chat/completions` | `/v1/chat/completions` |
| **Model Management** | Automatic (pull/push) | Manual (download GGUF files) |
| **Performance** | Good (uses llama.cpp internally) | Slightly better (direct, less overhead) |
| **Quantization Control** | Limited (pre-packaged quants) | Full (choose any GGUF variant) |
| **Multi-Model** | Yes (auto load/unload) | One model per server instance |
| **KV Cache Quant** | Limited | Full (`--cache-type-k q4_0`) |
| **Flash Attention** | Yes | Yes |
| **Windows** | Native installer | Binary download or build |

**Recommendation**: Start with **Ollama** for Phase L1 (simplicity). Switch to **llama.cpp** for Phase L3/L4 if we need finer control over performance tuning, KV cache quantization, or multi-model scheduling.

---

## 5. Integration Plan: Wiring into ALAS MCP Server

### Architecture: Vision Router

The ARCHITECTURE.md already defines a **Vision Router** in the orchestrator layer. Here's the concrete design:

```
┌─────────────────────────────────────────────────────────┐
│                     Vision Router                        │
│                                                         │
│  ┌─────────────┐   ┌──────────────┐   ┌─────────────┐  │
│  │  Screenshot  │──▶│  Route       │──▶│  Parse      │  │
│  │  (base64)    │   │  Decision    │   │  Response   │  │
│  └─────────────┘   └──────┬───────┘   └─────────────┘  │
│                     ┌─────┴──────┐                      │
│                     ▼            ▼                       │
│              ┌──────────┐ ┌──────────┐                  │
│              │  Local   │ │  Cloud   │                  │
│              │  VLM     │ │  Gemini  │                  │
│              │ (Ollama) │ │  Flash   │                  │
│              └──────────┘ └──────────┘                  │
└─────────────────────────────────────────────────────────┘
```

### New MCP Tool: `vision_analyze`

```python
@mcp.tool()
async def vision_analyze(
    screenshot_b64: str,
    prompt: str = "Describe the current game screen state as JSON",
    provider: str = "auto",  # "local", "cloud", "auto"
    timeout_seconds: float = 5.0,
) -> dict:
    """Analyze a game screenshot using the vision model.
    
    Provider routing:
    - "local": Use local VLM (Ollama/llama.cpp on 5090)
    - "cloud": Use Gemini Flash API
    - "auto": Try local first, fall back to cloud on timeout/error
    
    Returns tool contract envelope:
    {
        "success": bool,
        "data": {"description": str, "parsed": dict | None},
        "error": str | None,
        "observed_state": str | None,
        "expected_state": "vision_analysis_complete",
        "provider_used": "local" | "cloud",
        "latency_ms": float
    }
    """
```

### Configuration

Add to `alas_wrapped/config/` or `agent_orchestrator/` config:

```yaml
# vision_config.yaml
vision:
  # Provider settings
  local:
    enabled: true
    backend: "ollama"              # "ollama" or "llamacpp"
    base_url: "http://localhost:11434/v1"
    model: "qwen3-vl:8b"
    timeout_seconds: 3.0
    max_tokens: 500
    temperature: 0.1
  
  cloud:
    enabled: true
    provider: "gemini"
    model: "gemini-2.0-flash"
    timeout_seconds: 10.0
    max_tokens: 500
  
  # Routing
  routing:
    default_provider: "auto"       # "local", "cloud", "auto"
    fallback_on_timeout: true
    fallback_on_error: true
    
  # Performance
  image:
    max_width: 1280
    max_height: 720
    format: "png"                  # "png" or "jpeg"
    jpeg_quality: 85
```

### Fallback Strategy

```python
async def _route_vision_request(screenshot_b64: str, prompt: str, provider: str) -> dict:
    """Route vision request with fallback logic."""
    
    if provider == "auto":
        # Try local first
        try:
            result = await _call_local_vlm(screenshot_b64, prompt, timeout=3.0)
            return {**result, "provider_used": "local"}
        except (TimeoutError, ConnectionError) as e:
            logger.warning(f"Local VLM failed ({e}), falling back to cloud")
            result = await _call_cloud_vlm(screenshot_b64, prompt, timeout=10.0)
            return {**result, "provider_used": "cloud"}
    
    elif provider == "local":
        result = await _call_local_vlm(screenshot_b64, prompt, timeout=5.0)
        return {**result, "provider_used": "local"}
    
    elif provider == "cloud":
        result = await _call_cloud_vlm(screenshot_b64, prompt, timeout=10.0)
        return {**result, "provider_used": "cloud"}
```

### Integration with Existing MCP Server

The `alas_mcp_server.py` already has `adb_screenshot` which returns base64 PNG. The vision tool chains naturally:

```python
# Example orchestrator workflow:
screenshot = await mcp.call_tool("adb_screenshot")
analysis = await mcp.call_tool("vision_analyze", {
    "screenshot_b64": screenshot["data"]["base64"],
    "prompt": "What page is this? What buttons are visible? Return JSON.",
    "provider": "local"
})
```

---

## 6. Benchmarking Plan

### Latency Targets

| Scenario | Max Latency | Budget Breakdown |
|----------|-------------|------------------|
| **Real-time (1 FPS)** | 2–3 sec | Screenshot: 0.1s + Encode: 0.05s + VLM: 1.5–2.5s + Parse: 0.1s |
| **Recovery mode** | 5–10 sec | Screenshot: 0.1s + Encode: 0.05s + VLM: 4–9s + Parse: 0.1s |
| **Annotation pipeline** | 15–30 sec | Can tolerate larger models, longer prompts, multi-turn |

### Throughput Requirements

- Bot screenshot rate: ~1 FPS (1280×720 PNG)
- VLM must process: ≥1 screenshot every 2–3 seconds (real-time) or ≥1 every 5–10 seconds (recovery)
- Token output per analysis: ~50–200 tokens (structured JSON game state)
- Token input per image: ~1000–2000 tokens (depends on model's vision tokenizer + prompt)

### Test Scenarios

#### Scenario 1: Page Identification
- **Input**: Game screenshot
- **Prompt**: "What Azur Lane page/screen is this? Return one of: page_main, page_campaign, page_dock, page_academy, page_shop, page_unknown"
- **Expected output**: Single page name
- **Metrics**: Accuracy (vs ground truth), latency

#### Scenario 2: UI Element Extraction
- **Input**: Game screenshot
- **Prompt**: "List all visible buttons and interactive elements with their approximate screen positions (x, y). Return JSON array."
- **Expected output**: JSON array of {name, x, y}
- **Metrics**: Precision, recall, position accuracy, latency

#### Scenario 3: Text/Number Reading (OCR)
- **Input**: Game screenshot showing resources
- **Prompt**: "Read all visible numbers and resource counts (oil, gold, gems, etc). Return JSON."
- **Expected output**: JSON with resource values
- **Metrics**: Exact match accuracy, latency

#### Scenario 4: Anomaly Detection
- **Input**: Game screenshot with error dialog or unexpected state
- **Prompt**: "Is there any error, popup, or unexpected dialog? If so, describe it and suggest an action."
- **Expected output**: Description + action suggestion
- **Metrics**: Detection rate, action quality, latency

### Benchmarking Script

```python
#!/usr/bin/env python3
"""Benchmark local VLM against game screenshots."""

import asyncio
import base64
import json
import time
from pathlib import Path
from openai import AsyncOpenAI

SCREENSHOTS_DIR = Path("alas_wrapped/screenshots")
RESULTS_FILE = Path("docs/plans/vlm_benchmark_results.json")

# Configure for Ollama
client = AsyncOpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
MODEL = "qwen3-vl:8b"

PROMPTS = {
    "page_id": "What Azur Lane page/screen is this? Reply with only the page name.",
    "ui_elements": "List all visible buttons and UI elements. Return JSON array.",
    "ocr": "Read all visible text and numbers. Return JSON.",
    "anomaly": "Is there an error popup or unexpected dialog? Describe if yes.",
}

async def benchmark_single(image_path: Path, prompt_key: str) -> dict:
    with open(image_path, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode()
    
    start = time.perf_counter()
    response = await client.chat.completions.create(
        model=MODEL,
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": PROMPTS[prompt_key]},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}}
            ]
        }],
        max_tokens=500,
        temperature=0.1,
    )
    elapsed = time.perf_counter() - start
    
    return {
        "image": image_path.name,
        "prompt": prompt_key,
        "latency_s": round(elapsed, 3),
        "tokens": response.usage.completion_tokens if response.usage else None,
        "response": response.choices[0].message.content,
    }

async def main():
    screenshots = list(SCREENSHOTS_DIR.glob("*.png"))[:20]  # Limit for benchmarking
    results = []
    
    for img in screenshots:
        for prompt_key in PROMPTS:
            result = await benchmark_single(img, prompt_key)
            results.append(result)
            print(f"  {img.name} / {prompt_key}: {result['latency_s']}s")
    
    # Summary
    latencies = [r["latency_s"] for r in results]
    summary = {
        "model": MODEL,
        "total_tests": len(results),
        "avg_latency_s": round(sum(latencies) / len(latencies), 3),
        "p50_latency_s": round(sorted(latencies)[len(latencies) // 2], 3),
        "p95_latency_s": round(sorted(latencies)[int(len(latencies) * 0.95)], 3),
        "max_latency_s": round(max(latencies), 3),
    }
    
    output = {"summary": summary, "results": results}
    RESULTS_FILE.write_text(json.dumps(output, indent=2))
    print(f"\nSummary: {json.dumps(summary, indent=2)}")

if __name__ == "__main__":
    asyncio.run(main())
```

### Performance Expectations

Based on research data, expected benchmarks on RTX 5090:

| Model | Quant | Prompt Processing | Token Generation | Est. Total (1 image + 150 tok response) |
|-------|-------|-------------------|------------------|-----------------------------------------|
| Qwen3-VL-8B | Q4_K_M | ~500–1000 tok/s | ~200 tok/s | **~1.5–2.5 sec** |
| MiniCPM-V 4.5 | Q4_K_M | ~500–1000 tok/s | ~200 tok/s | **~1.5–2.5 sec** |
| Qwen3-VL-32B | Q4_K_M | ~200–400 tok/s | ~60 tok/s | **~4–7 sec** |
| Gemma 3 27B | Q4_K_M | ~250–500 tok/s | ~70 tok/s | **~3.5–6 sec** |
| Qwen3-VL-30B-A3B | Q4_K_M | ~400–800 tok/s | ~170 tok/s | **~2–3.5 sec** |

*Note: Vision prompt processing includes both text and image token processing. The image portion adds ~1000–2000 tokens depending on model and resolution. These are estimates extrapolated from published text-only benchmarks — actual vision latency may differ and must be validated empirically.*

---

## 7. Phase Plan

### Phase L1: Install & Basic Serving (1–2 days)

**Goal**: Get a local VLM running and responding to image queries.

**Steps**:
1. Install Ollama on the 5090 machine
   ```powershell
   winget install Ollama.Ollama
   ```
2. Pull the primary model
   ```powershell
   ollama pull qwen3-vl:8b
   ```
3. Verify vision works with a test image
   ```powershell
   ollama run qwen3-vl:8b "What do you see in this image?" --images test_screenshot.png
   ```
4. Verify the OpenAI-compatible API is accessible
   ```python
   # Quick test script
   from openai import OpenAI
   client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
   response = client.models.list()
   print([m.id for m in response.data])
   ```
5. Take a game screenshot and test analysis
   ```powershell
   # From ALAS, capture a screenshot
   # Then test:
   ollama run qwen3-vl:8b "What Azur Lane screen is this? List visible UI elements." --images screenshot.png
   ```

**Success Criteria**:
- [ ] Ollama running and serving qwen3-vl:8b
- [ ] Can send an image via OpenAI-compatible API and get a response
- [ ] Response time < 5 seconds for a game screenshot
- [ ] Model fits in VRAM with room for context

**Deliverables**:
- Working Ollama installation
- Test script confirming API accessibility

---

### Phase L2: Benchmark Against Game Screenshots (2–3 days)

**Goal**: Determine whether local VLM meets ALAS's latency and accuracy requirements.

**Steps**:
1. Collect 20–50 game screenshots covering key screens:
   - Main menu, campaign, dock, academy, shop
   - Dialog boxes, popups, error states
   - Resource counters (oil, gold, gems)
   - Battle screens, reward screens
2. Create ground-truth labels (page name, visible elements, text/numbers)
3. Run the benchmarking script (from Section 6) against multiple models:
   - `qwen3-vl:8b` (Q4_K_M)
   - `openbmb/minicpm-v4.5` (default quant)
   - `qwen3-vl:32b` (Q4_K_M) — for comparison
4. Measure latency, accuracy, and token usage
5. Test different quantization levels if needed:
   ```powershell
   # Try Q8 for quality comparison
   ollama pull qwen3-vl:8b-q8_0
   ```
6. Document findings in `docs/plans/vlm_benchmark_results.json`

**Success Criteria**:
- [ ] At least one model delivers page identification at >90% accuracy, <3 sec latency
- [ ] OCR accuracy on resource numbers at >95%
- [ ] P95 latency under 5 seconds for the "fast" model
- [ ] Documented comparison of at least 2 models

**Deliverables**:
- Benchmark results file
- Model selection decision with rationale
- Performance characteristics documented

---

### Phase L3: Integration with MCP Server (3–5 days)

**Goal**: Wire the local VLM into the ALAS MCP server as a callable tool.

**Steps**:
1. Create `agent_orchestrator/vision_router.py`:
   - OpenAI client for local VLM (Ollama)
   - OpenAI client for cloud VLM (Gemini)
   - Routing logic (auto/local/cloud)
   - Timeout and fallback handling
2. Add `vision_analyze` tool to `alas_mcp_server.py`
3. Create `vision_config.yaml` configuration
4. Add integration tests:
   ```python
   async def test_vision_analyze_local():
       result = await mcp.call_tool("vision_analyze", {
           "screenshot_b64": test_screenshot_b64,
           "prompt": "What page is this?",
           "provider": "local"
       })
       assert result["success"]
       assert result["provider_used"] == "local"
       assert result["latency_ms"] < 5000
   ```
5. Test the full chain: `adb_screenshot` → `vision_analyze` → parse state
6. Validate fallback: stop Ollama → verify cloud fallback works

**Success Criteria**:
- [ ] `vision_analyze` tool registered and callable via MCP
- [ ] "auto" routing tries local first, falls back to cloud
- [ ] Integration test passes with both providers
- [ ] Latency within targets (see Section 6)

**Deliverables**:
- `agent_orchestrator/vision_router.py`
- Updated `alas_mcp_server.py` with `vision_analyze` tool
- `vision_config.yaml`
- Integration tests
- Updated `docs/agent_tooling/README.md`

---

### Phase L4: Production Deployment (2–3 days)

**Goal**: Reliable, always-on local VLM serving for autonomous bot operation.

**Steps**:
1. Configure Ollama as a Windows service (auto-start on boot):
   ```powershell
   # Ollama typically auto-starts. Verify:
   Get-Service Ollama
   
   # Set environment variables persistently
   [System.Environment]::SetEnvironmentVariable("OLLAMA_KEEP_ALIVE", "24h", "Machine")
   [System.Environment]::SetEnvironmentVariable("OLLAMA_NUM_PARALLEL", "1", "Machine")
   [System.Environment]::SetEnvironmentVariable("OLLAMA_FLASH_ATTENTION", "1", "Machine")
   ```
2. Add health check to MCP server startup:
   ```python
   async def _check_vlm_health():
       """Verify local VLM is responding before starting bot."""
       try:
           response = await local_client.chat.completions.create(
               model="qwen3-vl:8b",
               messages=[{"role": "user", "content": "ping"}],
               max_tokens=5,
           )
           return True
       except Exception as e:
           logger.warning(f"Local VLM health check failed: {e}")
           return False
   ```
3. Add monitoring/metrics:
   - Log latency per vision call
   - Track local vs cloud fallback ratio
   - Alert if local VLM latency degrades
4. Optimize for production:
   - Pre-warm model on startup (send a dummy request)
   - Tune `num_ctx` based on actual usage patterns
   - Consider switching to llama.cpp if Ollama overhead is significant
5. Update ARCHITECTURE.md vision integration status to "Working"
6. Update ROADMAP.md

**OR, if llama.cpp proves better in benchmarks**:
```powershell
# Create a PowerShell script to auto-start llama-server
# start_vlm_server.ps1
$env:CUDA_VISIBLE_DEVICES = "0"
& "C:\tools\llama-cpp\llama-server.exe" `
    -hf ggml-org/Qwen3-VL-8B-Instruct-GGUF `
    --host 127.0.0.1 --port 8080 `
    -ngl 999 --flash-attn `
    -c 4096 `
    --metrics
```

**Success Criteria**:
- [ ] VLM auto-starts with the machine
- [ ] Bot can run autonomously using local VLM for vision
- [ ] Cloud fallback activates automatically on local failure
- [ ] Latency metrics logged and within targets
- [ ] Docs updated

**Deliverables**:
- Production configuration (service/startup scripts)
- Health check in MCP server
- Monitoring/logging
- Updated ARCHITECTURE.md (Vision Integration status → Working)
- Updated ROADMAP.md
- CHANGELOG.md entry

---

## Appendix A: Model Availability by Date

> This section tracks which models were available as of this document's creation (Feb 2026) and their ecosystem readiness.

| Model | Release | Ollama | llama.cpp GGUF | Notes |
|-------|---------|--------|----------------|-------|
| Qwen2.5-VL-7B | Jan 2025 | ✅ | ✅ | Mature, well-tested |
| Qwen2.5-VL-32B | Mar 2025 | ✅ | ✅ | First large open VLM with great quality |
| Gemma 3 27B | Mar 2025 | ✅ | ✅ | Google QAT, strong ecosystem |
| MiniCPM-V 4.5 | ~Mid 2025 | ✅ | ✅ | OCR champion, 8B |
| Qwen3-VL-8B | Oct 2025 | ✅ | ✅ | Latest gen, recommended |
| Qwen3-VL-32B | Oct 2025 | ✅ | ✅ | Dense, high quality |
| Qwen3-VL-30B-A3B | Oct 2025 | ✅ | ✅ | MoE, fast inference |
| Mistral Small 3.1 | Mar 2025 | ✅ | ✅ | 24B, tool-calling capable |

## Appendix B: Supported llama.cpp Vision Models

Canonical list from [llama.cpp multimodal docs](https://github.com/ggml-org/llama.cpp/blob/master/docs/multimodal.md):

```bash
# Qwen family
llama-server -hf ggml-org/Qwen2.5-VL-7B-Instruct-GGUF
llama-server -hf ggml-org/Qwen2.5-VL-32B-Instruct-GGUF
# Qwen3-VL requires latest builds (post Oct 2025)

# Gemma 3
llama-server -hf ggml-org/gemma-3-4b-it-GGUF
llama-server -hf ggml-org/gemma-3-12b-it-GGUF
llama-server -hf ggml-org/gemma-3-27b-it-GGUF

# MiniCPM-V
llama-server -m MiniCPM-V-4_5-Q4_K_M.gguf --mmproj mmproj-model-f16.gguf

# Others
llama-server -hf ggml-org/SmolVLM2-2.2B-Instruct-GGUF
llama-server -hf ggml-org/InternVL2.5-4B-GGUF
```

## Appendix C: Quick Reference Commands

```powershell
# === OLLAMA ===
# Install
winget install Ollama.Ollama

# Pull models
ollama pull qwen3-vl:8b
ollama pull qwen3-vl:32b
ollama pull openbmb/minicpm-v4.5

# Interactive test with image
ollama run qwen3-vl:8b "Describe this image" --images screenshot.png

# Check loaded models
ollama ps

# Check VRAM usage
nvidia-smi

# === LLAMA.CPP ===
# Serve model
llama-server -hf ggml-org/Qwen3-VL-8B-Instruct-GGUF --host 127.0.0.1 --port 8080 -ngl 999 --flash-attn -c 4096

# Test endpoint
curl http://localhost:8080/v1/models

# === MONITORING ===
# Watch GPU usage
nvidia-smi -l 1

# Watch Ollama logs (Windows)
Get-Content "$env:LOCALAPPDATA\Ollama\server.log" -Tail 50 -Wait
```

## Appendix D: Extrapolations & Uncertainty

Where definitive February 2026 data was unavailable, the following extrapolations were made:

1. **RTX 5090 VLM-specific benchmarks**: Published benchmarks are primarily for text-only LLMs. Vision models add overhead for image encoding (prompt processing). We estimate a 20–40% increase in total latency vs text-only for the same model, primarily in the prompt processing phase.

2. **Qwen3-VL generation speed**: Extrapolated from Qwen3 text model benchmarks on 5090 (e.g., qwen2.5:32b at ~62 tok/s). Vision versions use similar architectures with added vision encoder overhead.

3. **MoE model speeds**: The Qwen3-VL-30B-A3B speed estimate (~170 tok/s) is based on the fact that only 3B parameters are active per token, placing it between 3B and 8B dense model speeds, with some MoE routing overhead.

4. **Quantization quality for vision**: The claim that vision tasks degrade more gracefully with quantization is based on research showing that the vision encoder (typically kept at FP16) preserves perceptual quality while the language model's Q4 quantization primarily affects text generation nuance — which matters less for structured output extraction.

5. **Total latency estimates**: Combine prompt processing (image tokens + text tokens) and generation phases. Image token count varies dramatically by model and resolution — Qwen VL models are relatively efficient but exact token counts for 1280×720 images should be measured empirically.
