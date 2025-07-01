from typing import Any

from pydantic import NonNegativeFloat, NonNegativeInt, PositiveInt, validator

from bsag import BaseStepConfig, BaseStepDefinition
from bsag.bsagio import BSAGIO

from ._types import METADATA_KEY, RESULTS_KEY, Results, SubmissionMetadata


class LatenessConfig(BaseStepConfig):
    grace_period: NonNegativeInt = 0
    score_decay: dict[PositiveInt, float] = {}  # Start times
    min_lateness_score: NonNegativeFloat = 0

    @validator("score_decay")
    # pylint: disable-next=no-self-argument
    def halt_on_fail__score_decay_mutually_exclusive(
        cls,
        score_decay: dict[NonNegativeInt, float],
        values: dict[str, Any],
    ) -> dict[NonNegativeInt, float]:
        if values["halt_on_fail"] and score_decay:
            msg = "`halt_on_fail` and `score_decay` cannot both be set"
            raise ValueError(msg)
        return score_decay


class Lateness(BaseStepDefinition[LatenessConfig]):
    @staticmethod
    def name() -> str:
        return "gradescope.lateness"

    @classmethod
    def display_name(cls, _config: LatenessConfig) -> str:
        return "Lateness"

    @classmethod
    def run(cls, bsagio: BSAGIO, config: LatenessConfig) -> bool:
        subm_data: SubmissionMetadata = bsagio.data[METADATA_KEY]
        res: Results = bsagio.data[RESULTS_KEY]

        lateness = max(0, (subm_data.created_at - subm_data.users[0].assignment.due_date).total_seconds())
        graced_lateness = max(0, lateness - config.grace_period)

        bsagio.private.debug("Original due date: " + str(subm_data.assignment.due_date))
        bsagio.private.debug("Due for student:       " + str(subm_data.users[0].assignment.due_date))
        bsagio.private.debug("Submitted: " + str(subm_data.created_at))

        if lateness == 0:
            return True

        bsagio.both.info(f"Your submission is {lateness / 3600:.2f} hours late.")
        if graced_lateness == 0:
            bsagio.both.info("This is within the grace period for late submissions on this assignment.")
            return True

        if config.halt_on_fail:
            bsagio.student.info("The autograder for this assignment will not run on a late submission.")
            return False

        # At this point, we know the submission is late.

        penalty = 1.0
        keys = sorted(config.score_decay.keys())
        for k in keys:
            if lateness > k:
                penalty = config.score_decay[k]

        if res.score is not None:
            bsagio.both.info(f"Your score on this assignment was {res.score:.3f}.")
            if res.score > 0:
                res.score *= 1 - penalty
                res.score = max(res.score, config.min_lateness_score)
                bsagio.both.info(
                    f"After applying a lateness penalty of {penalty * 100:.2f}%, your final score is {res.score:.3f}."
                )
            else:
                bsagio.both.info("Scores of 0 do not have lateness applied.")
        else:
            bsagio.private.error("Cannot apply a lateness penalty without an overall score.")

        return False
