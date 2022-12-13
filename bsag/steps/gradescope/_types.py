from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel

METADATA_KEY = "gs_submission_metadata"
"""Created by `submission_metadata`.

Type: `SubmissionMetadata`, see https://gradescope-autograders.readthedocs.io/en/latest/submission_metadata/
"""

RESULTS_KEY = "gs_results"
"""Initially created and empty by `submission_metatadata`, populated by other modules.

Type: `Results`, see https://gradescope-autograders.readthedocs.io/en/latest/specs/#output-format
"""


class VisibilityEnum(str, Enum):
    HIDDEN = "hidden"
    AFTER_DUE_DATE = "after_due_date"
    AFTER_PUBLISHED = "after_published"
    VISIBLE = "visible"


class TestCaseStatusEnum(str, Enum):
    FAILED = "failed"
    PASSED = "passed"


class SubmissionMethodEnum(str, Enum):
    UPLOAD = "upload"
    GITHUB = "GitHub"
    BITBUCKET = "Bitbucket"


class User(BaseModel):
    email: str
    id: int
    name: str


class Assignment(BaseModel):
    due_date: datetime
    group_size: int | None
    group_submission: bool
    id: int
    course_id: int
    late_due_date: datetime | None
    release_date: datetime
    title: str
    total_points: float


class LeaderboardEntry(BaseModel):
    name: str
    value: float
    order: Literal["asc", "desc"] | None


class TestResult(BaseModel):
    score: float | None = None
    max_score: float | None = None
    status: TestCaseStatusEnum | None = None
    name: str | None = None
    number: str | None = None
    output: str | None = None
    tags: list[str] = []
    visibility: VisibilityEnum | None = None


class Results(BaseModel):
    score: float | None = None
    execution_time: float | None = None
    output: str | None = None
    visibility: VisibilityEnum | None = None
    stdout_visibility: VisibilityEnum | None = None
    tests: list[TestResult] = []
    leaderboard: list[LeaderboardEntry] = []

    def validate_score(self) -> bool:
        return self.score is not None or (bool(self.tests) and all(t.score is not None for t in self.tests))


class PreviousSubmission(BaseModel):
    submission_time: datetime
    score: float = 0.0
    result: Results = Results()


class SubmissionMetadata(BaseModel):
    id: int
    created_at: datetime
    assignment: Assignment
    submission_method: SubmissionMethodEnum
    users: list[User]
    previous_submissions: list[PreviousSubmission]
