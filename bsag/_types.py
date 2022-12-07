from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Generic, TypeAlias, TypeVar

from pydantic import BaseModel, Extra
from pydantic.dataclasses import dataclass

if TYPE_CHECKING:
    from bsag.bsagio import BSAGIO

C_co = TypeVar("C_co", bound="BaseStepConfig", covariant=True)


class BaseStepConfig(BaseModel, extra=Extra.forbid):
    halt_on_fail: bool = False


class BaseStepDefinition(ABC, Generic[C_co]):
    @staticmethod
    @abstractmethod
    def name() -> str:
        """Returns (unique) name of module."""

    # Technically we can't take a covariant parameter. However, this is a classmethod.
    # https://github.com/python/mypy/issues/7049
    # The reason these aren't instance methods is that I can't enforce a constructor call that would set `config`.
    @classmethod
    def display_name(cls, config: C_co) -> str:  # type: ignore
        """Returns display name of module that appears in student-facing logs."""
        return cls.name()

    @classmethod
    @abstractmethod
    def run(cls, bsagio: BSAGIO, config: C_co) -> bool:  # type: ignore
        ...


@dataclass
class StepWithConfig(Generic[C_co]):
    StepType: type[BaseStepDefinition[C_co]]
    config: C_co

    def name(self) -> str:
        return self.StepType.name()

    def run(self, bsagio: BSAGIO) -> bool:
        return self.StepType.run(bsagio, self.config)

    def display_name(self) -> str:
        return self.StepType.display_name(self.config)


BaseStepWithConfig: TypeAlias = StepWithConfig[BaseStepConfig]
ParamBaseStep: TypeAlias = BaseStepDefinition[BaseStepConfig]


class RunConfig(BaseModel, extra=Extra.forbid):
    execution_plan: list[BaseStepWithConfig] = []
    teardown_plan: list[BaseStepWithConfig] = []


class ConfigPreDiscoveryYaml(BaseModel, extra=Extra.forbid):
    shared_parameters: dict[str, Any] = {}
    execution_plan: list[str | dict[str, dict[str, Any]]] = []
    teardown_plan: list[str | dict[str, dict[str, Any]]] = []


class GlobalConfig(BaseModel, extra=Extra.forbid):
    shared_parameters: dict[str, Any] = {}
    global_settings: dict[str, dict[str, Any]] = {}
