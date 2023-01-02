from pathlib import Path
from subprocess import list2cmdline

from pydantic import PositiveInt

from bsag import BaseStepConfig, BaseStepDefinition
from bsag.bsagio import BSAGIO
from bsag.steps.gradescope import RESULTS_KEY, Results, TestCaseStatusEnum, TestResult
from bsag.utils.subprocesses import run_subprocess


class RunCommandConfig(BaseStepConfig):
    display_name: str
    command: str | list[str]
    working_dir: Path | None = None
    command_timeout: PositiveInt | None = None
    points: float | None = None
    show_output: bool = True


class RunCommand(BaseStepDefinition[RunCommandConfig]):
    @staticmethod
    def name() -> str:
        return "run_command"

    @classmethod
    def display_name(cls, config: RunCommandConfig) -> str:
        return config.display_name

    @classmethod
    def run(cls, bsagio: BSAGIO, config: RunCommandConfig) -> bool:
        results: Results = bsagio.data[RESULTS_KEY]

        bsagio.private.debug(f"Working directory: {config.working_dir}")
        if type(config.command) is str:
            bsagio.private.debug("\n" + config.command)
        else:
            bsagio.private.debug("\n" + list2cmdline(config.command))

        output = run_subprocess(
            config.command,
            cwd=config.working_dir,
            timeout=config.command_timeout,
        )

        test_result = TestResult(max_score=config.points)
        passed = True
        if output.timed_out:
            bsagio.student.error("Command timed out.")
            passed = False
        if not passed or output.return_code != 0:
            test_result.status = TestCaseStatusEnum.FAILED
            if config.points is not None:
                test_result.score = 0
            passed = False
        else:
            test_result.status = TestCaseStatusEnum.PASSED
            if config.points is not None:
                test_result.score = config.points

        if config.show_output:
            test_result.output = output.output

        results.tests.append(test_result)

        return passed
