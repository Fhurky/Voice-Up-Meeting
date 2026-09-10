#!/bin/sh
set -eu
umask 077

fail() {
  printf '%s\n' 'spark_proxy_start_failed' >&2
  exit 1
}

[ "$#" -eq 0 ] || fail
# Docker may give this alias both address families. Only a single canonical IPv4
# is usable by the Windows loopback tunnel; never ask nginx to resolve the name.
address="$(awk '
function ipv4(value, parts, count, i) {
  count = split(value, parts, ".")
  if (count != 4) return 0
  for (i = 1; i <= 4; i++) {
    if (parts[i] !~ /^[0-9]+$/ || length(parts[i]) > 3 || parts[i] + 0 > 255) return 0
    if (length(parts[i]) > 1 && substr(parts[i], 1, 1) == "0") return 0
  }
  return 1
}
{
  sub(/#.*/, "")
  for (i = 2; i <= NF; i++) {
    if ($i != "voiceup-spark-host") continue
    if (index($1, ":")) continue
    if (!ipv4($1)) { invalid = 1; continue }
    addresses[$1] = 1
  }
}
END {
  for (value in addresses) { count++; selected = value }
  if (invalid || count != 1) exit 1
  print selected
}' /etc/hosts)" || fail

directory="$(mktemp -d /tmp/voiceup-spark.XXXXXX)" || fail
# Render only the fixed private template; the original public config is included
# directly from its read-only mount. No environment or shell expansion is used.
awk -v address="$address" '
{
  count += gsub(/http:\/\/voiceup-spark-host:/, "http://" address ":")
  print
}
END { if (count != 2) exit 1 }
' /etc/nginx/spark.conf.template > "$directory/spark.conf" || fail

awk -v private="$directory/spark.conf" '
$1 == "include" && $2 == "/etc/nginx/conf.d/*.conf;" && NF == 2 {
  print
  print "    include " private ";"
  count++
  next
}
{ print }
END { if (count != 1) exit 1 }
' /etc/nginx/nginx.conf > "$directory/nginx.conf" || fail

nginx -t -c "$directory/nginx.conf" >/dev/null 2>&1 || fail
exec nginx -c "$directory/nginx.conf" -g 'daemon off;'
