#!/bin/sh
set -eu
umask 077
fail() { printf '%s\n' 'text_review_proxy_start_failed' >&2; exit 1; }
[ "$#" -eq 0 ] || fail
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
    if ($i != "voiceup-text-host" || index($1, ":")) continue
    if (!ipv4($1)) { invalid = 1; continue }
    addresses[$1] = 1
  }
}
END {
  for (value in addresses) { count++; selected = value }
  if (invalid || count != 1) exit 1
  print selected
}' /etc/hosts)" || fail
# Fixed tmpfs path is composed into the Spark chain when that overlay is selected.
[ ! -e /tmp/voiceup-text-review.conf ] || fail
awk -v address="$address" '
{ count += gsub(/http:\/\/voiceup-text-host:/, "http://" address ":"); print }
END { if (count != 3) exit 1 }
' /etc/nginx/text-review.conf.template > /tmp/voiceup-text-review.conf || fail
if [ -f /etc/nginx/spark.conf.template ]; then
  exec /bin/sh /opt/voiceup/start-spark-proxy.sh
fi
directory="$(mktemp -d /tmp/voiceup-text.XXXXXX)" || fail
awk '
$1 == "include" && $2 == "/etc/nginx/conf.d/*.conf;" && NF == 2 {
  print; print "    include /tmp/voiceup-text-review.conf;"; count++; next
}
{ print }
END { if (count != 1) exit 1 }
' /etc/nginx/nginx.conf > "$directory/nginx.conf" || fail
nginx -t -c "$directory/nginx.conf" >/dev/null 2>&1 || fail
exec nginx -c "$directory/nginx.conf" -g 'daemon off;'
