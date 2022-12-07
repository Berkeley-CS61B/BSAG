from pathlib import Path

from pydantic import BaseModel

from bsag import BaseStepConfig
from bsag.steps.gradescope import TestResult

PIECES_KEY = "jh61b_pieces"
TEST_RESULTS_KEY = "jh61b_test_results"


class Piece(BaseModel):
    student_files: set[Path]
    assessment_files: set[Path]


class FailedPiece(BaseModel):
    reason: str


class AssessmentPieces(BaseModel):
    live_pieces: dict[str, Piece] = {}
    failed_pieces: dict[str, FailedPiece] = {}


class BaseJh61bConfig(BaseStepConfig):
    grader_root: Path
    submission_root: Path


class Jh61bResults(BaseModel):
    score: float
    max_score: float
    tests: list[TestResult]
