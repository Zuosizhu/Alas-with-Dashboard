import argparse
import multiprocessing
import pickle

from module.logger import logger
from module.webui.setting import State

process: multiprocessing.Process = None


class ModelProxy:
    """Proxy for OCR models (deprecated)"""

    client = None
    online = False  # Always offline since OCR is removed

    @classmethod
    def init(cls, address="127.0.0.1:22268"):
        """Initialize connection to OCR server (deprecated)"""
        logger.warning("OCR server functionality has been removed")
        cls.online = False

    @classmethod
    def close(cls):
        """Close connection to OCR server (deprecated)"""
        if cls.client is not None:
            cls.client = None

    def __init__(self, lang) -> None:
        self.lang = lang

    def ocr(self, img_fp):
        """OCR functionality is deprecated and will be removed."""
        logger.warning("OCR functionality has been removed. Returning empty result.")
        return ""

    def ocr_for_single_line(self, img_fp):
        """OCR functionality is deprecated and will be removed."""
        logger.warning("OCR functionality has been removed. Returning empty result.")
        return ""

    def ocr_for_single_lines(self, img_list):
        """OCR functionality is deprecated and will be removed."""
        logger.warning("OCR functionality has been removed. Returning empty results.")
        return [""] * len(img_list) if isinstance(img_list, list) else ""


class ModelProxyFactory:
    """Factory for creating ModelProxy instances"""

    def __getattr__(self, name):
        return ModelProxy(name)


def start_ocr_server(port=22268):
    """OCR server functionality has been removed"""
    logger.error("OCR server functionality has been removed")
    return


def start_ocr_server_process(port=22268):
    """OCR server functionality has been removed"""
    logger.error("OCR server functionality has been removed")
    return


def stop_ocr_server_process():
    """OCR server functionality has been removed"""
    global process
    if process is not None:
        process = None


def alive() -> bool:
    """OCR server is never alive"""
    return False


if __name__ == "__main__":
    # Run server
    parser = argparse.ArgumentParser(description="Alas OCR service (deprecated)")
    parser.add_argument(
        "--port",
        type=int,
        help="Port to listen. Default to OcrServerPort in deploy setting",
    )
    args, _ = parser.parse_known_args()
    logger.error("OCR server functionality has been removed")
