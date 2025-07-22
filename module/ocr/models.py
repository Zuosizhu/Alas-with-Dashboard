"""
OCR models for different languages and use cases.
Provides cached OCR instances using EasyOCR backend.
"""
from module.base.decorator import cached_property


class OcrModel:
    """Factory for OCR models using EasyOCR backend."""
    
    @cached_property
    def azur_lane(self):
        """English OCR for Azur Lane"""
        # Original: densenet-lite-gru, 99.43% accuracy
        # Charset: 0123456789ABCDEFGHIJKLMNPQRSTUVWXYZ:/- 
        from module.ocr.al_ocr import AlOcr
        return AlOcr(name='azur_lane')

    @cached_property
    def azur_lane_jp(self):
        """Japanese/English OCR for Azur Lane"""
        # Original: densenet-lite-gru, 99.38% accuracy
        from module.ocr.al_ocr import AlOcr
        return AlOcr(name='azur_lane_jp')

    @cached_property
    def cnocr(self):
        """Chinese Simplified OCR"""
        # Original: densenet-lite-gru, 99.04% accuracy
        # Charset: Number, English, Chinese, symbols, <space>
        from module.ocr.al_ocr import AlOcr
        return AlOcr(name='cnocr')

    @cached_property
    def jp(self):
        """Japanese OCR"""
        from module.ocr.al_ocr import AlOcr
        return AlOcr(name='jp')

    @cached_property
    def tw(self):
        """Traditional Chinese OCR"""
        # Original: densenet-lite-gru, 99.24% accuracy
        # Charset: Numbers, Upper English, Chinese traditional
        from module.ocr.al_ocr import AlOcr
        return AlOcr(name='tw')


OCR_MODEL = OcrModel()
