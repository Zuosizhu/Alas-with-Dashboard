"""
Simplified OCR implementation for ALAS.
This provides a minimal working OCR that can be replaced with better solutions later.
"""
import numpy as np
import re
from typing import List, Optional, Union
from module.logger import logger


class SimpleOCR:
    """
    Minimal OCR implementation that provides basic functionality.
    Can be replaced with EasyOCR, Tesseract, or vision models later.
    """
    
    def __init__(self, name: str = 'azur_lane'):
        self.name = name
        self.patterns = {
            # Common game patterns
            'stage': re.compile(r'STAGE\s*\d+-\d+'),
            'time': re.compile(r'\d{1,2}:\d{2}:\d{2}'),
            'percentage': re.compile(r'\d{1,3}%'),
            'number': re.compile(r'\d+'),
            'duration': re.compile(r'\d{1,2}h\s*\d{1,2}m'),
        }
        logger.info(f"SimpleOCR initialized for {name}")
    
    def ocr(self, image: np.ndarray) -> str:
        """
        Simplified OCR that returns empty string.
        This allows ALAS to run without OCR while we implement better solution.
        """
        # For now, return empty string to avoid breaking ALAS
        # This will be replaced with actual OCR implementation
        return ""
    
    def ocr_for_single_line(self, image: np.ndarray) -> str:
        """Single line OCR"""
        return self.ocr(image)
    
    def ocr_for_single_lines(self, images: List[np.ndarray]) -> List[str]:
        """Multiple single line OCR"""
        return [self.ocr(img) for img in images]
    
    def atomic_ocr_for_single_lines(self, images: List[np.ndarray], alphabet: Optional[str] = None) -> List[List[str]]:
        """Atomic OCR returning character lists"""
        results = self.ocr_for_single_lines(images)
        return [list(text) for text in results]
    
    def set_cand_alphabet(self, alphabet: Optional[str]):
        """Set character whitelist (no-op for simple OCR)"""
        pass
    
    def atomic_ocr(self, image: np.ndarray, alphabet: Optional[str] = None) -> str:
        """Atomic OCR with alphabet"""
        return self.ocr(image)
    
    def atomic_ocr_for_single_line(self, image: np.ndarray, alphabet: Optional[str] = None) -> str:
        """Atomic single line OCR"""
        return self.ocr(image)
    
    def debug(self, images: List[np.ndarray]):
        """Debug OCR"""
        logger.info(f"SimpleOCR debug: {len(images)} images")
        for i, img in enumerate(images):
            result = self.ocr(img)
            logger.info(f"  Image {i}: '{result}'")