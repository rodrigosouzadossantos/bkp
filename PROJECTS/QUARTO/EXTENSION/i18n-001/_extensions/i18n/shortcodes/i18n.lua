-- shortcode: {{< i18n key param="value" >}}fallback{{< /i18n >}}
return {
  ['short'] = function(args, kwargs, meta)
    local key = pandoc.utils.stringify(args[1] or "")

    -- inline fallback content (if any)
    local fallback = ""
    if #args > 1 then
      fallback = pandoc.utils.stringify(args[2])
    end

    local attr = {
      ["data-i18n"] = key
    }

    -- pass named params as variables
    for k, v in pairs(kwargs) do
      attr["data-i18n-" .. k] = pandoc.utils.stringify(v)
    end

    local content = {}
    if fallback ~= "" then
      content = { pandoc.Str(fallback) }
    end

    return pandoc.Span(content, attr)
  end
}
