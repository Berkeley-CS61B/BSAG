from pathlib import Path
from subprocess import list2cmdline

from pydantic import PositiveInt

from bsag import BaseStepConfig, BaseStepDefinition
from bsag.bsagio import BSAGIO
from bsag.steps.gradescope import RESULTS_KEY, OutputFormatEnum, Results, TestCaseStatusEnum, TestResult, VisibilityEnum
from bsag.utils.subprocesses import run_subprocess


class RunCommandConfig(BaseStepConfig):
    display_name: str = "No Name"
    command: str | list[str]
    working_dir: Path | None = None
    command_timeout: PositiveInt | None = None
    points: float | None = None
    show_output: bool = True
    output_visibility: VisibilityEnum | None = None
    output_format: OutputFormatEnum | None = None
    shell: bool = False


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

        bsagio.private.debug(f"Working directory: {config.working_dir}")
        if isinstance(config.command, str):
            bsagio.private.debug("\n" + config.command)
        else:
            bsagio.private.debug("\n" + list2cmdline(config.command))

        output = run_subprocess(
            config.command,
            cwd=config.working_dir,
            timeout=config.command_timeout,
            shell=config.shell,
        )

        test_result = TestResult(name=config.display_name, max_score=config.points)
        passed = True

        if output.timed_out:
            # bsagio.student.error(f"Command timed out after {config.command_timeout} seconds.")
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
            if output.timed_out:
                test_result.output += f"\n------------\nTimed out after {config.command_timeout} seconds."
            if config.output_format:
                test_result.output_format = config.output_format
            if config.output_visibility:
                test_result.visibility = config.output_visibility
            results.tests.append(test_result)

        return passed
