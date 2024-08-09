import itertools
import sys
from argparse import ArgumentParser
from pathlib import Path
from typing import Any, get_args

import pluggy  # type: ignore
import yaml
from devtools import debug
from loguru import logger

import bsag.plugin
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
from bsag.plugin import PROJECT_NAME, hookimpl


def get_plugin_manager():
    plugin_manager = pluggy.PluginManager(PROJECT_NAME)
    plugin_manager.add_hookspecs(bsag.plugin)  # type: ignore
    plugin_manager.load_setuptools_entrypoints(PROJECT_NAME)  # type: ignore
    plugin_manager.register(sys.modules[__name__])  # type: ignore
    return plugin_manager


@hookimpl  # type: ignore
def bsag_load_step_defs() -> list[type[ParamBaseStep]]:
    # Defer to avoid circular imports
    from bsag.steps.common import DisplayMessage, RunCommand
    from bsag.steps.gradescope import Lateness, LimitVelocity, ReadSubMetadata, WriteResults

    return [
        ReadSubMetadata,
        Lateness,
        LimitVelocity,
        WriteResults,
        DisplayMessage,
        RunCommand,
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
        pm = get_plugin_manager()
        # type: ignore
        # pylint: disable-next=no-member
        plugin_steps: list[type[ParamBaseStep]] = list(itertools.chain(*pm.hook.bsag_load_step_defs()))  # type: ignore
        self._step_defs = {m.name(): m for m in plugin_steps + step_defs}
        self._global_config = self._load_yaml_global_config(global_config_path)
        self._config = self._load_yaml_config(config_path)
        self._bsagio = BSAGIO(colorize_private=colorize, log_level_private=log_level)
        self._colorize = colorize

    def _load_yaml_global_config(self, global_config_path: str | None) -> GlobalConfig:
        if global_config_path:
            with Path(global_config_path).open(encoding="utf-8") as f:
                return GlobalConfig.parse_obj(yaml.safe_load(f))
        else:
            return GlobalConfig()

    def _load_yaml_config(self, config_path: str) -> RunConfig:
        with Path(config_path).open(encoding="utf-8") as f:
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
                print(f"Available steps: {list(self._step_defs.keys())}")
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
                    self._bsagio.private.trace(f"Starting {swc.StepType.name()}")
                    debug_config = debug.format(swc.config).str(highlight=self._colorize)
                    self._bsagio.private.trace(f"Using config:\n{debug_config}")
                    step_result = swc.run(self._bsagio)
                    if step_result:
                        self._bsagio.step_logs[-1].success = True
                    elif swc.config.halt_on_fail:
                        msg = f"Step {swc.StepType.name()} failed and halts on failure."
                        # This is a known exception, so kill the traceback
                        sys.tracebacklimit = 0
                        raise RuntimeError(msg)
                    self._bsagio.private.trace(f"Finished {swc.StepType.name()}")

        old_tb = getattr(sys, "tracebacklimit", 1000)
        execute_plan(self._config.execution_plan)
        sys.tracebacklimit = old_tb
        execute_plan(self._config.teardown_plan)
        sys.tracebacklimit = old_tb

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
