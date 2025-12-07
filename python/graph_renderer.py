#!/usr/bin/env python3

from typing import Dict, Set
from collections import deque


class ASCIIGraphRenderer:

    def __init__(self, compact: bool = False):
        self.compact = compact

    def render_tree(self, dependencies: Dict[str, Set[str]], root: str) -> str:
        if root not in dependencies:
            return f"{root}\n(No dependencies found)"

        lines = [root]
        visited = {root}

        def render_node(node: str, prefix: str, is_last: bool, depth: int = 0):
            if depth > 20:
                return

            if node not in dependencies:
                return

            deps = sorted(dependencies[node])

            for i, dep in enumerate(deps):
                is_last_child = (i == len(deps) - 1)

                if is_last_child:
                    connector = "└── "
                    extension = "    "
                else:
                    connector = "├── "
                    extension = "│   "

                if dep in visited:
                    lines.append(f"{prefix}{connector}{dep} (circular)")
                else:
                    lines.append(f"{prefix}{connector}{dep}")
                    visited.add(dep)
                    render_node(dep, prefix + extension, is_last_child, depth + 1)

        render_node(root, "", True)
        return "\n".join(lines)

    def render_list(self, dependencies: Dict[str, Set[str]], root: str) -> str:
        if root not in dependencies:
            return f"{root}\n  (No dependencies found)"

        lines = [root]
        visited = {root}

        def render_deps(node: str, indent: int):
            if indent > 20 or node not in dependencies:
                return

            deps = sorted(dependencies[node])
            prefix = "  " * indent + "→ "

            for dep in deps:
                if dep in visited:
                    lines.append(f"{prefix}{dep} (circular)")
                else:
                    lines.append(f"{prefix}{dep}")
                    visited.add(dep)
                    render_deps(dep, indent + 1)

        render_deps(root, 1)
        return "\n".join(lines)

    def render_summary(self, dependencies: Dict[str, Set[str]], root: str) -> str:
        if root not in dependencies:
            return f"Function: {root}\nNo dependencies found."

        total_deps = set()

        def collect_deps(node: str, visited: Set[str]):
            if node in visited or node not in dependencies:
                return
            visited.add(node)
            for dep in dependencies[node]:
                total_deps.add(dep)
                collect_deps(dep, visited)

        collect_deps(root, set())

        direct_deps = dependencies.get(root, set())

        lines = [
            f"Function: {root}",
            f"Direct dependencies: {len(direct_deps)}",
            f"Total dependencies: {len(total_deps)}",
            "",
            "Dependency tree:"
        ]

        tree = self.render_tree(dependencies, root)
        lines.append(tree)

        return "\n".join(lines)
