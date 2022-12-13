from typing import NamedTuple

from bsag import BaseStepConfig, BaseStepDefinition
from bsag.bsagio import BSAGIO
from bsag.steps.gradescope import RESULTS_KEY, Results, TestResult

from ._types import TEST_RESULTS_KEY, Jh61bResults


class FinalScoreConfig(BaseStepConfig):
    max_points: float
    scoring: dict[str, float]
    scale_factor: float = 1
    penalties: dict[str, float] = {}


class Score(NamedTuple):
    score: float
    max_score: float


class FinalScore(BaseStepDefinition[FinalScoreConfig]):
    @staticmethod
    def name() -> str:
        return "jh61b.final_score"

    @classmethod
    def display_name(cls, config: FinalScoreConfig) -> str:
        return "Final Score"

    @classmethod
    def run(cls, bsagio: BSAGIO, config: FinalScoreConfig) -> bool:
        res: Results = bsagio.data[RESULTS_KEY]
        test_results: dict[str, Jh61bResults] = bsagio.data.get(TEST_RESULTS_KEY, {})

        subscores = {
            piece: result.score / result.max_score if result.max_score > 0 else 0.0
            for piece, result in test_results.items()
        }

        # Reweight scores
        total_weight = sum(config.scoring.values())
        weighted_scores: dict[str, Score] = {}
        for piece, score in subscores.items():
            weight = config.scoring.get(piece, 0)
            max_subscore = weight / total_weight * config.max_points
            weighted_scores[piece] = Score(score * max_subscore, max_subscore)

        if config.scale_factor > 1.0:
            bsagio.student.info(
                f"Your final score was multiplied by {config.scale_factor:.2f} since this assignment doesn't require\n"
                "total perfection for full credit. Your score may not exceed the max."
            )

        total_score = sum(scores[0] for scores in weighted_scores.values())
        total_score *= config.scale_factor
        total_score = min(config.max_points, total_score)

        # Apply penalties
        total_penalty = 0.0
        if config.penalties:
            for step_log in bsagio.step_logs:
                if not step_log.success and step_log.name in config.penalties:
                    penalty = config.penalties[step_log.name] * total_score
                    step_log.score = -penalty
                    total_penalty += penalty

        final_score = total_score - total_penalty
        bsagio.private.info(f"Final score post-scaling: {final_score:.3f} / {config.max_points:.3f}")
        res.score = final_score

        # Rescale Jh61bResults
        rescaled_tests: list[TestResult] = []
        for piece, result in test_results.items():
            rescale = weighted_scores[piece].max_score / result.max_score if result.max_score > 0 else 0.0
            for test in result.tests:
                test.score = rescale * test.score if test.score else 0.0
                test.max_score = rescale * test.max_score if test.max_score else 0.0
                rescaled_tests.append(test)

        rescaled_tests.sort(key=lambda t: t.number if t.number is not None else f"_{t.name}")
        res.tests.extend(rescaled_tests)

        return True
