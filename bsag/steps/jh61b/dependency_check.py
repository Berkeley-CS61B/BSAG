import re
from pathlib import Path
from subprocess import list2cmdline

from pydantic import PositiveInt

from bsag import BaseStepDefinition
from bsag.bsagio import BSAGIO
from bsag.utils.java import class_matches
from bsag.utils.subprocess import run_subprocess

from ._types import BaseJh61bConfig

JDEPS_CLASS_DEP_PAT = re.compile(
    r"""
    ^\s*
    (?P<class>\S+)
    \s+->\s+
    (?P<dep>\S+)
    \s+
    (?P<source>(?:not[ ]found)|\S+)
    \s*$
    """,
    re.VERBOSE,
)


class DepCheckConfig(BaseJh61bConfig):
    allowed_classes: list[str] = ["**"]
    disallowed_classes: list[str] = []
    command_timeout: PositiveInt | None = None


class DepCheck(BaseStepDefinition[DepCheckConfig]):
    @staticmethod
    def name() -> str:
        return "jh61b.dep_check"

    @classmethod
    def display_name(cls, config: DepCheckConfig) -> str:
        return "Illegal Dependency Check"

    @classmethod
    def run(cls, bsagio: BSAGIO, config: DepCheckConfig) -> bool:
        jdeps_commmand: list[str | Path] = [
            "jdeps",
            "--multi-release",
            "base",
            "-verbose:class",
            Path(config.submission_root, "**.class"),
        ]
        bsagio.private.debug("\n" + list2cmdline(jdeps_commmand))
        jdeps_result = run_subprocess(jdeps_commmand, timeout=config.command_timeout)
        if jdeps_result.timed_out:
            bsagio.both.error("Timed out during illegal dependency check.")
            return False

        passed = True
        for line in jdeps_result.output:
            match = re.match(JDEPS_CLASS_DEP_PAT, line)
            if match is None:
                continue
            student_class: str = match.group("class")
            dep_target: str = match.group("dep")

            is_ok = False
            for allowed_pat in config.allowed_classes:
                if class_matches(allowed_pat, dep_target):
                    is_ok = True
                    break
            for disallowed_pat in config.disallowed_classes:
                if class_matches(disallowed_pat, dep_target):
                    is_ok = False
                    break
            if not is_ok:
                passed = False
                bsagio.student.error(f"Class {student_class} has illegal dependency {dep_target}")

        return passed
