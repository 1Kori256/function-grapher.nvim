# function-grapher.nvim

Explore Python function calls without leaving Neovim. Uses Python's AST to build a
call graph, displayed in a split or floating window.

```text
main
├── process_data
│   ├── load_data
│   ├── normalize
│   └── summarize
└── save_report
    ├── load_data (shared)
    └── summarize (shared)
```

`(shared)` means the function appears elsewhere in the graph. `(circular)` marks
a call back to an ancestor. Built-ins and calls prefixed with standard-library
module names are hidden.

## Install

Requires Neovim 0.9+ and Python 3.10+. No Python packages needed.

With [lazy.nvim](https://github.com/folke/lazy.nvim):

```lua
{
  '1Kori256/function-grapher.nvim',
  opts = {},
}
```

Other plugin managers work too; call `require('function-grapher').setup()` to
configure the plugin.

## Use

Open a saved Python file, then run:

```vim
:FunctionGraph main
:FunctionGraph              " Name under the cursor
:FunctionGraphSetStyle list " tree, list, or summary
```

In the graph, use `j`/`k` to move, `<Enter>` to jump to a definition, and `q` to
close. Local definitions use recorded source locations; external calls require
an attached Python LSP server. Analysis runs asynchronously and reads saved files.

Optional keymap:

```lua
vim.keymap.set('n', '<leader>fg', '<cmd>FunctionGraph<CR>')
```

## Configure

```lua
require('function-grapher').setup({
  max_depth = 10,
  style = 'tree',
  python_cmd = 'python3',
  window = {
    position = 'right', -- left, below, above, or float
    width = 60,
    height = 20,
  },
})
```

`max_depth` limits call expansion; `0` shows only the root. Calls at the limit
may still have dependencies that are not displayed.

## CLI

From this repository:

```sh
python3 python/function_grapher.py examples/pipeline.py main
python3 python/function_grapher.py examples/pipeline.py main --style summary
python3 python/function_grapher.py examples/pipeline.py main --max-depth 2 --json
```

Text goes to stdout; source locations go to stderr with a `__LOCATIONS__` prefix
for the plugin. `--json` writes both to stdout. Invalid input exits nonzero.

## Limits

This is a static call graph, not an execution trace. Dynamic dispatch, import
aliases, and receiver types such as `self.method()` are not resolved. Duplicate
function or method names can be ambiguous. Directory scans accept `file.function`
as a root, but do not resolve imports between files. Standard-library filtering
uses names, so aliases and shadowed names can produce incorrect results.

## Development

```sh
python3 -m unittest discover -s tests -v
nvim -n --headless -u NONE -i NONE -c 'luafile tests/test_neovim.lua'
```

MIT license.
