import sys
from argparse import ArgumentParser
from typing import Any, get_args

import yaml
from devtools import debug
from loguru import logger

from bsag._logging import StepLogs
from bsag._types import (
    BaseStepConfig,
    BaseStepWithConfig,
    ConfigPreDiscoveryYaml,
    GlobalConfig,
    ParamBaseStep,
    RunConfig,
    StepWithConfig,
)
from bsag.bsagio import BSAGIO
from bsag.steps.common import DisplayMessage
from bsag.steps.external import CheckStyle
from bsag.steps.gradescope import Lateness, LimitVelocity, Motd, ReadSubMetadata, WriteResults
from bsag.steps.jh61b import ApiCheck, Assessment, CheckFiles, Compilation, DepCheck, FinalScore

DEFAULT_STEP_DEFINITIONS: list[type[ParamBaseStep]] = [
    ReadSubMetadata,
    Lateness,
    LimitVelocity,
    Motd,
    WriteResults,
    ApiCheck,
    Assessment,
    CheckFiles,
    Compilation,
    DepCheck,
    FinalScore,
    DisplayMessage,
    CheckStyle,
]


class BSAG:
    def __init__(
        self,
        config_path: str,
        global_config_path: str | None = None,
        step_defs: list[type[ParamBaseStep]] | None = None,
        colorize: bool = False,
        log_level: str = "DEBUG",
    ):
        if not step_defs:
            step_defs = []
        self._step_defs = {m.name(): m for m in DEFAULT_STEP_DEFINITIONS + step_defs}
        self._global_config = self._load_yaml_global_config(global_config_path)
        self._config = self._load_yaml_config(config_path)
        self._bsagio = BSAGIO(colorize_private=colorize, log_level_private=log_level)

    def _load_yaml_global_config(self, global_config_path: str | None) -> GlobalConfig:
        if global_config_path:
            with open(global_config_path, encoding="utf-8") as f:
                return GlobalConfig.parse_obj(yaml.safe_load(f))
        else:
            return GlobalConfig()

    def _load_yaml_config(self, config_path: str) -> RunConfig:
        with open(config_path, encoding="utf-8") as f:
            predisc_config = ConfigPreDiscoveryYaml.parse_obj(yaml.safe_load(f))

        config = RunConfig()
        self._global_config.shared_parameters |= predisc_config.shared_parameters

        self._process_step_plan(
            predisc_config.execution_plan,
            config.execution_plan,
        )
        self._process_step_plan(
            predisc_config.teardown_plan,
            config.teardown_plan,
        )

        return config

    def _process_step_plan(
        self,
        source_plan: list[str | dict[str, dict[str, Any]]],
        target_plan: list[BaseStepWithConfig],
    ) -> None:
        for step in source_plan:
            step_config: dict[str, Any]
            if isinstance(step, str):
                step_name = step
                step_config = {}
            elif len(step) == 1:
                step_name = next(iter(step.keys()))
                step_config = step[step_name]
            else:
                print(f"Step `{step}` not formatted properly")
                sys.exit(1)

            if step_name not in self._step_defs:
                print(f"Step `{step_name}` not found", file=sys.stderr)
                sys.exit(1)

            StepDefType = self._step_defs[step_name]
            StepConfigType: type[BaseStepConfig]
            StepConfigType = get_args(StepDefType.__orig_bases__[0])[0]  # type: ignore
            # Prioritize specific configs over global
            step_config = self._global_config.global_settings.get(step_name, {}) | step_config

            # Merge relevant global shared parameters...
            for k, v in self._global_config.shared_parameters.items():
                # ... prioritizing params in step config
                if k in StepConfigType.__fields__ and k not in step_config:
                    step_config[k] = v

            target_plan.append(
                StepWithConfig(
                    StepType=StepDefType,
                    config=StepConfigType.parse_obj(step_config),
                )
            )

    def run(self) -> None:
        # loguru catch wll not reraise by default
        @self._bsagio.private.catch()
        def execute_plan(plan: list[BaseStepWithConfig]) -> None:
            for swc in plan:
                self._bsagio.step_logs.append(StepLogs(name=swc.name(), display_name=swc.display_name()))
                with logger.contextualize(swc=swc):
                    self._bsagio.private.info(f"Starting {swc.StepType.name()}")
                    step_result = swc.run(self._bsagio)
                    if step_result:
                        self._bsagio.step_logs[-1].success = True
                    elif swc.config.halt_on_fail:
                        raise RuntimeError(f"Step {swc.StepType.name()} failed and halts on failure.")
                    self._bsagio.private.trace(f"Finished {swc.StepType.name()}")

        execute_plan(self._config.execution_plan)
        execute_plan(self._config.teardown_plan)

    @property
    def config(self) -> RunConfig:
        return self._config


def main(steps: list[type[ParamBaseStep]] | None = None) -> None:
    parser = ArgumentParser(description="A Better Simple AutoGrader")
    parser.add_argument("--dry-run", action="store_true", help="Parse config, but don't run.")
    parser.add_argument("--global-config", help="Path to global config file")
    parser.add_argument("--config", required=True, help="Path to config file")
    parser.add_argument("--colorize", action="store_true", help="Colorize private logs")
    parser.add_argument(
        "--log-level",
        default="DEBUG",
        choices=("TRACE", "DEBUG", "INFO", "SUCCESS", "WARNING", "ERROR", "CRITICAL"),
        type=str.upper,
        help="Customize private log level",
    )
    args = parser.parse_args()

    bsag = BSAG(
        config_path=args.config,
        global_config_path=args.global_config,
        step_defs=steps,
        colorize=args.colorize,
        log_level=args.log_level,
    )
    if args.dry_run:
        debug(bsag.config)
        sys.exit(0)

    bsag.run()
