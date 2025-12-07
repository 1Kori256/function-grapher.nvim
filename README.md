# function-grapher.nvim

A Neovim plugin for visualizing Python function dependencies using AST analysis and ASCII graph rendering.

![License](https://img.shields.io/badge/license-MIT-blue.svg)

## Features

- 📊 **AST-based Analysis**: Uses Python's built-in AST module for accurate dependency extraction
- 🎨 **ASCII Visualization**: Clean tree-based dependency graphs
- 🔍 **Smart Filtering**: Default mode excludes standard library calls
- ⚡ **Async Execution**: Non-blocking analysis using Neovim's job control
- 🎯 **LSP Integration**: Jump to definitions using LSP (supports venv packages)
- 🪟 **Flexible Display**: Multiple window positioning options

## Requirements

- Neovim >= 0.7.0
- Python 3.6+
- LSP server (pylsp or pyright) for jump-to-definition

## Installation

### [lazy.nvim](https://github.com/folke/lazy.nvim)

```lua
{
  '1Kori256/function-grapher.nvim',
  config = function()
    require('function-grapher').setup()
  end,
}
```

### [packer.nvim](https://github.com/wbthomason/packer.nvim)

```lua
use {
  '1Kori256/function-grapher.nvim',
  config = function()
    require('function-grapher').setup()
  end
}
```

### [vim-plug](https://github.com/junegunn/vim-plug)

```vim
Plug '1Kori256/function-grapher.nvim'
```

Then in your `init.lua`:
```lua
require('function-grapher').setup()
```

## Usage

### Commands

#### `:FunctionGraph [function_name]`
Graph the dependencies of a function.

```vim
:FunctionGraph process_data  " Graph specific function
:FunctionGraph               " Graph function under cursor
```

#### `:FunctionGraphSetStyle <style>`
Set the visualization style: `tree`, `list`, or `summary`.

### Keymaps

Example configuration:

```lua
vim.keymap.set('n', '<leader>fg', ':FunctionGraph<CR>', { desc = 'Graph function' })
```

### Interactive Navigation

In the graph window:
- `j`/`k` - Navigate up/down
- `<Enter>` - Jump to function definition (uses LSP)
- `q` - Close the graph window

## Visualization

### Tree Style (Default)

```
main
├── process_data
│   ├── validate_input
│   └── transform
│       └── helper
└── save_results
    └── write_file
```

### List Style

```
main
  → process_data
    → validate_input
    → transform
      → helper
  → save_results
    → write_file
```

### Summary Style

```
Function: main
Direct dependencies: 2
Total dependencies: 5

Dependency tree:
main
├── process_data
│   ├── validate_input
│   └── transform
│       └── helper
└── save_results
    └── write_file
```

## Configuration

```lua
require('function-grapher').setup({
  max_depth = 10,
  style = 'tree',
  python_cmd = 'python3',
  window = {
    position = 'right',
    width = 60,
    height = 20,
  },
})
```

### Options

- `max_depth` - Maximum recursion depth for dependencies (default: `10`)
- `style` - Visualization style: `'tree'`, `'list'`, or `'summary'` (default: `'tree'`)
- `python_cmd` - Python executable to use (default: `'python3'`)
- `window.position` - Window position: `'right'`, `'left'`, `'below'`, `'above'`, `'float'` (default: `'right'`)
- `window.width` - Width for vertical splits (default: `60`)
- `window.height` - Height for horizontal splits (default: `20`)

**Note:** The plugin automatically filters out Python standard library and built-in functions to show only your code and third-party dependencies.

## How It Works

1. **AST Parsing**: Parses Python source using the `ast` module
2. **Dependency Extraction**: Walks the AST to find function calls
3. **Filtering**: Filters out stdlib and built-in functions
4. **Graph Building**: Recursively resolves dependencies
5. **Rendering**: Converts the graph to ASCII art
6. **LSP Integration**: Uses LSP for jump-to-definition functionality

## Python CLI

The plugin includes a standalone CLI tool:

```bash
cd python
python3 function_grapher.py myfile.py my_function
python3 function_grapher.py myfile.py my_function --style=summary
python3 function_grapher.py myfile.py my_function --max-depth=5
```

## License

MIT

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.
