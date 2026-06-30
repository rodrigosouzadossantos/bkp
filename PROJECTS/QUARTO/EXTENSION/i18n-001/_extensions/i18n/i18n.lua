--- local yaml = require("lyaml")

local translations_cache = {}

-- ------------------------
-- Config
-- ------------------------
local function get_i18n_config(meta)
  local cfg = {
    path = "i18n",
    fallback = "en"
  }

  if meta.i18n then
    if meta.i18n.path then
      cfg.path = pandoc.utils.stringify(meta.i18n.path)
    end

    if meta.i18n.fallback then
      cfg.fallback = pandoc.utils.stringify(meta.i18n.fallback)
    end
  end

  return cfg
end

-- ------------------------
-- Language
-- ------------------------
local function get_lang(meta)
  if meta.lang then
    return pandoc.utils.stringify(meta.lang)
  end
  return "en"
end

-- ------------------------
-- File loader (cached)
-- ------------------------
local function load_file(meta, lang)
  local cfg = get_i18n_config(meta)
  local path = cfg.path .. "/" .. lang .. ".yml"

  if translations_cache[path] then
    return translations_cache[path]
  end

  local f = io.open(path, "r")
  if not f then
    -- optional debug:
    -- io.stderr:write("i18n: missing file " .. path .. "\n")
    return nil
  end

  local content = f:read("*all")
  f:close()

  local parsed = yaml.load(content)
  translations_cache[path] = parsed

  return parsed
end

-- ------------------------
-- Nested lookup: a.b.c
-- ------------------------
local function lookup(tbl, key)
  for part in key:gmatch("[^%.]+") do
    if not tbl then return nil end
    tbl = tbl[part]
  end
  return tbl
end

-- ------------------------
-- Variable interpolation
-- ------------------------
local function interpolate(str, vars)
  return (str:gsub("{(.-)}", function(k)
    return vars[k] or "{" .. k .. "}"
  end))
end

-- ------------------------
-- Translate
-- ------------------------
local function translate(meta, key, vars)
  local cfg = get_i18n_config(meta)

  local lang = get_lang(meta)
  local fallback = cfg.fallback

  local current = meta.i18n --- load_file(meta, lang)
  local fallback_tbl = load_file(meta, fallback)

  local value =
    (current and lookup(current, key)) or
    (fallback_tbl and lookup(fallback_tbl, key))

  if not value then
    return nil
  end

  value = pandoc.utils.stringify(value)

  if vars then
    value = interpolate(value, vars)
  end

  return value
end

-- ------------------------
-- Main filter
-- ------------------------
return {
  {
    Span = function(el)
      local key = el.attributes["data-i18n"]
      if not key then
        return nil
      end

      -- collect variables
      local vars = {}
      for k, v in pairs(el.attributes) do
        local name = k:match("^data%-i18n%-(.+)")
        if name then
          vars[name] = v
        end
      end

      local text = translate(quarto.doc.meta, key, vars)

      if text then
        return pandoc.Str(text)
      end

      -- fallback: inline content
      if #el.content > 0 then
        return el.content
      end

      -- final fallback: show key
      return pandoc.Str(key)
    end
  }
}
