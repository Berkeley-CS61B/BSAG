import os
from pathlib import Path
from subprocess import list2cmdline

from pydantic import PositiveInt

from bsag import BaseStepDefinition
from bsag.bsagio import BSAGIO
from bsag.utils.java import path_to_classname
from bsag.utils.subprocess import run_subprocess

from ._types import PIECES_KEY, AssessmentPieces, BaseJh61bConfig


class ApiCheckConfig(BaseJh61bConfig):
    api_checker_class: str = "jh61b.grader.APIChecker"
    command_timeout: PositiveInt | None = None


class ApiCheck(BaseStepDefinition[ApiCheckConfig]):
    @staticmethod
    def name() -> str:
        return "jh61b.api"

    @classmethod
    def display_name(cls, config: ApiCheckConfig) -> str:
        return "API Checker"

    @classmethod
    def run(cls, bsagio: BSAGIO, config: ApiCheckConfig) -> bool:
        pieces: AssessmentPieces = bsagio.data[PIECES_KEY]

        for name, failed in pieces.failed_pieces.items():
            bsagio.both.info(f"Unable to test API for {name}: {failed.reason}")

        student_classes: set[str] = set()
        api_files: set[Path] = set()
        for name, piece in pieces.live_pieces.items():
            for student_file in piece.student_files:
                api_file = Path(config.grader_root, student_file.with_stem("AGAPI" + student_file.stem))
                if api_file.is_file():
                    student_classes.add(path_to_classname(student_file))
                    api_files.add(api_file)

        if not api_files:
            bsagio.private.warning("No API files to compile.")
            return False

        bsagio.private.trace("Compiling API checkers")
        api_compile_command = ["javac", "-encoding", "utf8"]
        api_compile_command.extend(["-sourcepath", f"{config.grader_root}:{config.submission_root}"])
        bsagio.private.debug(list2cmdline(api_compile_command))
        compile_result = run_subprocess(api_compile_command, timeout=config.command_timeout)
        if compile_result.timed_out:
            bsagio.both.error("API compilation timed out.")
            return False
        if compile_result.return_code != 0:
            bsagio.both.error("API compilation failed.")
            bsagio.private.error("\n" + compile_result.output.strip())

        classpath = ":".join([str(config.grader_root), str(config.submission_root), os.environ.get("CLASSPATH", "")])
        bsagio.private.trace("Testing API")
        api_test_command: list[str | Path] = ["java", "-classpath", classpath, config.api_checker_class]
        api_test_command.extend(student_classes)
        bsagio.private.debug(list2cmdline(api_test_command))

        api_test_result = run_subprocess(api_test_command, timeout=config.command_timeout)
        passed = True
        if api_test_result.timed_out:
            bsagio.both.error("API checker timed out.")
            passed = False
        elif api_test_result.return_code != 0:
            bsagio.both.error("One or more API checks failed.")
            passed = False
        if pieces.failed_pieces:
            bsagio.student.warning(f"Unable to run {len(pieces.failed_pieces)} API check(s).")
            passed = False

        if passed:
            bsagio.student.success("All API checks passed.")

        return passed
