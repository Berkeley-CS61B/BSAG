from datetime import datetime, timedelta

from pytz import timezone
from pydantic import BaseModel, PositiveInt, validator

from bsag import BaseStepConfig, BaseStepDefinition
from bsag.bsagio import BSAGIO
from bsag.utils.datetimes import ZERO_TD, format_datetime

from ._types import METADATA_KEY, SubmissionMetadata

EXTRA_TOKENS_KEY = "extra_tokens"
"""Used by `gradescope.limit_velocity` to add extra velocity tokens. If not present, then 0 tokens are added.

Type: `int`, for number of extra tokens available
"""


class Window(BaseModel):
    # Due date is affected by extensions, so use absolute time
    start_time: datetime = datetime.utcfromtimestamp(0)
    max_tokens: PositiveInt
    recharge_time: timedelta
    reset_tokens: bool = True


class LimitVelocityConfig(BaseStepConfig):
    time_zone: str = "UTC"
    time_format: str = "%a %B %d %Y, %H:%M:%S %Z"
    ignore_scores_below: float = 0.0
    windows: list[Window]

    @validator("windows")
    def windows_must_be_strictly_asc(cls, windows: list[Window]) -> list[Window]:
        for i in range(len(windows) - 1):
            if windows[i + 1].recharge_time - windows[i].recharge_time <= ZERO_TD:
                msg = "Window start times not strictly increasing"
                raise ValueError(msg)
        return windows


class LimitVelocity(BaseStepDefinition[LimitVelocityConfig]):
    @staticmethod
    def name() -> str:
        return "gradescope.limit_velocity"

    @classmethod
    def display_name(cls, config: LimitVelocityConfig) -> str:
        return "Limit Velocity"

    @classmethod
    def run(cls, bsagio: BSAGIO, config: LimitVelocityConfig) -> bool:
        data = bsagio.data
        subm_data: SubmissionMetadata = data[METADATA_KEY]
        curr_sub_create_time = subm_data.created_at
        prev_submissions = subm_data.previous_submissions

        windows = [
            Window(
                start_time=datetime.utcfromtimestamp(0).astimezone(timezone(config.time_zone)),
                max_tokens=1,
                recharge_time=ZERO_TD,
            )
        ] + config.windows

        # Latest window with start time before current submission
        w_idx, active_window = [(i, w) for i, w in enumerate(windows) if w.start_time < curr_sub_create_time][-1]

        token_submissions_times = [
            sub.submission_time
            for sub in prev_submissions
            if (sub.score > config.ignore_scores_below)
            and (sub.submission_time > active_window.start_time)
            and (ZERO_TD <= (curr_sub_create_time - sub.submission_time) < active_window.recharge_time)
        ]
        token_submissions_times.append(curr_sub_create_time)

        extra_tokens: int = data.get(EXTRA_TOKENS_KEY, 0)
        bsagio.private.trace(f"Extra tokens: {extra_tokens}")
        tokens_avail = active_window.max_tokens + extra_tokens - len(token_submissions_times)
        recharge_at = token_submissions_times[0] + active_window.recharge_time

        bsagio.student.info(
            "This assignment uses velocity limiting based on a token system. Tokens are assignment-specific."
        )
        bsagio.student.info(
            f"The current limiting scheme for this assignment is a maximum of {active_window.max_tokens}, each "
            f" recharging after {active_window.recharge_time} seconds."
        )
        bsagio.student.info("")

        if tokens_avail >= 0:
            bsagio.student.info(f"After this submission, you will have {tokens_avail} tokens remaining.")
        else:
            bsagio.student.error("You are out of tokens, so the autograder will not run until your next recharge.")
            bsagio.private.error("Velocity limited -- halting AG...")

        bsagio.student.info("")
        bsagio.student.info("Tokens are currently consumed by:")
        for i, sub_time in enumerate(token_submissions_times[::-1]):
            sub_msg = "* Submission at " + format_datetime(sub_time, config.time_zone, config.time_format)
            if i == 0:
                sub_msg += " [current]"
            bsagio.student.info(sub_msg)

        bsagio.student.info("")
        bsagio.student.info(f"Submissions with scores {config.ignore_scores_below} or lower do not consume tokens.")
        bsagio.student.info(f"This assignment's tokens recharge every {active_window.recharge_time} seconds.")

        if w_idx + 1 < len(windows):
            next_window = windows[w_idx + 1]
            bsagio.student.info(
                f"At {next_window.start_time}, the velocity limiting will change to a maximum of "
                f"{next_window.max_tokens}, each recharging after {next_window.recharge_time} seconds."
            )

        if w_idx + 1 < len(windows) and windows[w_idx + 1].start_time < recharge_at and windows[w_idx + 1].reset_tokens:
            next_window = windows[w_idx + 1]
            bsagio.student.info("When the velocity limiting changes, your tokens will be completely refreshed.")
        else:
            recharge_time = format_datetime(recharge_at, config.time_zone, config.time_format)
            bsagio.student.info(f"Your next recharge will occur at {recharge_time}.")

        return tokens_avail >= 0
