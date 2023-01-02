from bsag import BaseStepConfig, BaseStepDefinition
from bsag.bsagio import BSAGIO
from bsag.steps.gradescope import TestCaseStatusEnum


class DisplayMessageConfig(BaseStepConfig):
    title: str
    text: str
    result: TestCaseStatusEnum = TestCaseStatusEnum.PASSED


class DisplayMessage(BaseStepDefinition[DisplayMessageConfig]):
    @staticmethod
    def name() -> str:
        return "display_message"

    @classmethod
    def display_name(cls, config: DisplayMessageConfig) -> str:
        return config.title

    @classmethod
    def run(cls, bsagio: "BSAGIO", config: DisplayMessageConfig) -> bool:
        bsagio.student.critical(config.text)
        return config.result == TestCaseStatusEnum.PASSED
