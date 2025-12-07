#!/usr/bin/env python3

import sys
import json
from analyzer import DependencyResolver
from graph_renderer import ASCIIGraphRenderer


def main():
    if len(sys.argv) < 3:
        print("Usage: function_grapher.py <file> <function> [options]", file=sys.stderr)
        print("Options:", file=sys.stderr)
        print("  --style=<tree|list|summary>: Output style (default: tree)", file=sys.stderr)
        print("  --max-depth=N: Maximum recursion depth (default: 10)", file=sys.stderr)
        print("  --json: Output as JSON", file=sys.stderr)
        sys.exit(1)

    file_path = sys.argv[1]
    function_name = sys.argv[2]

    output_json = '--json' in sys.argv
    max_depth = 10
    style = 'tree'

    for arg in sys.argv[3:]:
        if arg.startswith('--max-depth='):
            max_depth = int(arg.split('=')[1])
        elif arg.startswith('--style='):
            style = arg.split('=')[1]

    resolver = DependencyResolver(file_path)
    resolver.scan_directory()

    dependencies = resolver.get_dependencies(function_name, max_depth)

    if output_json:
        output = {
            'function': function_name,
            'dependencies': {k: list(v) for k, v in dependencies.items()},
            'locations': resolver.function_locations
        }
        print(json.dumps(output, indent=2))
    else:
        renderer = ASCIIGraphRenderer()

        if style == 'tree':
            output = renderer.render_tree(dependencies, function_name)
        elif style == 'list':
            output = renderer.render_list(dependencies, function_name)
        elif style == 'summary':
            output = renderer.render_summary(dependencies, function_name)
        else:
            print(f"Unknown style: {style}", file=sys.stderr)
            sys.exit(1)

        print(output)

        location_data = {
            'locations': {k: {'file': v[0], 'line': v[1], 'end_line': v[2]}
                         for k, v in resolver.function_locations.items()}
        }
        print("__LOCATIONS__" + json.dumps(location_data), file=sys.stderr)


if __name__ == '__main__':
    main()
