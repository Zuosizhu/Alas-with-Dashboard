"""
Tesseract OCR backend for ALAS
Drop-in replacement for the original cnocr-based OCR
"""
import os
import warnings
from typing import List, Optional, Union

import cv2
import numpy as np

# Try to import pytesseract, provide helpful error if not available
try:
    import pytesseract
except ImportError:
    raise ImportError(
        "pytesseract not installed. Please run: pip install pytesseract\n"
        "Also ensure Tesseract executable is installed: https://github.com/UB-Mannheim/tesseract/wiki"
    )

from module.logger import logger
from module.base.utils import extract_letters


class TesseractBackend:
    """
    Tesseract-based OCR backend that matches the AlOcr interface
    """
    
    # Check if Tesseract executable is available
    TESSERACT_AVAILABLE = False
    try:
        pytesseract.get_tesseract_version()
        TESSERACT_AVAILABLE = True
    except:
        logger.warning("Tesseract executable not found. Please install Tesseract OCR.")
    
    def __init__(self, 
                 model_name: str = 'densenet-lite-gru',
                 model_epoch: Optional[int] = None,
                 cand_alphabet: Optional[str] = None,
                 root: Optional[str] = None,
                 context: str = 'cpu',
                 name: Optional[str] = None):
        """
        Initialize Tesseract backend with AlOcr-compatible interface
        
        Args:
            model_name: Ignored, kept for compatibility
            model_epoch: Ignored, kept for compatibility
            cand_alphabet: Character whitelist
            root: Ignored, kept for compatibility
            context: Ignored, kept for compatibility
            name: Language name (azur_lane, jp, tw, cnocr, etc.)
        """
        self.name = name or 'azur_lane'
        self.cand_alphabet = cand_alphabet
        
        # Map ALAS language names to Tesseract language codes
        self.lang_map = {
            'azur_lane': 'eng',
            'azur_lane_jp': 'jpn+eng',
            'cnocr': 'chi_sim+eng',
            'jp': 'jpn',
            'tw': 'chi_tra+eng'
        }
        
        self.lang = self.lang_map.get(self.name, 'eng')
        self._config = self._build_config()
        
        if self.TESSERACT_AVAILABLE:
            logger.info(f"Tesseract OCR initialized for language: {self.name} ({self.lang})")
        else:
            logger.error("Tesseract not available. OCR will return empty results.")
    
    def _build_config(self, custom_whitelist: Optional[str] = None) -> str:
        """Build Tesseract configuration string"""
        config_parts = []
        
        # Page segmentation mode
        # 7 = Treat image as single text line
        # 8 = Treat image as single word
        # 11 = Sparse text. Find as much text as possible in no particular order
        config_parts.append('--psm 7')
        
        # OCR Engine Mode
        # 3 = Default, based on what is available
        config_parts.append('--oem 3')
        
        # Character whitelist
        whitelist = custom_whitelist or self.cand_alphabet
        if whitelist:
            # Escape special characters for Tesseract
            whitelist = whitelist.replace('-', '\\-')
            config_parts.append(f'-c tessedit_char_whitelist={whitelist}')
        
        return ' '.join(config_parts)
    
    def _preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """
        Preprocess image for better OCR results
        
        Args:
            image: Input image (can be BGR or grayscale)
            
        Returns:
            Preprocessed grayscale image
        """
        # Validate input
        if image is None or image.size == 0:
            return image
            
        # Convert to grayscale if needed
        if len(image.shape) == 3:
            image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Get image dimensions
        height, width = image.shape
        
        # Scale up small images (Tesseract works better with larger text)
        min_height = 32
        if height < min_height:
            scale_factor = min_height / height
            new_width = int(width * scale_factor)
            image = cv2.resize(image, (new_width, min_height), interpolation=cv2.INTER_CUBIC)
        
        # Apply threshold to get binary image
        # Use Otsu's method to automatically determine threshold
        _, binary = cv2.threshold(image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Check if image is mostly white text on dark background
        white_pixels = np.sum(binary == 255)
        total_pixels = binary.size
        if white_pixels < total_pixels * 0.5:
            # Invert if text is white on dark background
            binary = cv2.bitwise_not(binary)
        
        # Add small border to help OCR
        border_size = 5
        binary = cv2.copyMakeBorder(
            binary, 
            border_size, border_size, border_size, border_size,
            cv2.BORDER_CONSTANT, 
            value=255
        )
        
        return binary
    
    def ocr(self, img_fp: np.ndarray) -> str:
        """
        Perform OCR on image
        
        Args:
            img_fp: Image as numpy array
            
        Returns:
            Recognized text string
        """
        if not self.TESSERACT_AVAILABLE:
            return ""
        
        # Input validation
        if img_fp is None:
            return ""
        if not isinstance(img_fp, np.ndarray):
            logger.warning(f"Tesseract OCR received non-numpy array: {type(img_fp)}")
            return ""
        if img_fp.size == 0:
            return ""
        
        try:
            # Preprocess image
            processed = self._preprocess_image(img_fp)
            
            # Run OCR
            text = pytesseract.image_to_string(
                processed,
                lang=self.lang,
                config=self._config
            )
            
            # Clean up result
            text = text.strip()
            
            # Remove common OCR artifacts
            text = text.replace('\n', ' ')
            text = text.replace('\x0c', '')  # Form feed character
            
            return text
            
        except Exception as e:
            logger.warning(f"Tesseract OCR failed: {str(e)}")
            return ""
    
    def ocr_for_single_line(self, img_fp: np.ndarray) -> str:
        """
        Optimized OCR for single line text
        
        Args:
            img_fp: Image containing single line of text
            
        Returns:
            Recognized text string
        """
        # Use PSM 7 for single line (already default)
        return self.ocr(img_fp)
    
    def ocr_for_single_lines(self, img_list: List[np.ndarray]) -> List[str]:
        """
        OCR multiple single-line images
        
        Args:
            img_list: List of images
            
        Returns:
            List of recognized text strings
        """
        return [self.ocr_for_single_line(img) for img in img_list]
    
    def set_cand_alphabet(self, cand_alphabet: Optional[str]):
        """
        Set character whitelist
        
        Args:
            cand_alphabet: String of allowed characters
        """
        self.cand_alphabet = cand_alphabet
        self._config = self._build_config()
    
    def atomic_ocr(self, img_fp: np.ndarray, cand_alphabet: Optional[str] = None) -> str:
        """
        Atomic OCR operation with temporary alphabet override
        
        Args:
            img_fp: Image to OCR
            cand_alphabet: Temporary character whitelist
            
        Returns:
            Recognized text
        """
        if cand_alphabet:
            old_alphabet = self.cand_alphabet
            old_config = self._config
            
            self.cand_alphabet = cand_alphabet
            self._config = self._build_config()
            
            result = self.ocr(img_fp)
            
            # Restore original settings
            self.cand_alphabet = old_alphabet
            self._config = old_config
            
            return result
        else:
            return self.ocr(img_fp)
    
    def atomic_ocr_for_single_line(self, img_fp: np.ndarray, cand_alphabet: Optional[str] = None) -> str:
        """
        Atomic single-line OCR with temporary alphabet override
        """
        return self.atomic_ocr(img_fp, cand_alphabet)
    
    def atomic_ocr_for_single_lines(self, img_list: List[np.ndarray], cand_alphabet: Optional[str] = None) -> List[List[str]]:
        """
        Atomic OCR for multiple images, returning results as character lists
        
        This matches the original AlOcr interface which returns list of character lists
        
        Args:
            img_list: List of images
            cand_alphabet: Character whitelist
            
        Returns:
            List of character lists (e.g., [['H','e','l','l','o'], ['W','o','r','l','d']])
        """
        if cand_alphabet:
            old_alphabet = self.cand_alphabet
            old_config = self._config
            
            self.cand_alphabet = cand_alphabet
            self._config = self._build_config()
            
            # Get text results
            text_results = self.ocr_for_single_lines(img_list)
            
            # Convert to character lists to match original interface
            char_results = [list(text) for text in text_results]
            
            # Restore original settings
            self.cand_alphabet = old_alphabet
            self._config = old_config
            
            return char_results
        else:
            text_results = self.ocr_for_single_lines(img_list)
            return [list(text) for text in text_results]
    
    def debug(self, img_list: List[np.ndarray]):
        """
        Debug method to visualize what's being sent to OCR
        
        Args:
            img_list: List of images to debug
        """
        logger.info(f"Debug: Processing {len(img_list)} images with Tesseract")
        
        # Could save images for debugging if needed
        debug_dir = './log/ocr_debug'
        if not os.path.exists(debug_dir):
            os.makedirs(debug_dir, exist_ok=True)
        
        for i, img in enumerate(img_list):
            # Save preprocessed image
            processed = self._preprocess_image(img)
            debug_path = os.path.join(debug_dir, f'debug_{i}.png')
            cv2.imwrite(debug_path, processed)
            
            # Try OCR and log result
            result = self.ocr(img)
            logger.info(f"Image {i}: '{result}'")


# Convenience class that exactly matches AlOcr interface
class AlOcr(TesseractBackend):
    """Direct replacement for the original AlOcr class"""
    pass