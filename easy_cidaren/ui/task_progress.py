"""Structured progress shared by the worker and the user interface."""

from dataclasses import dataclass


@dataclass(frozen = True)
class TaskProgress:
    done: int
    total: int
    right: int
    wrong: int
    skipped: int
    task_index: int
    task_total: int
    task_name: str
