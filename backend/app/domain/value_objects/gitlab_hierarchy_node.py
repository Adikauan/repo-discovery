from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True, slots=True)
class GitLabHierarchyNode:
    id: int
    type: Literal["group", "repository"]
    name: str
    full_path: str
    parent_group_id: int | None = None
    expandable: bool = False

