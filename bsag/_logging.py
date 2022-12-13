from __future__ import annotations  # necessary for loguru

from enum import Flag, auto
from typing import Callable

import loguru
from pydantic import BaseModel

from bsag._types import BaseStepWithConfig


class LogVisibility(Flag):
    NONE = 0
    LOG_STUDENT = auto()
    LOG_PRIVATE = auto()
    LOG_BOTH = LOG_STUDENT | LOG_PRIVATE


def student_filter(record: loguru.Record) -> bool:
    vis: LogVisibility = record["extra"].get("visibility", LogVisibility.NONE)
    return bool(vis & LogVisibility.LOG_STUDENT)


def private_filter(record: loguru.Record) -> bool:
    vis: LogVisibility = record["extra"].get("visibility", LogVisibility.NONE)
    return bool(vis & LogVisibility.LOG_PRIVATE)


def private_formatter(record: loguru.Record) -> str:
    swc: BaseStepWithConfig | None = record["extra"].get("swc")
    if swc is None:
        name = record["file"].name
    else:
        name = swc.name()
    return (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: >8}</level> | "
        f"[{name: >19}] | "
        "<cyan>{file}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>\n{exception}"
    )


def create_student_sink(logs: list[StepLogs]) -> Callable[[loguru.Message], None]:
    def student_sink(msg: loguru.Message) -> None:
        logs[-1].log_chunks.append(msg)

    return student_sink


class StepLogs(BaseModel):
    success: bool = False
    log_chunks: list[str] = []
    score: float | None = 0
    name: str
    display_name: str
