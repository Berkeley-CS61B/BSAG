from pydantic import PositiveInt

from bsag import BaseStepConfig, BaseStepDefinition
from bsag.bsagio import BSAGIO
from bsag.steps.gradescope import RESULTS_KEY, Results, TestResult


class RunCommandConfig(BaseStepConfig):
    display_name: str
    command: str
    command_timeout: PositiveInt | None = None
    # Other things related to capturing and displaying output
    points: float | None = None


class RunCommand(BaseStepDefinition[RunCommandConfig]):
    @staticmethod
    def name() -> str:
        return "common.run_command"

    @classmethod
    def display_name(cls, config: RunCommandConfig) -> str:
        return config.display_name

    @classmethod
    def run(cls, bsagio: BSAGIO, config: RunCommandConfig) -> bool:
        results: Results = bsagio.data[RESULTS_KEY]

        # TODO: run the command
        # - Display output (stdout, stderr) if requested
        # - Create a test result if necessary
        # This should let me do the total grading thing, because jh61b
        # proportionally scores based on its own max score (rather than an overall max score)

        return True
