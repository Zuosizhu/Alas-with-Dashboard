import logging
import threading
import time
import cv2
import base64
import os
import numpy as np

# Import configuration
try:
    from config.vision_llm_config import *
except ImportError:
    # Fallback configuration if config file not available
    GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
    GEMINI_MODEL = "gemini-2.5-flash"
    VISION_LOG_FILE = "logs/vision_llm.log"
    LOG_LEVEL = "DEBUG"
    LOG_ONLY_MATCHES = True
    API_TIMEOUT = 10
    MAX_IMAGE_SIZE = (800, 600)
    ENABLE_LLM_LOGGING = True
    ENABLE_JSON_PARSING = True
    ENABLE_FALLBACK_PARSING = True
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
    ERROR_NO_API_KEY = "GOOGLE_API_KEY not found in environment variables"
    ERROR_MISSING_DEPS = "google-generativeai package not installed. Run: pip install google-generativeai"

# --- Logger Configuration ---
# Ensure logs directory exists
os.makedirs('logs', exist_ok=True)

# A dedicated logger for the vision model's analysis
vision_logger = logging.getLogger('vision_llm')
vision_logger.setLevel(getattr(logging, LOG_LEVEL))
# Create file handler
fh = logging.FileHandler(VISION_LOG_FILE)
fh.setLevel(getattr(logging, LOG_LEVEL))
# Create formatter and add it to the handlers
formatter = logging.Formatter('%(asctime)s - %(message)s')
fh.setFormatter(formatter)
vision_logger.addHandler(fh)

# --- LLM Interaction (Gemini Flash 2.5) ---
def call_vision_model(screen_b64, template_b64, template_name):
    """
    Call Gemini Flash 2.5 vision model to analyze template matching.
    """
    try:
        import google.generativeai as genai

        # Check API key
        if not GOOGLE_API_KEY:
            vision_logger.warning(ERROR_NO_API_KEY)
            return {'error': 'No API key', 'model': GEMINI_MODEL}

        # Configure API key
        genai.configure(api_key=GOOGLE_API_KEY)
        
        # Decode base64 images
        screen_bytes = base64.b64decode(screen_b64)
        template_bytes = base64.b64decode(template_b64)
        
        # Resize images if too large (to reduce API costs)
        screen_img = cv2.imdecode(np.frombuffer(screen_bytes, np.uint8), cv2.IMREAD_COLOR)
        if screen_img.shape[1] > MAX_IMAGE_SIZE[0] or screen_img.shape[0] > MAX_IMAGE_SIZE[1]:
            screen_img = cv2.resize(screen_img, MAX_IMAGE_SIZE)
            _, screen_buffer = cv2.imencode('.png', screen_img)
            screen_bytes = screen_buffer.tobytes()
        
        template_img = cv2.imdecode(np.frombuffer(template_bytes, np.uint8), cv2.IMREAD_COLOR)
        if template_img.shape[1] > MAX_IMAGE_SIZE[0] or template_img.shape[0] > MAX_IMAGE_SIZE[1]:
            template_img = cv2.resize(template_img, MAX_IMAGE_SIZE)
            _, template_buffer = cv2.imencode('.png', template_img)
            template_bytes = template_buffer.tobytes()
        
        # Create PIL Images from bytes for Gemini
        import io
        from PIL import Image
        
        screen_image = Image.open(io.BytesIO(screen_bytes))
        template_image = Image.open(io.BytesIO(template_bytes))
        
        # Use configured prompt template
        prompt = TEMPLATE_MATCHING_PROMPT.format(template_name=template_name)
        
        # Create model instance
        model = genai.GenerativeModel(GEMINI_MODEL)
        
        # Make API call
        response = model.generate_content([prompt, screen_image, template_image])
        
        # Parse response
        if ENABLE_JSON_PARSING:
            try:
                import json
                result = json.loads(response.text.strip())
                result['model'] = GEMINI_MODEL
                return result
            except json.JSONDecodeError:
                if not ENABLE_FALLBACK_PARSING:
                    return {'error': 'JSON parsing failed', 'model': GEMINI_MODEL}
        
        # Fallback parsing if JSON fails or is disabled
        return {
            'found': 'found' in response.text.lower() or 'detected' in response.text.lower(),
            'bounding_box': None,
            'confidence': 0.5,
            'explanation': response.text[:200],
            'model': GEMINI_MODEL
        }
            
    except ImportError:
        vision_logger.warning(ERROR_MISSING_DEPS)
        return {'error': 'Missing dependencies', 'model': GEMINI_MODEL}
    except Exception as e:
        vision_logger.error(f"Gemini API call failed for template '{template_name}': {e}")
        return {'error': str(e), 'model': GEMINI_MODEL}

# --- Core Logging Function ---
def _log_vision_task(screen_image, template_image, template_name, traditional_result):
    """
    The core task that runs in a separate thread.
    """
    try:
        # 1. Encode images to base64
        _, screen_buffer = cv2.imencode('.png', screen_image)
        screen_b64 = base64.b64encode(screen_buffer).decode('utf-8')

        _, template_buffer = cv2.imencode('.png', template_image)
        template_b64 = base64.b64encode(template_buffer).decode('utf-8')

        # 2. Call the vision model
        llm_result = call_vision_model(screen_b64, template_b64, template_name)

        # 3. Log results
        log_entry = {
            'timestamp': time.time(),
            'template_name': template_name,
            'traditional_system': traditional_result,
            'llm_system': llm_result
        }
        vision_logger.info(log_entry)

    except Exception as e:
        vision_logger.error(f"Error in vision logging for {template_name}: {e}")

def log_vision_comparison(screen_image, template_image, template_name, traditional_result):
    """
    Public function to be called from the main application.
    Starts the logging task in a new thread to avoid blocking.
    """
    # Check if LLM logging is enabled
    if not ENABLE_LLM_LOGGING:
        return
    
    # Check if we should only log matches
    if LOG_ONLY_MATCHES and not traditional_result.get('matched', False):
        return
    
    thread = threading.Thread(
        target=_log_vision_task,
        args=(screen_image, template_image, template_name, traditional_result)
    )
    thread.daemon = True # Allows main program to exit even if threads are running
    thread.start()
