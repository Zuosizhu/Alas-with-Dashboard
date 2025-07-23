import logging
import threading
import time
import cv2
import base64

# --- Configuration ---
# A dedicated logger for the vision model's analysis
vision_logger = logging.getLogger('vision_llm')
vision_logger.setLevel(logging.DEBUG)
# Create file handler
fh = logging.FileHandler('logs/vision_llm.log')
fh.setLevel(logging.DEBUG)
# Create formatter and add it to the handlers
formatter = logging.Formatter('%(asctime)s - %(message)s')
fh.setFormatter(formatter)
vision_logger.addHandler(fh)

# --- LLM Interaction (Placeholder) ---
def call_vision_model(screen_b64, template_b64, template_name):
    """
    Placeholder function to simulate calling a vision LLM.
    In a real implementation, this would make an HTTP request to an LLM API.
    """
    # Simulate network latency
    time.sleep(2)

    # Simulate a response
    # In a real scenario, this would be the actual bounding box and confidence
    response = {
        'found': True, # or False
        'bounding_box': [100, 150, 240, 320], # [x1, y1, x2, y2]
        'confidence': 0.95,
        'model': 'gemma-27b-vision-simulated'
    }
    return response

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
    thread = threading.Thread(
        target=_log_vision_task,
        args=(screen_image, template_image, template_name, traditional_result)
    )
    thread.daemon = True # Allows main program to exit even if threads are running
    thread.start()
