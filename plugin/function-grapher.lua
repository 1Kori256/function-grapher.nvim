-- Auto-loaded plugin file for Function Grapher
-- This file is automatically sourced by Neovim

if vim.g.loaded_function_grapher then
  return
end
vim.g.loaded_function_grapher = 1

-- Default setup with empty config (user can override in their init.lua)
require('function-grapher').setup({})
