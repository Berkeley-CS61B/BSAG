from typing import Any

from pydantic import NonNegativeInt, PositiveInt, validator

from bsag import BaseStepConfig, BaseStepDefinition
from bsag.bsagio import BSAGIO

from ._types import METADATA_KEY, RESULTS_KEY, Results, SubmissionMetadata


class LatenessConfig(BaseStepConfig):
    grace_period: NonNegativeInt = 0
    score_decay: dict[PositiveInt, float] = {}  # Start times

    @validator("score_decay")
    def halt_on_fail__score_decay_mutually_exclusive(
        cls,
        score_decay: dict[NonNegativeInt, float],
        values: dict[str, Any],
    ):
        if values["halt_on_fail"] and score_decay:
            raise ValueError("`halt_on_fail` and `score_decay` cannot both be set")
        return score_decay


class Lateness(BaseStepDefinition[LatenessConfig]):
    @staticmethod
    def name() -> str:
        return "gradescope.lateness"

    @classmethod
    def display_name(cls, config: LatenessConfig) -> str:
        return "Lateness"

    @classmethod
    def run(cls, bsagio: BSAGIO, config: LatenessConfig) -> bool:
        subm_data: SubmissionMetadata = bsagio.data[METADATA_KEY]
        res: Results = bsagio.data[RESULTS_KEY]

        lateness = max(0, (subm_data.assignment.due_date - subm_data.created_at).total_seconds())
        graced_lateness = max(0, lateness - config.grace_period)

        if lateness == 0:
            return True

        bsagio.both.info("Your submission is %.2f hours late." % (lateness / 3600))
        if graced_lateness == 0:
            bsagio.both.info("This is within the grace period for late submissions on this assignment.")
            return True

        if config.halt_on_fail:
            bsagio.student.info("The autograder for this assignment will not run on a late submission.")
            return False

        penalty = 1.0
        keys = sorted(config.score_decay.keys())
        for k in keys:
            if lateness < k:
                penalty = config.score_decay[k]

        if res.score:
            bsagio.both.info(f"Your score on this assignment was {res.score:.2f}")
            res.score *= 1 - penalty
            bsagio.both.info(
                f"After applying a lateness penalty of {penalty * 100:.2f}%, your final score is {res.score:.2f}"
            )
        else:
            bsagio.private.error("Cannot apply a lateness penalty without an overall score.")

        return False
