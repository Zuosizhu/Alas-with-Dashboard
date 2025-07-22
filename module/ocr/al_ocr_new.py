"""
Flexible OCR implementation for ALAS.
Tries multiple OCR backends in order of preference.
"""
import numpy as np
from typing import List, Optional
from module.logger import logger

# Try to import OCR backends in order of preference
OCR_BACKEND = None
OCR_NAME = "none"

# Try EasyOCR first (best for game text)
try:
    import easyocr
    _reader = None
    
    def get_easyocr_reader():
        global _reader
        if _reader is None:
            logger.info("Initializing EasyOCR (first time may download models)...")
            _reader = easyocr.Reader(['en', 'ja', 'ch_sim', 'ch_tra'], gpu=False)
            logger.info("EasyOCR initialized successfully")
        return _reader
    
    OCR_BACKEND = "easyocr"
    OCR_NAME = "EasyOCR"
    logger.info("OCR backend: EasyOCR available")
except ImportError:
    pass

# Try Tesseract second
if OCR_BACKEND is None:
    try:
        from module.ocr.tesseract_backend import TesseractBackend
        if TesseractBackend.TESSERACT_AVAILABLE:
            OCR_BACKEND = "tesseract"
            OCR_NAME = "Tesseract"
            logger.info("OCR backend: Tesseract available")
    except:
        pass

# Fall back to simple OCR
if OCR_BACKEND is None:
    from module.ocr.simple_ocr import SimpleOCR
    OCR_BACKEND = "simple"
    OCR_NAME = "SimpleOCR (placeholder)"
    logger.warning("No OCR backend available, using placeholder")


class AlOcr:
    """
    Unified OCR interface that uses the best available backend.
    """
    
    def __init__(self,
                 model_name='densenet-lite-gru',
                 model_epoch=None,
                 cand_alphabet=None,
                 root=None,
                 context='cpu',
                 name=None):
        """
        Initialize OCR with the best available backend.
        
        Args:
            name: Language/model name (azur_lane, jp, tw, cnocr, etc.)
        """
        self.name = name or 'azur_lane'
        self.cand_alphabet = cand_alphabet
        self.backend = OCR_BACKEND
        
        # Initialize appropriate backend
        if self.backend == "tesseract":
            from module.ocr.tesseract_backend import TesseractBackend
            self._impl = TesseractBackend(
                model_name=model_name,
                model_epoch=model_epoch,
                cand_alphabet=cand_alphabet,
                root=root,
                context=context,
                name=name
            )
        elif self.backend == "simple":
            from module.ocr.simple_ocr import SimpleOCR
            self._impl = SimpleOCR(name=name)
        
        logger.info(f"AlOcr initialized with {OCR_NAME} for {self.name}")
    
    def ocr(self, image: np.ndarray) -> str:
        """
        Perform OCR on image.
        
        Args:
            image: numpy array of image
            
        Returns:
            Recognized text string
        """
        if self.backend == "easyocr":
            try:
                reader = get_easyocr_reader()
                if isinstance(image, np.ndarray):
                    results = reader.readtext(image, detail=0)
                    return " ".join(results) if results else ""
                return ""
            except Exception as e:
                logger.warning(f"EasyOCR failed: {e}")
                return ""
        else:
            return self._impl.ocr(image)
    
    def ocr_for_single_line(self, image: np.ndarray) -> str:
        """Optimized OCR for single line text"""
        return self.ocr(image)
    
    def ocr_for_single_lines(self, images: List[np.ndarray]) -> List[str]:
        """OCR multiple single-line images"""
        return [self.ocr(img) for img in images]
    
    def atomic_ocr_for_single_lines(self, images: List[np.ndarray], alphabet: Optional[str] = None) -> List[List[str]]:
        """
        Atomic OCR matching original interface.
        Returns list of character lists.
        """
        if self.backend == "easyocr":
            results = self.ocr_for_single_lines(images)
            return [list(text) for text in results]
        else:
            return self._impl.atomic_ocr_for_single_lines(images, alphabet)
    
    def set_cand_alphabet(self, alphabet: Optional[str]):
        """Set character whitelist"""
        self.cand_alphabet = alphabet
        if self.backend != "easyocr":
            self._impl.set_cand_alphabet(alphabet)
    
    def atomic_ocr(self, image: np.ndarray, alphabet: Optional[str] = None) -> str:
        """Atomic OCR with temporary alphabet"""
        if alphabet and self.backend != "easyocr":
            return self._impl.atomic_ocr(image, alphabet)
        return self.ocr(image)
    
    def atomic_ocr_for_single_line(self, image: np.ndarray, alphabet: Optional[str] = None) -> str:
        """Atomic single-line OCR"""
        return self.atomic_ocr(image, alphabet)
    
    def debug(self, images: List[np.ndarray]):
        """Debug OCR by printing results for each image"""
        logger.info(f"Debug: Processing {len(images)} images with {OCR_NAME}")
        if self.backend == "easyocr":
            for i, img in enumerate(images):
                result = self.ocr(img)
                logger.info(f"Image {i}: '{result}'")
        else:
            self._impl.debug(images)