local function check()
  vim.opt.runtimepath:prepend(vim.fn.getcwd())
  local grapher = require('function-grapher')
  grapher.setup({ window = { width = 40 } })
  vim.cmd('edit examples/pipeline.py')
  vim.bo.filetype = 'python'

  local function graph(style)
    grapher.config.style = style
    vim.cmd('FunctionGraph main')
    assert(vim.wait(10000, function()
      for _, win in ipairs(vim.api.nvim_list_wins()) do
        local buf = vim.api.nvim_win_get_buf(win)
        if vim.bo[buf].filetype == 'funcgraph' then
          local lines = vim.api.nvim_buf_get_lines(buf, 0, -1, false)
          if lines[1] == (style == 'summary' and 'Function: main' or 'main') then
            return true
          end
        end
      end
      return false
    end, 20), 'graph job timed out')

    for _, win in ipairs(vim.api.nvim_list_wins()) do
      local buf = vim.api.nvim_win_get_buf(win)
      if vim.bo[buf].filetype == 'funcgraph' then
        vim.api.nvim_set_current_win(win)
        return buf
      end
    end
    error('graph window missing')
  end

  for _, style in ipairs({ 'tree', 'list', 'summary' }) do
    local buf = graph(style)
    local lines = vim.api.nvim_buf_get_lines(buf, 0, -1, false)
    local target
    for index, line in ipairs(lines) do
      if line:find('summarize (shared)', 1, true) then
        target = index
      end
    end
    assert(target, 'shared dependency missing in ' .. style)
    vim.api.nvim_win_set_cursor(0, { target, 0 })
    local enter
    for _, map in ipairs(vim.api.nvim_buf_get_keymap(buf, 'n')) do
      if map.lhs == '<CR>' then enter = map.callback end
    end
    assert(enter, 'jump mapping missing')
    enter()
    assert(vim.fn.expand('%:t') == 'pipeline.py', 'jump opened wrong file')
    assert(vim.api.nvim_win_get_cursor(0)[1] == 9, 'jump landed on wrong line')
  end

  -- Enough metadata to cross job callback chunk boundaries.
  local temporary = vim.fn.tempname() .. '.py'
  local source = { 'def main():', '    return helper()', '', 'def helper():', '    pass' }
  for index = 1, 600 do
    table.insert(source, 'def extra_' .. index .. '(): pass')
  end
  vim.fn.writefile(source, temporary)
  vim.cmd('edit ' .. vim.fn.fnameescape(temporary))
  vim.bo.filetype = 'python'
  local buf = graph('tree')
  local lines = vim.api.nvim_buf_get_lines(buf, 0, -1, false)
  assert(lines[2] == '└── helper', 'large metadata graph missing')
  vim.api.nvim_win_set_cursor(0, { 2, 0 })
  for _, map in ipairs(vim.api.nvim_buf_get_keymap(buf, 'n')) do
    if map.lhs == '<CR>' then map.callback() end
  end
  assert(vim.api.nvim_win_get_cursor(0)[1] == 4, 'large metadata lost local locations')
  vim.fn.delete(temporary)

  -- An older job finishing late must not replace a newer graph.
  vim.cmd('edit examples/pipeline.py')
  vim.bo.filetype = 'python'
  local jobs = {}
  local original_jobstart = vim.fn.jobstart
  vim.fn.jobstart = function(_, options)
    assert(options.stdout_buffered and options.stderr_buffered, 'job output must be buffered')
    table.insert(jobs, options)
    return #jobs
  end
  vim.cmd('FunctionGraph main')
  vim.cmd('FunctionGraph summarize')
  vim.fn.jobstart = original_jobstart
  jobs[2].on_stdout(2, { 'summarize', '' })
  jobs[2].on_stderr(2, { '__LOCATIONS__' .. vim.json.encode({
    locations = { summarize = { file = vim.fn.expand('%:p'), line = 9, end_line = 10 } },
  }), '' })
  jobs[2].on_exit(2, 0)
  jobs[1].on_stdout(1, { 'main', '' })
  jobs[1].on_exit(1, 0)
  for _, win in ipairs(vim.api.nvim_list_wins()) do
    local graph_buf = vim.api.nvim_win_get_buf(win)
    if vim.bo[graph_buf].filetype == 'funcgraph' then
      assert(vim.api.nvim_buf_get_lines(graph_buf, 0, 1, false)[1] == 'summarize',
        'stale job replaced newer output')
    end
  end
end

local ok, error_message = pcall(check)
if not ok then
  io.stderr:write(tostring(error_message) .. '\n')
  vim.cmd('cquit 1')
else
  print('Neovim integration checks passed')
  vim.cmd('qa!')
end
