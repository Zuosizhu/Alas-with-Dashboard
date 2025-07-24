#!/usr/bin/env python3
"""
Configuration for Ollama Vision LLM Integration
"""

import os

# Ollama configuration
OLLAMA_API_BASE = "http://localhost:11434"
VISION_MODEL = "llava-phi3"  # Optimized for 4050 Ti
ENABLE_OLLAMA_VISION = True
LOG_ONLY_MATCHES = True

# API settings
API_TIMEOUT = 30.0  # seconds
MAX_IMAGE_SIZE = 800  # pixels
THREAD_TIMEOUT = 35.0  # slightly longer than API timeout

# Log settings
VISION_LOG_FILE = "logs/vision_ollama.log"
LOG_LEVEL = "DEBUG"
ENABLE_LLM_LOGGING = True
ENABLE_JSON_PARSING = True
ENABLE_FALLBACK_PARSING = True