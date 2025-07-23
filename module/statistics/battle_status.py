from module.base.decorator import cached_property
from module.combat.assets import BATTLE_STATUS_S

# from module.ocr.ocr import Ocr
from module.statistics.assets import ENEMY_NAME


class BattleStatusStatistics:
    def appear_on(self, image):
        return BATTLE_STATUS_S.appear_on(image)

    @cached_property
    def ocr_object(self):
        class OcrStub:
            def ocr(self, image):
                return ""

        return OcrStub()

    def stats_battle_status(self, image):
        """
        Args:
            image (np.ndarray):

        Returns:
            str: Enemy name, such as '中型主力舰队'.
        """
        result = self.ocr_object.ocr(image)
        # Delete wrong OCR result
        for letter in "-一个―~(":
            result = result.replace(letter, "")

        return result
