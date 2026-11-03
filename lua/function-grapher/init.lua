local M = {}

M.config = {
  max_depth = 10,
  style = 'tree',
  python_cmd = 'python3',
  window = {
    position = 'right',
    width = 60,
    height = 20,
  },
  highlight = {
    enabled = true,
  }
}

local function get_python_path()
  local source = debug.getinfo(1, "S").source:sub(2)
  local plugin_dir = vim.fn.fnamemodify(source, ":h:h:h")
  return plugin_dir .. "/python"
end

local location_metadata = {}
local source_file_path = nil
local output_buf = nil
local output_win = nil
local request_id = 0

local function run_analyzer(file_path, function_name, callback)
  local python_path = get_python_path()
  local script_path = python_path .. "/function_grapher.py"

  local args = {
    M.config.python_cmd,
    script_path,
    file_path,
    function_name,
    "--style=" .. M.config.style,
    "--max-depth=" .. M.config.max_depth,
  }

  local output = {}
  local stderr_output = {}
  local locations = {}
  local job_id = vim.fn.jobstart(args, {
    stdout_buffered = true,
    stderr_buffered = true,
    on_stdout = function(_, data, _)
      for _, line in ipairs(data) do
        table.insert(output, line)
      end
      if output[#output] == '' then
        table.remove(output)
      end
    end,
    on_stderr = function(_, data, _)
      for _, line in ipairs(data) do
        if line ~= "" then
          if line:match("^__LOCATIONS__") then
            local json_str = line:sub(14)
            local ok, decoded = pcall(vim.json.decode, json_str)
            if ok then
              locations = decoded.locations or {}
            end
          else
            table.insert(stderr_output, line)
          end
        end
      end
    end,
    on_exit = function(_, exit_code, _)
      if exit_code == 0 then
        callback(output, locations)
      else
        for _, err in ipairs(stderr_output) do
          vim.notify("Function Grapher: " .. err, vim.log.levels.ERROR)
        end
        vim.notify("Function Grapher failed with exit code " .. exit_code, vim.log.levels.ERROR)
      end
    end,
  })

  if job_id <= 0 then
    vim.notify("Failed to start Function Grapher", vim.log.levels.ERROR)
  end
end

local function create_output_window()
  if not output_buf or not vim.api.nvim_buf_is_valid(output_buf) then
    output_buf = vim.api.nvim_create_buf(false, true)
    vim.api.nvim_buf_set_option(output_buf, 'buftype', 'nofile')
    vim.api.nvim_buf_set_option(output_buf, 'bufhidden', 'hide')
    vim.api.nvim_buf_set_option(output_buf, 'swapfile', false)
    vim.api.nvim_buf_set_name(output_buf, "Function Dependency Graph")
  end

  if output_win and vim.api.nvim_win_is_valid(output_win) then
    vim.api.nvim_win_close(output_win, true)
  end

  local win_config = M.config.window

  if win_config.position == 'float' then
    local width = win_config.width
    local height = win_config.height
    local row = math.floor((vim.o.lines - height) / 2)
    local col = math.floor((vim.o.columns - width) / 2)

    output_win = vim.api.nvim_open_win(output_buf, true, {
      relative = 'editor',
      width = width,
      height = height,
      row = row,
      col = col,
      style = 'minimal',
      border = 'rounded',
    })
  else
    local cmd
    if win_config.position == 'right' then
      cmd = 'vertical rightbelow '
    elseif win_config.position == 'left' then
      cmd = 'vertical leftabove '
    elseif win_config.position == 'below' then
      cmd = 'rightbelow '
    else
      cmd = 'leftabove '
    end

    if win_config.position == 'right' or win_config.position == 'left' then
      cmd = cmd .. win_config.width .. 'split'
    else
      cmd = cmd .. win_config.height .. 'split'
    end

    vim.cmd(cmd)
    output_win = vim.api.nvim_get_current_win()
    vim.api.nvim_win_set_buf(output_win, output_buf)
  end

  vim.api.nvim_win_set_option(output_win, 'wrap', false)
  vim.api.nvim_win_set_option(output_win, 'number', false)
  vim.api.nvim_win_set_option(output_win, 'relativenumber', false)

  local opts = { noremap = true, silent = true, buffer = output_buf }
  vim.keymap.set('n', 'q', function()
    if output_win and vim.api.nvim_win_is_valid(output_win) then
      vim.api.nvim_win_close(output_win, true)
    end
  end, opts)

  return output_buf, output_win
end

local function extract_function_from_line(line)
  local cleaned = line:gsub('├── ', ''):gsub('└── ', ''):gsub('│', ''):gsub('→ ', '')
  cleaned = cleaned:gsub('%s*%(circular%)', ''):gsub('%s*%(shared%)', '')
  cleaned = cleaned:gsub('%s*%(depth limit%)', '')
  local func_name = cleaned:match('^%s*([^%s()]+)%s*$')
  return func_name
end

local function jump_to_definition()
  local line = vim.api.nvim_get_current_line()
  local func_name = extract_function_from_line(line)

  if not func_name or func_name == "" then
    vim.notify("No function found on this line", vim.log.levels.WARN)
    return
  end

  if output_win and vim.api.nvim_win_is_valid(output_win) then
    vim.api.nvim_win_close(output_win, true)
  end

  local location = location_metadata[func_name]

  if location then
    vim.cmd('edit ' .. vim.fn.fnameescape(location.file))
    vim.api.nvim_win_set_cursor(0, {location.line, 0})
    vim.cmd('normal! zz')
    vim.notify("Jumped to: " .. func_name .. ":" .. location.line, vim.log.levels.INFO)
    return
  end

  if not source_file_path or not vim.fn.filereadable(source_file_path) then
    vim.notify("Source file not available for LSP lookup", vim.log.levels.WARN)
    return
  end

  vim.cmd('edit ' .. vim.fn.fnameescape(source_file_path))

  local found = vim.fn.search('\\<' .. func_name .. '\\>', 'w')

  if found == 0 then
    vim.notify("Could not find function call: " .. func_name, vim.log.levels.WARN)
    return
  end

  local params = vim.lsp.util.make_position_params()

  vim.lsp.buf_request(0, 'textDocument/definition', params, function(err, result, ctx, config)
    vim.schedule(function()
      if err then
        vim.notify("LSP error: " .. tostring(err.message), vim.log.levels.ERROR)
        return
      end

      if not result or vim.tbl_isempty(result) then
        vim.notify("LSP could not find definition for: " .. func_name, vim.log.levels.WARN)
        return
      end

      local target
      if vim.tbl_islist(result) then
        target = result[1]
      else
        target = result
      end

      local uri = target.uri or target.targetUri
      local range = target.range or target.targetSelectionRange
      local filepath = vim.uri_to_fname(uri)
      local line_num = range.start.line + 1

      vim.cmd('edit ' .. vim.fn.fnameescape(filepath))
      vim.api.nvim_win_set_cursor(0, {line_num, 0})
      vim.cmd('normal! zz')

      local msg = "Jumped to: " .. func_name .. " (" .. filepath .. ":" .. line_num .. ")"
      if vim.tbl_islist(result) and #result > 1 then
        msg = msg .. " [1/" .. #result .. " matches]"
      end
      vim.notify(msg, vim.log.levels.INFO)
    end)
  end)
end

local function display_output(lines, locations)
  local buf, win = create_output_window()

  location_metadata = locations or {}

  vim.api.nvim_buf_set_option(buf, 'modifiable', true)
  vim.api.nvim_buf_set_lines(buf, 0, -1, false, lines)
  vim.api.nvim_buf_set_option(buf, 'modifiable', false)
  vim.api.nvim_buf_set_option(buf, 'modified', false)
  vim.api.nvim_buf_set_option(buf, 'filetype', 'funcgraph')

  local opts = { noremap = true, silent = true, buffer = buf }
  vim.keymap.set('n', '<CR>', jump_to_definition, opts)

  if M.config.window.position ~= 'float' then
    vim.cmd('wincmd p')
  end
end

local function get_function_name_under_cursor()
  local line = vim.api.nvim_get_current_line()
  local col = vim.api.nvim_win_get_cursor(0)[2]

  local has_ts, ts_utils = pcall(require, 'nvim-treesitter.ts_utils')
  if has_ts then
    local node = ts_utils.get_node_at_cursor()
    while node do
      if node:type() == 'function_definition' then
        for child in node:iter_children() do
          if child:type() == 'identifier' then
            return vim.treesitter.get_node_text(child, 0)
          end
        end
      end
      node = node:parent()
    end
  end

  local before = line:sub(1, col + 1)
  local after = line:sub(col + 1)

  local func_name = before:match('def%s+([%w_]+)') or after:match('^([%w_]+)')

  if not func_name then
    func_name = vim.fn.expand('<cword>')
  end

  return func_name
end

function M.graph_function(args)
  local function_name = args.args

  if function_name == "" then
    function_name = get_function_name_under_cursor()
    if not function_name or function_name == "" then
      vim.notify("No function name provided or found under cursor", vim.log.levels.ERROR)
      return
    end
  end

  local file_path = vim.fn.expand('%:p')

  if vim.bo.filetype ~= 'python' then
    vim.notify("Function Grapher only works with Python files", vim.log.levels.WARN)
    return
  end

  vim.notify("Analyzing function: " .. function_name .. "...", vim.log.levels.INFO)

  request_id = request_id + 1
  local current_request = request_id
  run_analyzer(file_path, function_name, function(output, locations)
    if current_request ~= request_id then
      return
    end
    source_file_path = file_path
    display_output(output, locations)
  end)
end

function M.setup(opts)
  M.config = vim.tbl_deep_extend('force', M.config, opts or {})

  vim.api.nvim_create_user_command('FunctionGraph', M.graph_function, {
    nargs = '?',
    desc = 'Graph function dependencies',
  })

  vim.api.nvim_create_user_command('FunctionGraphSetStyle', function(args)
    local style = args.args
    if style == 'tree' or style == 'list' or style == 'summary' then
      M.config.style = style
      vim.notify("Function Grapher style: " .. style, vim.log.levels.INFO)
    else
      vim.notify("Invalid style. Use: tree, list, or summary", vim.log.levels.ERROR)
    end
  end, {
    nargs = 1,
    complete = function() return {'tree', 'list', 'summary'} end,
    desc = 'Set graph display style',
  })
end

return M
