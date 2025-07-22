#!/usr/bin/env python3
"""
Simple test script to verify OCR functionality without logger
"""
import numpy as np
from PIL import Image, ImageDraw
import os
import sys

# Add module to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def create_test_image(text="TEST 123", width=200, height=50):
    """Create a simple test image with text"""
    # Create white image
    img = Image.new('RGB', (width, height), color='white')
    draw = ImageDraw.Draw(img)
    
    # Draw black text with default font
    draw.text((10, 10), text, fill='black')
    
    # Convert to numpy array
    return np.array(img)


def test_tesseract_direct():
    """Test Tesseract directly"""
    print("Testing Tesseract directly...")
    
    try:
        import pytesseract
        
        # Create test image
        img = create_test_image("HELLO WORLD")
        
        # Try OCR
        text = pytesseract.image_to_string(img)
        print(f"Direct Tesseract result: '{text.strip()}'")
        
        # Check version
        version = pytesseract.get_tesseract_version()
        print(f"Tesseract version: {version}")
        
    except Exception as e:
        print(f"Tesseract error: {e}")
        return False
    
    return True


def test_ocr_module():
    """Test our OCR module"""
    print("\nTesting OCR module...")
    
    try:
        # Import directly to avoid logger issues
        from module.ocr.al_ocr import AlOcr
        
        # Create OCR instance
        ocr = AlOcr(name='azur_lane')
        
        # Create test image
        img = create_test_image("TEST 123")
        
        # Try OCR
        result = ocr.ocr(img)
        print(f"AlOcr result: '{result}'")
        
        # Test multiple images
        images = [
            create_test_image("HELLO"),
            create_test_image("WORLD"),
            create_test_image("12345")
        ]
        
        results = ocr.ocr_for_single_lines(images)
        print(f"Multiple OCR results: {results}")
        
    except Exception as e:
        print(f"OCR module error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("="*60)
    print("OCR Simple Test")
    print("="*60)
    
    # Test Tesseract directly
    if test_tesseract_direct():
        # Test our module
        test_ocr_module()
    else:
        print("\nTesseract not available. Please install:")
        print("1. Download from: https://github.com/UB-Mannheim/tesseract/wiki")
        print("2. Install to: C:\\Program Files\\Tesseract-OCR")
        print("3. Add to PATH")