function dump(name, val)
  io.stderr:write("---- " .. name .. " ----\n")

  if type(val) == "table" then
    for k, v in pairs(val) do
      local out = type(v) == "table"
        and pandoc.utils.stringify(v)
        or tostring(v)

      io.stderr:write(tostring(k) .. " = " .. out .. "\n")
    end
  else
    io.stderr:write(tostring(val) .. "\n")
  end
end

local function stringify(x)
  return pandoc.utils.stringify(x)
end

-- resolve nested keys like "home.title"
local function resolve_key(tbl, key)
  local current = tbl
  for part in string.gmatch(key, "[^%.]+") do
    if type(current) ~= "table" then
      return nil
    end
    current = current[part]
    if current == nil then
      return nil
    end
  end
  return current
end

-- replace {var} with kwargs
local function interpolate(text, kwargs)
  return (text:gsub("{(.-)}", function(k)
    local v = kwargs[k]
    if v then
      return stringify(v)
    else
      return "{" .. k .. "}" -- keep if missing
    end
  end))
end

return {
  ['i18n'] = function(args, kwargs, meta, raw_args, context) 

    local key = args[1] and stringify(args[1])
    if not key then
      return pandoc.Str("missing key")
    end

    local i18n = meta.i18n
    if not i18n then
      return pandoc.Str("no i18n block")
    end

    local lang = pandoc.utils.stringify(meta.lang or "en")

    local dict

    if i18n[lang] then
      dict = i18n[lang]
    else
      dict = i18n
    end

    -- resolve key (supports nested like home.title)
    local value = resolve_key(dict, key)

    if value then
      local text = stringify(value)
      text = interpolate(text, kwargs)
      return pandoc.Str(text)
    end

    -- fallback: use enclosed content if exists
    if raw_args and raw_args[2] then
      return raw_args[2]  -- content between {{< >}} ... {{< / >}}
    end

    -- final fallback
    return pandoc.Str("missing: " .. key)

  end
}
