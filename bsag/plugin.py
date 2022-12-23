import pluggy  # type: ignore

from bsag._types import ParamBaseStep

PROJECT_NAME = "bsag"

hookimpl = pluggy.HookimplMarker(PROJECT_NAME)
hookspec = pluggy.HookspecMarker(PROJECT_NAME)


@hookspec  # type: ignore
def bsag_load_step_defs() -> list[type["ParamBaseStep"]]:  # type: ignore
    """This hook is used to load BSAG step definitions."""
