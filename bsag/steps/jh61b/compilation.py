from pathlib import Path
from subprocess import list2cmdline

from pydantic import PositiveInt

from bsag import BaseStepDefinition
from bsag.bsagio import BSAGIO
from bsag.utils.subprocess import run_subprocess

from ._types import PIECES_KEY, AssessmentPieces, BaseJh61bConfig, FailedPiece


class CompilationConfig(BaseJh61bConfig):
    compile_flags: list[str] = []
    command_timeout: PositiveInt | None = None


class Compilation(BaseStepDefinition[CompilationConfig]):
    @staticmethod
    def name() -> str:
        return "jh61b.compilation"

    @classmethod
    def display_name(cls, config: CompilationConfig) -> str:
        return "Compilation"

    @classmethod
    def run(cls, bsagio: BSAGIO, config: CompilationConfig) -> bool:
        pieces: AssessmentPieces = bsagio.data[PIECES_KEY]
        num_live_pieces = len(pieces.live_pieces)
        for name, piece in list(pieces.live_pieces.items()):
            bsagio.both.info(f"Compiling tests for {name}...")

            compile_command: list[str | Path] = ["javac", "-encoding", "utf8", "-g"]
            compile_command.extend(["-sourcepath", f"{config.grader_root}:{config.submission_root}"])
            compile_command.extend(config.compile_flags)
            compile_command.extend(piece.assessment_files)
            bsagio.private.debug("\n" + list2cmdline(compile_command))

            compile_result = run_subprocess(compile_command, timeout=config.command_timeout)

            if compile_result.timed_out:
                bsagio.both.error("Timed out.")
                pieces.failed_pieces[name] = FailedPiece(reason="compilation timed out")
                del pieces.live_pieces[name]
            elif compile_result.return_code:
                bsagio.both.error("=========== COMPILATION ERROR =============")
                pieces.failed_pieces[name] = FailedPiece(reason="compilation failed")
                del pieces.live_pieces[name]
            else:
                bsagio.student.info("Success!")

            if compile_result.output:
                bsagio.student.info(compile_result.output.strip())
                bsagio.private.info("\n" + compile_result.output.strip())

        return num_live_pieces == len(pieces.live_pieces)
