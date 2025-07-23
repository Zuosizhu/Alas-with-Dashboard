"""
Configuration settings for LLM vision integration.
"""
import os

# --- API Configuration ---
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")

# --- Model Settings ---
GEMINI_MODEL = "gemini-2.5-flash"

# --- Logging Configuration ---
VISION_LOG_FILE = "logs/vision_llm.log"
LOG_LEVEL = "DEBUG"

# --- Performance Settings ---
# Only log positive matches to reduce API calls and log volume
LOG_ONLY_MATCHES = True

# Timeout for API calls (seconds)
API_TIMEOUT = 10

# Maximum image size for API calls (to reduce costs)
MAX_IMAGE_SIZE = (800, 600)

# --- Feature Flags ---
ENABLE_LLM_LOGGING = True  # Set to False to disable LLM integration entirely
ENABLE_JSON_PARSING = True  # Try to parse JSON responses
ENABLE_FALLBACK_PARSING = True  # Use fallback parsing if JSON fails

# --- Prompt Templates ---
TEMPLATE_MATCHING_PROMPT = """You are analyzing a screenshot from the Azur Lane mobile game to find a specific UI element.

TASK: Determine if the template image (second image) appears in the screenshot (first image).

Template name: {template_name}

Please analyze both images and respond with:
1. Whether the template is found (true/false)
2. If found, the approximate bounding box coordinates [x1, y1, x2, y2]
3. Confidence level (0.0 to 1.0)
4. Brief explanation of what you see

Format your response as JSON:
{{"found": boolean, "bounding_box": [x1, y1, x2, y2], "confidence": float, "explanation": "string"}}"""

# --- Error Messages ---
ERROR_NO_API_KEY = "GOOGLE_API_KEY not found in environment variables"
ERROR_MISSING_DEPS = "google-generativeai package not installed. Run: pip install google-generativeai"