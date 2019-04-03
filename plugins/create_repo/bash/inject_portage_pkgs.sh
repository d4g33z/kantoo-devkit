#!/usr/bin/env sh

built_pkgs=$(find ${TMP_PKGDIR} -name "*.tbz2" | xargs)

echo "=== Injecting packages ==="
#if [ ! -z ${built_pkgs} ]; then
eit inject ${built_pkgs} || { echo "ouch unable to inject"; }
#else
#    echo "no built portage packages found"
#fi

# we just want to inject a handful of packages, not everything on system
#echo "=== commiting all installed packages locally ==="
#eit commit --quick
#echo "=== Pushing built packages locally ==="
#eit push --quick --force