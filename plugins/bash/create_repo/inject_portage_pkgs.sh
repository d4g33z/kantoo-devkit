#!/usr/bin/env sh

built_pkgs=$(find /root/packages -name "*.tbz2" | xargs)

echo "=== Injecting packages ==="
if [ ! -z ${built_pkgs} ]; then
    eit inject ${built_pkgs} || { echo "ouch unable to inject"; }
else
    echo "no built portage packages found"
fi
