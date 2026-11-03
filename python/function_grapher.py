#!/usr/bin/env python3

import argparse
import json
import sys

from analyzer import DependencyResolver
from graph_renderer import ASCIIGraphRenderer


def non_negative_int(value):
    number = int(value)
    if number < 0:
        raise argparse.ArgumentTypeError('must be non-negative')
    return number


def main(argv=None):
    parser = argparse.ArgumentParser(description='Graph Python function dependencies.')
    parser.add_argument('path', help='Python file or directory to scan')
    parser.add_argument('function', help='Function name, optionally prefixed by file stem')
    parser.add_argument('--style', choices=('tree', 'list', 'summary'), default='tree')
    parser.add_argument('--max-depth', type=non_negative_int, default=10,
                        help='Maximum call distance from the root (default: 10)')
    parser.add_argument('--json', action='store_true', help='Output graph and locations as JSON')
    args = parser.parse_args(argv)

    resolver = DependencyResolver(args.path)
    try:
        resolver.scan_directory()
        dependencies = resolver.get_dependencies(args.function, args.max_depth)
    except (OSError, UnicodeError, SyntaxError, ValueError) as error:
        parser.exit(1, f'{parser.prog}: {error}\n')

    if args.json:
        print(json.dumps({
            'function': args.function,
            'dependencies': {name: sorted(calls) for name, calls in dependencies.items()},
            'locations': resolver.function_locations,
        }, indent=2, sort_keys=True))
    else:
        renderer = ASCIIGraphRenderer()
        render = getattr(renderer, 'render_' + args.style)
        print(render(dependencies, args.function, max_depth=args.max_depth))
        location_data = {
            'locations': {name: {'file': loc[0], 'line': loc[1], 'end_line': loc[2]}
                          for name, loc in resolver.function_locations.items()}
        }
        print('__LOCATIONS__' + json.dumps(location_data, sort_keys=True), file=sys.stderr)
    return 0


if __name__ == '__main__':
    sys.exit(main())
