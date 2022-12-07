from pathlib import Path

from bsag import BaseStepConfig, BaseStepDefinition
from bsag.bsagio import BSAGIO

from ._types import RESULTS_KEY, Results, TestCaseStatusEnum, TestResult


class ResultsConfig(BaseStepConfig):
    round_tests_to_digits: int = 3
    output_path: Path = Path("/autograder/results/results.json")


class WriteResults(BaseStepDefinition[ResultsConfig]):
    @staticmethod
    def name() -> str:
        return "gradescope.results"

    @classmethod
    def display_name(cls, config: ResultsConfig) -> str:
        return "Results"

    @classmethod
    def run(cls, bsagio: BSAGIO, config: ResultsConfig) -> bool:
        res: Results = bsagio.data[RESULTS_KEY]
        if not res.validate_score():
            return False

        digits = config.round_tests_to_digits
        if res.score is not None:
            res.score = round(res.score, digits)
        for test in res.tests:
            if test.score is not None:
                test.score = round(test.score, digits)
            if test.max_score is not None:
                test.max_score = round(test.max_score, digits)

        module_logs: list[TestResult] = []
        for log in bsagio.step_logs:
            if not log.log_chunks:
                continue
            module_logs.append(
                TestResult(
                    name=log.display_name,
                    output="\n".join(log.log_chunks),
                    score=log.score if log.score is None else round(log.score, digits),
                    status=TestCaseStatusEnum.PASSED if log.success else TestCaseStatusEnum.FAILED,
                )
            )
        res.tests = module_logs + res.tests

        with config.output_path.open("w") as outfile:
            outfile.write(res.json())

        return True
