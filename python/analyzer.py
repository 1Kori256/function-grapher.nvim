#!/usr/bin/env python3

import ast
import sys
from pathlib import Path
from typing import Set, Dict, Tuple, Optional


class FunctionCallVisitor(ast.NodeVisitor):

    def __init__(self):
        self.calls: Set[str] = set()
        self.depth = 0

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
            if base_module in self.stdlib_modules or base_module in dir(__builtins__):
                continue
            filtered.add(call)
        return filtered

    def analyze(self, source_code: str):
        try:
            tree = ast.parse(source_code)
            self.visit(tree)
        except SyntaxError as e:
            print(f"Syntax error in {self.file_path}: {e}", file=sys.stderr)
            raise


class DependencyResolver:

    def __init__(self, root_path: str):
        self.root_path = Path(root_path)
        self.all_functions: Dict[str, Set[str]] = {}
        self.function_locations: Dict[str, Tuple[str, int, int]] = {}

    def scan_file(self, file_path: Path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source = f.read()

            analyzer = FunctionAnalyzer(str(file_path))
            analyzer.analyze(source)

            for func_name, deps in analyzer.functions.items():
                qualified_name = f"{file_path.stem}.{func_name}"
                self.all_functions[qualified_name] = deps

                if func_name in analyzer.function_lines:
                    start, end = analyzer.function_lines[func_name]
                    self.function_locations[qualified_name] = (str(file_path), start, end)

            for func_name, deps in analyzer.functions.items():
                if func_name not in self.all_functions:
                    self.all_functions[func_name] = deps
                    if func_name in analyzer.function_lines:
                        start, end = analyzer.function_lines[func_name]
                        self.function_locations[func_name] = (str(file_path), start, end)

        except Exception as e:
            print(f"Error scanning {file_path}: {e}", file=sys.stderr)

    def scan_directory(self):
        if self.root_path.is_file():
            self.scan_file(self.root_path)
        else:
            for py_file in self.root_path.rglob('*.py'):
                if '__pycache__' not in str(py_file):
                    self.scan_file(py_file)

    def get_dependencies(self, function_name: str, max_depth: int = 10) -> Dict[str, Set[str]]:
        result = {}
        visited = set()

        def recurse(func: str, depth: int):
            if depth > max_depth or func in visited:
                return

            visited.add(func)

            if func in self.all_functions:
                deps = self.all_functions[func]
                result[func] = deps

                for dep in deps:
                    recurse(dep, depth + 1)

        recurse(function_name, 0)
        return result
