#!/usr/bin/env python3
"""
Test script for Gemini Flash 2.5 vision integration.
This script demonstrates how to test the LLM vision system.

Usage:
1. Set GOOGLE_API_KEY environment variable
2. pip install google-generativeai
3. python test_gemini_vision.py
"""

import os
import sys
import cv2
import numpy as np

# Add module path
sys.path.insert(0, os.path.dirname(__file__))

from module.vision_llm import log_vision_comparison, call_vision_model
from module.logger import logger

def create_test_images():
    """Create simple test images for demonstration"""
    # Create a mock screenshot (blue background with white rectangle)
    screen = np.full((480, 640, 3), (255, 100, 50), dtype=np.uint8)  # Blue background
    cv2.rectangle(screen, (200, 150), (400, 300), (255, 255, 255), -1)  # White rectangle
    cv2.putText(screen, "BUTTON", (250, 230), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
    
    # Create a template (smaller white rectangle with text)
    template = np.full((150, 200, 3), (255, 255, 255), dtype=np.uint8)  # White background
    cv2.putText(template, "BUTTON", (50, 80), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
    
    return screen, template

def test_gemini_vision():
    """Test the Gemini vision integration"""
    logger.info("Testing Gemini Flash 2.5 vision integration...")
    
    # Check if API key is set
    if not os.environ.get("GOOGLE_API_KEY"):
        logger.warning("GOOGLE_API_KEY not set. This test will demonstrate error handling.")
    
    # Create test images
    screen_img, template_img = create_test_images()
    
    # Save test images for reference
    cv2.imwrite("logs/test_screen.png", screen_img)
    cv2.imwrite("logs/test_template.png", template_img)
    logger.info("Test images saved to logs/test_screen.png and logs/test_template.png")
    
    # Simulate traditional template matching result
    traditional_result = {
        'matched': True,
        'similarity': 0.95,
        'method': 'test'
    }
    
    # Test the vision comparison system
    logger.info("Calling log_vision_comparison...")
    log_vision_comparison(
        screen_image=screen_img,
        template_image=template_img,
        template_name="TEST_BUTTON",
        traditional_result=traditional_result
    )
    
    # Direct API test
    logger.info("Testing direct API call...")
    import base64
    _, screen_buffer = cv2.imencode('.png', screen_img)
    screen_b64 = base64.b64encode(screen_buffer).decode('utf-8')
    
    _, template_buffer = cv2.imencode('.png', template_img)
    template_b64 = base64.b64encode(template_buffer).decode('utf-8')
    
    result = call_vision_model(screen_b64, template_b64, "TEST_BUTTON")
    logger.info(f"Direct API result: {result}")
    
    logger.info("Test completed. Check logs/vision_llm.log for LLM analysis results.")

if __name__ == "__main__":
    # Ensure logs directory exists
    os.makedirs('logs', exist_ok=True)
    
    test_gemini_vision()
    
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    print("1. Test images created and saved to logs/")
    print("2. LLM vision comparison system tested")
    print("3. Check logs/vision_llm.log for detailed results")
    print("4. To use with real API:")
    print("   - Set GOOGLE_API_KEY environment variable")
    print("   - Install: pip install google-generativeai")
    print("="*60)