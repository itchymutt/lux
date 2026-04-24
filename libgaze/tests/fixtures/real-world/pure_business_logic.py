"""
Pure business logic. No effects. Tests that libgaze doesn't false-positive on:
- string operations
- list/dict comprehensions
- class definitions with methods
- decorators
- type annotations that mention effectful modules
- math operations
- dataclasses
"""

from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class Priority(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3


@dataclass
class Task:
    title: str
    priority: Priority
    completed: bool = False
    tags: list[str] = field(default_factory=list)


@dataclass
class Sprint:
    name: str
    tasks: list[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> None:
        self.tasks.append(task)

    def complete_task(self, title: str) -> Optional[Task]:
        for task in self.tasks:
            if task.title == title:
                task.completed = True
                return task
        return None

    @property
    def progress(self) -> float:
        if not self.tasks:
            return 0.0
        done = sum(1 for t in self.tasks if t.completed)
        return done / len(self.tasks)

    def high_priority_incomplete(self) -> list[Task]:
        return [
            t for t in self.tasks
            if t.priority == Priority.HIGH and not t.completed
        ]


def format_progress(sprint: Sprint) -> str:
    pct = sprint.progress * 100
    remaining = len([t for t in sprint.tasks if not t.completed])
    return f"{sprint.name}: {pct:.0f}% done, {remaining} remaining"


def merge_sprints(a: Sprint, b: Sprint) -> Sprint:
    merged = Sprint(name=f"{a.name} + {b.name}")
    merged.tasks = a.tasks + b.tasks
    return merged


def calculate_velocity(sprints: list[Sprint]) -> float:
    if not sprints:
        return 0.0
    completed = sum(
        sum(1 for t in s.tasks if t.completed)
        for s in sprints
    )
    return completed / len(sprints)
