#!/usr/bin/env python3

import ast
import builtins
import sys
import tokenize
from collections import deque
from pathlib import Path
from typing import Set, Dict, Tuple, Optional


class FunctionCallVisitor(ast.NodeVisitor):

    def __init__(self):
        self.calls: Set[str] = set()

    # Defining a function does not execute its body in the enclosing function.
    def visit_FunctionDef(self, node):
        for expression in node.decorator_list + node.args.defaults + node.args.kw_defaults:
            if expression is not None:
                self.visit(expression)

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Lambda(self, node):
        for expression in node.args.defaults + node.args.kw_defaults:
            if expression is not None:
                self.visit(expression)

    def visit_Call(self, node):
        call_name = self._get_call_name(node.func)
        if call_name:
            self.calls.add(call_name)
        self.generic_visit(node)

    def _get_call_name(self, node) -> Optional[str]:
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            parts = []
            current = node
            while isinstance(current, ast.Attribute):
                parts.append(current.attr)
                current = current.value
            if isinstance(current, ast.Name):
                parts.append(current.id)
            return '.'.join(reversed(parts))
        return None


class FunctionAnalyzer(ast.NodeVisitor):

    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        self.functions: Dict[str, Set[str]] = {}
        self.function_lines: Dict[str, Tuple[int, int]] = {}
        self.stdlib_modules = self._get_stdlib_modules()

    def _get_stdlib_modules(self) -> Set[str]:
        import sys
        stdlib = set(sys.stdlib_module_names) if hasattr(sys, 'stdlib_module_names') else set()
        common_stdlib = {
            'os', 'sys', 'math', 'random', 'json', 're', 'datetime', 'collections',
            'itertools', 'functools', 'pathlib', 'typing', 'dataclasses', 'enum',
            'io', 'subprocess', 'threading', 'multiprocessing', 'asyncio', 'time',
            'copy', 'pickle', 'csv', 'sqlite3', 'logging', 'argparse', 'unittest',
            'tempfile', 'shutil', 'glob', 'fnmatch', 'zipfile', 'tarfile', 'gzip',
            'hashlib', 'hmac', 'secrets', 'uuid', 'socket', 'urllib', 'http',
            'email', 'base64', 'binascii', 'struct', 'array', 'weakref', 'abc',
            'contextlib', 'warnings', 'traceback', 'inspect', 'importlib'
        }
        return stdlib | common_stdlib

    def visit_FunctionDef(self, node):
        func_name = node.name
        end_line = node.end_lineno if hasattr(node, 'end_lineno') else node.lineno
        self.function_lines[func_name] = (node.lineno, end_line)

        visitor = FunctionCallVisitor()
        for stmt in node.body:
            visitor.visit(stmt)

        filtered_calls = self._filter_calls(visitor.calls)
        self.functions[func_name] = filtered_calls
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node):
        self.visit_FunctionDef(node)

    def _filter_calls(self, calls: Set[str]) -> Set[str]:
        filtered = set()
        for call in calls:
            base_module = call.split('.')[0]
            if base_module in self.stdlib_modules or base_module in vars(builtins):
                continue
            filtered.add(call)
        return filtered

    def analyze(self, source_code: str):
        tree = ast.parse(source_code, filename=str(self.file_path))
        self.functions.clear()
        self.function_lines.clear()
        self.visit(tree)


class DependencyResolver:

    def __init__(self, root_path: str):
        self.root_path = Path(root_path)
        self.all_functions: Dict[str, Set[str]] = {}
        self.function_locations: Dict[str, Tuple[str, int, int]] = {}

    def scan_file(self, file_path: Path):
        with tokenize.open(file_path) as source_file:
            source = source_file.read()

        analyzer = FunctionAnalyzer(str(file_path))
        analyzer.analyze(source)

        for func_name, deps in analyzer.functions.items():
            qualified_name = f"{file_path.stem}.{func_name}"
            start, end = analyzer.function_lines[func_name]
            location = (str(file_path), start, end)
            self.all_functions[qualified_name] = deps
            self.function_locations[qualified_name] = location
            if func_name not in self.all_functions:
                self.all_functions[func_name] = deps
                self.function_locations[func_name] = location

    def scan_directory(self):
        if not self.root_path.exists():
            raise FileNotFoundError(f"Path does not exist: {self.root_path}")
        if self.root_path.is_file():
            self.scan_file(self.root_path)
        else:
            for py_file in sorted(self.root_path.rglob('*.py')):
                if '__pycache__' not in py_file.parts:
                    self.scan_file(py_file)

    def get_dependencies(self, function_name: str, max_depth: int = 10) -> Dict[str, Set[str]]:
        if max_depth < 0:
            raise ValueError("Maximum depth must be non-negative")
        if function_name not in self.all_functions:
            raise ValueError(f"Function not found: {function_name}")

        result = {}
        visited = set()
        pending = deque([(function_name, 0)])
        # Breadth-first traversal reaches shared dependencies by their shortest path.
        while pending:
            func, depth = pending.popleft()
            if func in visited:
                continue
            visited.add(func)
            if func in self.all_functions:
                deps = set(self.all_functions[func]) if depth < max_depth else set()
                result[func] = deps
                pending.extend((dep, depth + 1) for dep in sorted(deps))
        return result
