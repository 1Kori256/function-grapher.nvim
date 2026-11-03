#!/usr/bin/env python3

from typing import Dict, Set


class ASCIIGraphRenderer:

    def _render(self, dependencies: Dict[str, Set[str]], root: str, tree: bool, max_depth=None) -> str:
        if root not in dependencies:
            return f'{root}\n(No dependencies found)'

        lines = []
        expanded = set()
        # A path detects recursion; expanded tracks nodes already shown elsewhere.
        pending = [(root, '', '', frozenset(), 0)]
        while pending:
            node, prefix, connector, ancestors, depth = pending.pop()
            if node in ancestors:
                lines.append(f'{prefix}{connector}{node} (circular)')
                continue
            if node in expanded:
                lines.append(f'{prefix}{connector}{node} (shared)')
                continue

            children = sorted(dependencies.get(node, set()))
            if children and max_depth is not None and depth >= max_depth:
                lines.append(f'{prefix}{connector}{node} (depth limit)')
                continue
            lines.append(f'{prefix}{connector}{node}')
            expanded.add(node)
            child_prefix = prefix
            if connector:
                if tree:
                    child_prefix += '    ' if connector == '└── ' else '│   '
                else:
                    child_prefix += '  '
            elif not tree:
                child_prefix = '  '
            for index in range(len(children) - 1, -1, -1):
                if tree:
                    child_connector = '└── ' if index == len(children) - 1 else '├── '
                else:
                    child_connector = '→ '
                pending.append((children[index], child_prefix, child_connector, ancestors | {node}, depth + 1))

        return '\n'.join(lines)

    def render_tree(self, dependencies: Dict[str, Set[str]], root: str, max_depth=None) -> str:
        return self._render(dependencies, root, tree=True, max_depth=max_depth)

    def render_list(self, dependencies: Dict[str, Set[str]], root: str, max_depth=None) -> str:
        return self._render(dependencies, root, tree=False, max_depth=max_depth)

    def render_summary(self, dependencies: Dict[str, Set[str]], root: str, max_depth=None) -> str:
        if root not in dependencies:
            return f'Function: {root}\nNo dependencies found.'

        reachable = set()
        pending = [root]
        while pending:
            node = pending.pop()
            if node in reachable:
                continue
            reachable.add(node)
            pending.extend(dependencies.get(node, set()) - reachable)
        reachable.discard(root)

        return '\n'.join([
            f'Function: {root}',
            f'Direct dependencies: {len(dependencies[root])}',
            f'Total dependencies: {len(reachable)}',
            '',
            'Dependency tree:',
            self.render_tree(dependencies, root, max_depth=max_depth),
        ])
