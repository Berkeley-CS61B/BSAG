from pathlib import Path


def class_matches(pat: str, cl: str) -> bool:
    """Checks if the pattern `pat` matches the fully qualified Java class `cl`.

    For class `java.lang.System`, patterns that match include: `java.lang.System`,
    `java.lang.*`, `java.**`, `*.*.*`. Patterns that do not match include
    `java.lang.Other`, `java.*`, `*`.

    Args:
        pat (str): pattern (may contain `*`, `**`, which act similarly to globs)
        cl (str): fully qualified Java class

    Returns:
        bool: if pattern matches class
    """

    pat_chunks = pat.strip().split(".")
    cl_chunks = cl.strip().split(".")

    for pat_chunk, cl_chunk in zip(pat_chunks, cl_chunks):
        if pat_chunk == cl_chunk or pat_chunk == "*":
            continue
        if pat_chunk == "**":
            return True
        return False

    return len(pat_chunks) == len(cl_chunks)


def path_to_classname(path: Path) -> str:
    """
    Converts a filesystem path into a java classname. Intended to be used on relative paths.
    """
    return str(path).replace("/", ".").removesuffix(".java")
