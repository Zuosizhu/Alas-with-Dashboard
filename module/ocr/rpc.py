import argparse
import multiprocessing
import pickle

from module.logger import logger
from module.webui.setting import State

process: multiprocessing.Process = None


class ModelProxy:
    client = None
    online = True

    @classmethod
    def init(cls, address="127.0.0.1:22268"):
        import zerorpc

        cls.online = True
        logger.info(f"Connecting to OCR server {address}")
        cls.client = zerorpc.Client(timeout=5)
        cls.client.connect(f"tcp://{address}")
        try:
            cls.client.hello()
            logger.info("Successfully connected to OCR server")
        except:
            cls.online = False
            logger.warning("Ocr server not running")
            try:
                cls.client.close()
            except Exception:
                pass
            cls.client = None

    @classmethod
    def close(cls):
        if cls.client is not None:
            logger.info('Disconnect to OCR server')
            cls.client.close()
            logger.info('Successfully disconnected to OCR server')
            cls.client = None

    def __init__(self, lang) -> None:
        self.lang = lang

    def _ensure_online(self):
        if not self.online:
            raise RuntimeError("OCR server not running")

    def ocr(self, img_fp):
        """
        Args:
            img_fp (np.ndarray):

        Returns:

        """
        if self.online:
            img_str = img_fp.dumps()
            try:
                return self.client("ocr", self.lang, img_str)
            except:
                self.online = False
        self._ensure_online()

    def ocr_for_single_line(self, img_fp):
        """
        Args:
            img_fp (np.ndarray):

        Returns:

        """
        if self.online:
            img_str = img_fp.dumps()
            try:
                return self.client("ocr_for_single_line", self.lang, img_str)
            except:
                self.online = False
        self._ensure_online()

    def ocr_for_single_lines(self, img_list):
        """
        Args:
            img_list (list[np.ndarray]):

        Returns:

        """
        if self.online:
            img_str_list = [img_fp.dumps() for img_fp in img_list]
            try:
                return self.client("ocr_for_single_lines", self.lang, img_str_list)
            except:
                self.online = False
        self._ensure_online()

    def set_cand_alphabet(self, cand_alphabet: str):
        if self.online:
            try:
                return self.client("set_cand_alphabet", self.lang, cand_alphabet)
            except:
                self.online = False
        self._ensure_online()

    def atomic_ocr(self, img_fp, cand_alphabet=None):
        """
        Args:
            img_fp (np.ndarray):
            cand_alphabet:

        Returns:

        """
        if self.online:
            img_str = img_fp.dumps()
            try:
                return self.client("atomic_ocr", self.lang, img_str, cand_alphabet)
            except:
                self.online = False
        self._ensure_online()

    def atomic_ocr_for_single_line(self, img_fp, cand_alphabet=None):
        """
        Args:
            img_fp (np.ndarray):
            cand_alphabet:

        Returns:

        """
        if self.online:
            img_str = img_fp.dumps()
            try:
                return self.client("atomic_ocr_for_single_line", self.lang, img_str, cand_alphabet)
            except:
                self.online = False
        self._ensure_online()

    def atomic_ocr_for_single_lines(self, img_list, cand_alphabet=None):
        """
        Args:
            img_list (list[np.ndarray]):
            cand_alphabet:

        Returns:

        """
        if self.online:
            img_str_list = [img_fp.dumps() for img_fp in img_list]
            try:
                return self.client("atomic_ocr_for_single_lines", self.lang, img_str_list, cand_alphabet)
            except:
                self.online = False
        self._ensure_online()

    def debug(self, img_list):
        """
        Args:
            img_list (list[np.ndarray]):

        Returns:

        """
        if self.online:
            img_str_list = [img_fp.dumps() for img_fp in img_list]
            try:
                return self.client("debug", self.lang, img_str_list)
            except:
                self.online = False
        self._ensure_online()


class ModelProxyFactory:
    def __getattribute__(self, __name: str) -> ModelProxy:
        if __name in ["azur_lane", "cnocr", "jp", "tw", "azur_lane_jp"]:
            if ModelProxy.client is None or not ModelProxy.online:
                ModelProxy.init(address=State.deploy_config.OcrClientAddress)
            return ModelProxy(lang=__name)
        else:
            return super().__getattribute__(__name)

    def close(self):
        ModelProxy.close()


def start_ocr_server(port=22268):
    import zerorpc
    import zmq
    from module.ocr.al_ocr import AlOcr
    from module.ocr.models import OcrModel

    class OCRServer(OcrModel):
        def hello(self):
            return "hello"

        def ocr(self, lang, img_fp):
            img_fp = pickle.loads(img_fp)
            cnocr: AlOcr = self.__getattribute__(lang)
            return cnocr.ocr(img_fp)

        def ocr_for_single_line(self, lang, img_fp):
            img_fp = pickle.loads(img_fp)
            cnocr: AlOcr = self.__getattribute__(lang)
            return cnocr.ocr_for_single_line(img_fp)

        def ocr_for_single_lines(self, lang, img_list):
            img_list = [pickle.loads(img_fp) for img_fp in img_list]
            cnocr: AlOcr = self.__getattribute__(lang)
            return cnocr.ocr_for_single_lines(img_list)

        def set_cand_alphabet(self, lang, cand_alphabet):
            cnocr: AlOcr = self.__getattribute__(lang)
            return cnocr.set_cand_alphabet(cand_alphabet)

        def atomic_ocr(self, lang, img_fp, cand_alphabet):
            img_fp = pickle.loads(img_fp)
            cnocr: AlOcr = self.__getattribute__(lang)
            return cnocr.atomic_ocr(img_fp, cand_alphabet)

        def atomic_ocr_for_single_line(self, lang, img_fp, cand_alphabet):
            img_fp = pickle.loads(img_fp)
            cnocr: AlOcr = self.__getattribute__(lang)
            return cnocr.atomic_ocr_for_single_line(img_fp, cand_alphabet)

        def atomic_ocr_for_single_lines(self, lang, img_list, cand_alphabet):
            img_list = [pickle.loads(img_fp) for img_fp in img_list]
            cnocr: AlOcr = self.__getattribute__(lang)
            return cnocr.atomic_ocr_for_single_lines(img_list, cand_alphabet)

        def debug(self, lang, img_list):
            img_list = [pickle.loads(img_fp) for img_fp in img_list]
            cnocr: AlOcr = self.__getattribute__(lang)
            return cnocr.debug(img_list)

    server = zerorpc.Server(OCRServer())
    try:
        server.bind(f"tcp://*:{port}")
    except zmq.error.ZMQError:
        logger.error(f"Ocr server cannot bind on port {port}")
        return
    logger.info(f"Ocr server listen on port {port}")
    server.run()


def start_ocr_server_process(port=22268):
    global process
    if not alive():
        process = multiprocessing.Process(target=start_ocr_server, args=(port,))
        process.start()


def stop_ocr_server_process():
    global process
    if alive():
        process.kill()
        process = None


def alive() -> bool:
    global process
    if process is not None:
        return process.is_alive()
    else:
        return False


if __name__ == "__main__":
    # Run server
    parser = argparse.ArgumentParser(description="Alas OCR service")
    parser.add_argument(
        "--port",
        type=int,
        help="Port to listen. Default to OcrServerPort in deploy setting",
    )
    args, _ = parser.parse_known_args()
    port = args.port or State.deploy_config.OcrServerPort
    start_ocr_server(port=port)
