# BSAG (Better Simple AutoGrader)

A Gradescope autograder with a focus on simplicity, extensibility, and
correctness.

## Notice

**This package is currently under active development! It's probably broken.**
I'm working as fast as I can to un-break it and add features.
Once I've verified that I can run an autograder, I will publish it on PyPI.

## Architecture Summary

BSAG is based on sequential execution of "steps". A step defines and accepts a
*configuration*, performs some computation, and possibly modifies stored data.
BSAG uses [Pydantic](https://docs.pydantic.dev/) for config parsing and typing,
and parses YAML for ease of writing.

A more detailed description can be found in [ARCHITECTURE.md](ARCHITECTURE.md).

## Usage

BSAG is primarily meant to be used as a
[Gradescope autograder](https://gradescope-autograders.readthedocs.io/en/latest/),
on any system using at least Python 3.10.

BSAG provides a small suite of default steps, and can be run with simply:

```shell
python -m bsag --config <path_to_config>
```

To provide your own custom step definitions, you can define your own entry
point and provide your modules at runtime:

```python
import bsag


bsag.main([MyCustomStep])
```
