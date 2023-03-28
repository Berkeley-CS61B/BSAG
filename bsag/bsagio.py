import contextlib
import sys
from typing import Any

from loguru import logger

from bsag._logging import (
    LogVisibility,
    StepLogs,
    create_student_sink,
    private_filter,
    private_formatter,
    student_filter,
)


class BSAGIO:
    def __init__(self, colorize_private: bool = False, log_level_private: str = "DEBUG") -> None:
        # TODO: verify data entries by changing it to Pydantic create_model and asking models for fields?
        self.data: dict[str, Any] = {}
        self.step_logs: list[StepLogs] = []
        self.colorize_private = colorize_private

        self.student = logger.bind(visibility=LogVisibility.LOG_STUDENT)
        self.private = logger.bind(visibility=LogVisibility.LOG_PRIVATE)
        self.both = logger.bind(visibility=LogVisibility.LOG_BOTH)

        # TODO: `format` callable provided as argument?
        # TODO: log level setting, at least for private?
        with contextlib.suppress(ValueError):
            logger.remove(0)

        student_sink = create_student_sink(self.step_logs)
        # Student logs are never formatted
        logger.add(student_sink, filter=student_filter, format="{message}")
        logger.add(
            sys.stdout,
            filter=private_filter,
            format=private_formatter,
            colorize=colorize_private,
            level=log_level_private,
        )
