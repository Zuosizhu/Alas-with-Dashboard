#!/usr/bin/env python3
"""Test flexible OCR system"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from module.ocr.models import OCR_MODEL
    from module.ocr.al_ocr import OCR_BACKEND, OCR_NAME
    
    print("="*60)
    print("Flexible OCR System Test")
    print("="*60)
    print(f"Active OCR Backend: {OCR_NAME} ({OCR_BACKEND})")
    print()
    
    # Test basic functionality
    ocr = OCR_MODEL.azur_lane
    print(f"Created azur_lane OCR instance: {ocr}")
    print(f"OCR backend in use: {ocr.backend}")
    
    # Test with None (should return empty string)
    result = ocr.ocr(None)
    print(f"OCR with None input: '{result}' (should be empty)")
    
    print("\nFlexible OCR system is working!")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()