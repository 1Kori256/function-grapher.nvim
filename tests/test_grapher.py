import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'python'))

from analyzer import DependencyResolver, FunctionAnalyzer
from graph_renderer import ASCIIGraphRenderer


class AnalyzerTests(unittest.TestCase):
    def analyze(self, source):
        analyzer = FunctionAnalyzer('example.py')
        analyzer.analyze(textwrap.dedent(source))
        return analyzer

    def test_builtins_and_standard_library_are_filtered(self):
        analyzer = self.analyze('''
            def process():
                print(len(sorted(load())))
                json.dumps({})
        ''')
        self.assertEqual(analyzer.functions['process'], {'load'})

    def test_nested_bodies_belong_to_their_own_function(self):
        analyzer = self.analyze('''
            def outer():
                @decorate(factory())
                def inner(value=default()):
                    hidden()
                callback = lambda value=fallback(): deferred()
                return inner()
        ''')
        self.assertEqual(analyzer.functions['outer'],
                         {'decorate', 'factory', 'default', 'fallback', 'inner'})
        self.assertEqual(analyzer.functions['inner'], {'hidden'})

    def test_async_calls_and_locations(self):
        analyzer = self.analyze('''\
            async def process():
                return await fetch()
        ''')
        self.assertEqual(analyzer.functions['process'], {'fetch'})
        self.assertEqual(analyzer.function_lines['process'], (1, 2))

    def test_reanalysis_clears_old_definitions(self):
        analyzer = self.analyze('def old(): pass')
        analyzer.analyze('def new(): pass')
        self.assertEqual(set(analyzer.functions), {'new'})


class ResolverTests(unittest.TestCase):
    def setUp(self):
        self.resolver = DependencyResolver('.')
        self.resolver.all_functions = {
            'main': {'a', 'shared'}, 'a': {'b'}, 'b': {'shared'},
            'shared': {'leaf'}, 'leaf': set(),
        }

    def test_shared_function_uses_shortest_distance(self):
        graph = self.resolver.get_dependencies('main', 2)
        self.assertEqual(graph['shared'], {'leaf'})
        self.assertEqual(graph['b'], set())
        self.assertEqual(graph['leaf'], set())

    def test_zero_depth_only_includes_root(self):
        self.assertEqual(self.resolver.get_dependencies('main', 0), {'main': set()})

    def test_cycle_terminates(self):
        self.resolver.all_functions = {'main': {'main'}}
        self.assertEqual(self.resolver.get_dependencies('main'), {'main': {'main'}})

    def test_missing_function_and_negative_depth_fail(self):
        with self.assertRaisesRegex(ValueError, 'Function not found'):
            self.resolver.get_dependencies('missing')
        with self.assertRaisesRegex(ValueError, 'non-negative'):
            self.resolver.get_dependencies('main', -1)

    def test_declared_source_encoding(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'encoded.py'
            path.write_bytes(b'# coding: latin-1\ndef main():\n    "caf\xe9"\n    helper()\n')
            self.resolver = DependencyResolver(directory)
            self.resolver.scan_file(path)
            self.assertEqual(self.resolver.all_functions['main'], {'helper'})
            self.assertEqual(self.resolver.function_locations['main'], (str(path), 2, 4))


class RendererTests(unittest.TestCase):
    def setUp(self):
        self.renderer = ASCIIGraphRenderer()
        self.graph = {'main': {'left', 'right'}, 'left': {'shared'},
                      'right': {'shared'}, 'shared': set()}

    def test_tree_distinguishes_shared_calls_from_cycles(self):
        self.assertEqual(self.renderer.render_tree(self.graph, 'main'),
                         'main\n├── left\n│   └── shared\n└── right\n    └── shared (shared)')

    def test_list_distinguishes_shared_calls_from_cycles(self):
        result = self.renderer.render_list(self.graph, 'main')
        self.assertIn('    → shared (shared)', result)
        self.assertNotIn('(circular)', result)

    def test_real_cycle_is_marked_in_both_styles(self):
        graph = {'main': {'helper'}, 'helper': {'main'}}
        for render in (self.renderer.render_tree, self.renderer.render_list):
            with self.subTest(style=render.__name__):
                self.assertIn('main (circular)', render(graph, 'main'))

    def test_depth_limit_applies_to_each_rendered_path(self):
        graph = {'main': {'a', 'shared'}, 'a': {'shared'}, 'shared': {'leaf'}, 'leaf': set()}
        result = self.renderer.render_tree(graph, 'main', max_depth=2)
        self.assertIn('│   └── shared (depth limit)', result)
        self.assertIn('└── shared\n    └── leaf', result)
        self.assertNotIn('        └── leaf', result)

    def test_deep_graph_is_not_silently_cut_off(self):
        graph = {str(index): {str(index + 1)} for index in range(1100)}
        for render in (self.renderer.render_tree, self.renderer.render_list):
            with self.subTest(style=render.__name__):
                self.assertTrue(render(graph, '0').endswith('1100'))

    def test_summary_excludes_root_from_dependency_count(self):
        graph = {'main': {'helper'}, 'helper': {'main', 'external'}}
        result = self.renderer.render_summary(graph, 'main')
        self.assertIn('Direct dependencies: 1', result)
        self.assertIn('Total dependencies: 2', result)


class CLITests(unittest.TestCase):
    def run_cli(self, *args, env=None):
        return subprocess.run([sys.executable, str(ROOT / 'python/function_grapher.py'), *args],
                              text=True, capture_output=True, env=env)

    def test_example_and_location_protocol(self):
        result = self.run_cli(str(ROOT / 'examples/pipeline.py'), 'main')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('summarize (shared)', result.stdout)
        locations = json.loads(result.stderr.removeprefix('__LOCATIONS__'))['locations']
        self.assertEqual(locations['main']['line'], 23)
        self.assertTrue(Path(locations['main']['file']).is_file())

    def test_json_is_stable_across_hash_seeds(self):
        outputs = []
        for seed in ('1', '42', '100'):
            result = self.run_cli(str(ROOT / 'examples/pipeline.py'), 'main', '--json',
                                  env=dict(os.environ, PYTHONHASHSEED=seed))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stderr, '')
            outputs.append(result.stdout)
        self.assertEqual(len(set(outputs)), 1)
        self.assertEqual(json.loads(outputs[0])['dependencies']['main'],
                         ['process_data', 'save_report'])

    def test_cli_rejects_invalid_input_without_tracebacks(self):
        example = str(ROOT / 'examples/pipeline.py')
        cases = [(example, 'missing'), (example, 'main', '--max-depth=-1'),
                 (example, 'main', '--max-depth=no'), (example, 'main', '--style=bad'),
                 (example, 'main', '--unknown'), (example + '.missing', 'main')]
        for args in cases:
            with self.subTest(args=args):
                result = self.run_cli(*args)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(result.stdout, '')
                self.assertNotIn('Traceback', result.stderr)

    def test_syntax_errors_fail_instead_of_returning_empty_graphs(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'broken.py'
            path.write_text('def broken(:')
            result = self.run_cli(str(path), 'broken')
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, '')
        self.assertNotIn('Traceback', result.stderr)
        self.assertIn('broken.py', result.stderr)

    def test_zero_depth_cli(self):
        result = self.run_cli(str(ROOT / 'examples/pipeline.py'), 'main', '--max-depth', '0')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, 'main\n')


if __name__ == '__main__':
    unittest.main()
