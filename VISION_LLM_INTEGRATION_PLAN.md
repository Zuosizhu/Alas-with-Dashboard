# Vision LLM Integration Plan

This document outlines a plan to integrate a parallel LLM-based vision system into ALAS for evaluation purposes. The goal is to log the results of the LLM alongside the existing template matching system without interfering with the bot's core functionality.

## 1. New Module: `vision_llm.py`

A new module will be created to encapsulate all logic related to the LLM interaction.

**File:** `c:/_Development/ALAS/module/vision_llm.py`

```python
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

```

## 2. Integration into `template.py`

The `Template` class in `module/base/template.py` will be modified to call the new logging function.

**File:** `c:/_Development/ALAS/module/base/template.py`

### Proposed changes for `match` method:

```python
    def match(self, image, scaling=1.0, similarity=0.85):
        # ... existing code ...
        res = cv2.matchTemplate(image, self.image, cv2.TM_CCOEFF_NORMED)
        _, sim, _, _ = cv2.minMaxLoc(res)
        result = sim > similarity

        # --- START: New Vision LLM Logging ---
        try:
            from module.vision_llm import log_vision_comparison
            if result: # Log only positive matches to start
                template_image = self.image[0] if self.is_gif else self.image
                log_vision_comparison(
                    screen_image=image,
                    template_image=template_image,
                    template_name=self.name,
                    traditional_result={'matched': True, 'similarity': round(sim, 4), 'method': 'match'}
                )
        except Exception as e:
            from module.logger import logger
            logger.warning(f"Vision LLM logging failed: {e}")
        # --- END: New Vision LLM Logging ---

        return result
```

### Proposed changes for `match_binary` method:

```python
    def match_binary(self, image, similarity=0.85):
        # ... existing code ...
        res = cv2.matchTemplate(self.image_binary, image_binary, cv2.TM_CCOEFF_NORMED)
        _, sim, _, _ = cv2.minMaxLoc(res)
        result = sim > similarity

        # --- START: New Vision LLM Logging ---
        try:
            from module.vision_llm import log_vision_comparison
            if result:
                template_image = self.image[0] if self.is_gif else self.image
                log_vision_comparison(
                    screen_image=image, # Original color image
                    template_image=template_image,
                    template_name=self.name,
                    traditional_result={'matched': True, 'similarity': round(sim, 4), 'method': 'match_binary'}
                )
        except Exception as e:
            from module.logger import logger
            logger.warning(f"Vision LLM logging failed: {e}")
        # --- END: New Vision LLM Logging ---

        return result
```

## 3. Critique

- **Minimal Interference**: The design is highly non-invasive. The new logic is isolated, runs in a non-blocking thread, and is wrapped in error handling to prevent any impact on the bot's stability or performance.
- **Standardization**: Modifying the base `Template` class ensures that every template match across the application is captured, providing a complete dataset for comparison.
- **Flexibility**: The placeholder `call_vision_model` can be easily replaced with a real implementation for any LLM API (Gemma, OpenAI, etc.) without changing the integration points.
