"""Ngoại lệ domain cho app."""

from __future__ import annotations


class LotoError(Exception):
    pass


class LayoutError(LotoError):
    pass


class ExportCanceled(LotoError):
    pass
