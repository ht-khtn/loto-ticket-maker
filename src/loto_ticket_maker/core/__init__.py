"""Core logic: models + generator + rules."""

from .loto_15x6 import generate_loto_15x6
from .loto_3x9 import generate_loto_3x9

__all__ = ["generate_loto_15x6", "generate_loto_3x9"]
