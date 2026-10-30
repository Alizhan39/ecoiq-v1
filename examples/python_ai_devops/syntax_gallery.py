"""Python 3.11 examples: arguments, operators, typing and advanced syntax."""
from __future__ import annotations

from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass
from functools import wraps
from typing import ParamSpec, TypeVar

P = ParamSpec("P")
T = TypeVar("T")


def signatures(case_id: str, /, quantity: float = 0.0, *,
               unit: str = "kg", reviewer: str | None = None,
               **metadata: str) -> dict[str, object]:
    """Positional-only (/), default, keyword-only (*) and **kwargs."""
    if not case_id.strip():
        raise ValueError("case_id required")
    return dict(case_id=case_id, quantity=quantity, unit=unit,
                reviewer=reviewer, metadata=metadata)


def variadic(*values: float, scale: float = 1) -> tuple[float, ...]:
    """Gather positional values with *args."""
    return tuple(value * scale for value in values)


def assignment_examples() -> dict[str, object]:
    n: int = 6
    n += 3
    n -= 1
    n *= 2
    n //= 3
    n %= 5
    n **= 2
    first, second = ("input", "loss")
    if (length := len(first)) > 0:
        return {"final": n, "unpacked": (first, second), "walrus": length}
    raise AssertionError("unreachable")


def operator_examples() -> dict[str, object]:
    a, b = 7, 3
    obj, other = object(), object()
    alias = obj
    members = ("material", "water")
    optional = None
    return {
        "arithmetic": {
            "add": a + b, "subtract": a - b, "multiply": a * b,
            "divide": a / b, "floor": a // b, "mod": a % b,
            "power": a ** b, "unary_plus": +b, "unary_minus": -b,
        },
        "comparison": {
            "equal": a == b, "not_equal": a != b, "greater": a > b,
            "less": a < b, "at_least": a >= b, "at_most": a <= b,
            "chained": 0 < b < a,
        },
        "logic": {
            "and": True and False, "or": True or False,
            "not": not False, "xor_boolean": True != False,
            "fallback": "" or "fallback",
        },
        "membership": {
            "in": "water" in members, "not_in": "energy" not in members,
        },
        "identity": {
            "is": alias is obj, "is_not": other is not obj,
            "none": optional is None,
        },
        "bitwise": {
            "and": a & b, "or": a | b, "xor": a ^ b,
            "invert": ~a, "left_shift": a << 1, "right_shift": a >> 1,
        },
    }


def classify_state(value: int | None) -> str:
    """match/case preserves UNKNOWN versus MEASURED_ZERO."""
    match value:
        case None:
            return "UNKNOWN"
        case 0:
            return "MEASURED_ZERO"
        case int() if value > 0:
            return "POSITIVE"
        case int():
            return "NEGATIVE"
        case _:
            raise TypeError("Expected int | None")


@dataclass(frozen=True)
class Observation:
    case_id: str
    value: float | None


def known_values(observations: Sequence[Observation]) -> Iterator[float]:
    """yield is a generator, not an aggregation policy."""
    for observation in observations:
        if observation.value is not None:
            yield observation.value


def decorate_result(fn: Callable[P, T]) -> Callable[P, T]:
    @wraps(fn)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        return fn(*args, **kwargs)
    return wrapper


@decorate_result
def square(x: int) -> int:
    return x * x


async def async_label(case_id: str) -> str:
    """Coroutine returned by async def; await it in an event loop."""
    return f"case:{case_id}"
