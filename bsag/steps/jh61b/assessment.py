import json
import os
import tempfile
from subprocess import list2cmdline

from pydantic import PositiveInt

from bsag import BaseStepDefinition
from bsag.bsagio import BSAGIO
from bsag.steps.gradescope import METADATA_KEY, Results, SubmissionMetadata, TestCaseStatusEnum, TestResult
from bsag.utils.java import path_to_classname
from bsag.utils.subprocess import run_subprocess

from ._types import PIECES_KEY, TEST_RESULTS_KEY, AssessmentPieces, BaseJh61bConfig, Jh61bResults


class AssessmentConfig(BaseJh61bConfig):
    piece_name: str
    java_options: list[str] = []
    command_timeout: PositiveInt | None = None
    require_full_score: bool = False
    aggregated_number: str | None = None


class Assessment(BaseStepDefinition[AssessmentConfig]):
    @staticmethod
    def name() -> str:
        return "jh61b.assessment"

    @classmethod
    def display_name(cls, config: AssessmentConfig) -> str:
        return f"Assessment {config.piece_name}"

    @classmethod
    def run(cls, bsagio: BSAGIO, config: AssessmentConfig) -> bool:
        pieces: AssessmentPieces = bsagio.data[PIECES_KEY]
        sub_meta: SubmissionMetadata = bsagio.data[METADATA_KEY]

        if config.piece_name not in pieces.live_pieces:
            if config.piece_name in pieces.failed_pieces:
                reason = pieces.failed_pieces[config.piece_name].reason
            else:
                reason = "unknown piece name"

            bsagio.both.error(f"Unable to run assessment for {config.piece_name}: {reason}")
            return False

        bsagio.private.info(f"Testing {config.piece_name}...")

        java_properties = {
            "bsag.grader.classroot": config.grader_root,
            "bsag.submission.classroot": config.submission_root,
            "bsag.student.email": ",".join(s.email for s in sub_meta.users),
            "bsag.student.name": ",".join(s.name for s in sub_meta.users),
        }
        java_options = [f"-D{k}={v}" for k, v in java_properties.items()]
        java_options += config.java_options

        classpath = f"{config.grader_root}:{config.submission_root}:{os.environ.get('CLASSPATH')}"

        piece = pieces.live_pieces[config.piece_name]
        test_results: list[TestResult] = []
        _, outfile = tempfile.mkstemp(suffix=".json", prefix="assess")
        for assessment_file in piece.assessment_files:
            assessment_class = path_to_classname(assessment_file.relative_to(config.grader_root))

            assessment_command = ["java"] + java_options
            assessment_command += ["-classpath", classpath, assessment_class]
            assessment_command += ["--secure", "--json", "--outfile", outfile]

            bsagio.private.debug("\n" + list2cmdline(assessment_command))

            # Grader may use relative paths, so use cwd
            result = run_subprocess(
                assessment_command,
                cwd=config.grader_root,
                timeout=config.command_timeout,
            )
            if result.timed_out:
                bsagio.private.error(f"timed out while running {assessment_class}")
                bsagio.student.error(
                    f"Your submission timed out on the test suite {assessment_class}.\n"
                    "Please make sure your code terminates on all inputs, and doesn't take too long to do so."
                )
                return False
            if result.return_code > 128 or result.return_code < 0:
                bsagio.private.error(f"process died with code {result.return_code} running {assessment_class}")
                bsagio.student.error(
                    f"Your submission failed to complete on the test suite {assessment_class}.\n"
                    "You're most likely using too much memory."
                )
                return False

            # jh61b produces an entire Results, but we may have multiple Assessments.
            try:
                with open(outfile, encoding="utf-8") as f:
                    test_json = json.load(f)
                results = Results.parse_obj(test_json)
                test_results.extend(results.tests)
            except json.JSONDecodeError:
                bsagio.private.error(f"Error decoding output for {assessment_class}")
                bsagio.private.error("\n" + result.output)
                bsagio.student.error("Unexpected error while running assessment; details in staff logs.")

                return False

        score = 0.0
        max_score = 0.0
        for test in test_results:
            score += test.score or 0
            max_score += test.max_score or 0

        bsagio.private.info(f"Scored {score:.3f} / {max_score:.3f} points on {config.piece_name}")

        if TEST_RESULTS_KEY not in bsagio.data:
            bsagio.data[TEST_RESULTS_KEY] = {}

        if config.require_full_score:
            if score != max_score:
                bsagio.private.info(f"{config.piece_name} requires full score to receive credit.")
                score = 0

            failed_tests: list[str] = []
            for test in test_results:
                if test.score != test.max_score:
                    test.status = TestCaseStatusEnum.FAILED
                    failed_tests.append(
                        "- " + (test.number if test.number else "") + (test.name if test.name else "Unnamed test")
                    )
                test.score = None
                test.max_score = None

            output_chunks = [
                f"{config.piece_name} requires full score to receive credit.",
            ]
            if failed_tests:
                output_chunks.append("Failing the following tests:")
                output_chunks.extend(failed_tests)

            test_results.insert(
                0,
                TestResult(
                    name=config.piece_name,
                    number=config.aggregated_number,
                    score=score,
                    max_score=max_score,
                    output="\n".join(output_chunks),
                ),
            )

        bsagio.data[TEST_RESULTS_KEY][config.piece_name] = Jh61bResults(
            score=score, max_score=max_score, tests=test_results
        )

        return not (config.require_full_score and score != max_score)
