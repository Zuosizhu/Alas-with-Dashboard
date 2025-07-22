"""
Tesseract-based OCR implementation for ALAS.
Drop-in replacement for the original cnocr-based OCR.
"""
import numpy as np
from module.logger import logger

# Import our Tesseract backend
try:
    from module.ocr.tesseract_backend import TesseractBackend
    OCR_AVAILABLE = TesseractBackend.TESSERACT_AVAILABLE
except ImportError:
    logger.warning("Tesseract backend not available")
    OCR_AVAILABLE = False


class AlOcr(TesseractBackend if OCR_AVAILABLE else object):
    """
    Tesseract-based OCR that matches the original AlOcr interface.
    Inherits from TesseractBackend for full functionality.
    """
    
    def __init__(self,
                 model_name='densenet-lite-gru',
                 model_epoch=None,
                 cand_alphabet=None,
                 root=None,
                 context='cpu',
                 name=None):
        """
        Initialize OCR instance.
        
        Args:
            name: Language/model name (azur_lane, jp, tw, cnocr, etc.)
        """
        if OCR_AVAILABLE:
            # Initialize parent TesseractBackend
            super().__init__(
                model_name=model_name,
                model_epoch=model_epoch,
                cand_alphabet=cand_alphabet,
                root=root,
                context=context,
                name=name
            )
        else:
            self.name = name or 'azur_lane'
            self.cand_alphabet = cand_alphabet
            logger.warning("OCR not available - Tesseract not installed")
    
    # If Tesseract not available, provide stub methods
    if not OCR_AVAILABLE:
        def ocr(self, image):
            """Stub OCR method when Tesseract not available"""
            return ""
        
        def ocr_for_single_line(self, image):
            """Stub single line OCR"""
            return ""
        
        def ocr_for_single_lines(self, images):
            """Stub multiple OCR"""
            return ["" for _ in images]
        
        def atomic_ocr_for_single_lines(self, images, alphabet=None):
            """Stub atomic OCR"""
            return [[] for _ in images]
        
        def set_cand_alphabet(self, alphabet):
            """Stub alphabet setter"""
            self.cand_alphabet = alphabet
        
        def atomic_ocr(self, image, alphabet=None):
            """Stub atomic OCR"""
            return ""
        
        def atomic_ocr_for_single_line(self, image, alphabet=None):
            """Stub atomic single line OCR"""
            return ""
        
        def debug(self, images):
            """Stub debug method"""
            logger.warning("OCR debug not available - Tesseract not installed")
