#mkdir -p {cvx/{core,lib/{config,data,display/{console,plotting},storage/{aws,local},features,reporting}},tests/{unit,memory,integration,distributed},docs


tree -J | jq -r '
def toyaml:
  if .type == "directory" then
    # Separate contents into files and dirs
    ( .contents // [] ) as $c |
    ($c | map(select(.type=="file")) | map("- "+.name)) as $files |
    ($c | map(select(.type=="directory"))) as $dirs |
    "\(.name): " + (
      if ($files | length == 0) and ($dirs | length == 0) then
        "null"
      else
        (if $files | length > 0 then
          "\n" + ($files | join("\n") | gsub("(?m)^"; "  "))
        else
          ""
        end) +
        (if $dirs | length > 0 then
          "\n" + ($dirs | map(toyaml) | join("\n") | gsub("(?m)^"; "  "))
        else
          ""
        end)
      end
    )
  else
    empty
  end;

.[0].contents[] | toyaml
'
