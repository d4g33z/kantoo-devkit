#!/bin/sh
# notice the python f-string variables and the
set -e
repo="${REPOSITORY_NAME}"

export DONT_MOUNT_BOOT=1
emerge -C debian-sources-lts
emerge equo entropy-server bsdiff

if [ ! -f /var/lib/entropy/client/database/${ENTROPY_ARCH}/equo.db ]; then
    echo "yes\nyes\nyes\n" | equo rescue generate
fi

equo rescue spmsync


built_pkgs=$(find /root/packages -name "*.tbz2" | xargs)
sed -e 's:python2.7:python:g' -i /usr/bin/eit

if [ -d "/entropy/artifacts/standard" ]; then
  echo "=== Repository already exists, syncronizing ==="
  eit unlock ${repo} || true
  eit pull --quick ${repo} || true
  #eit sync ${{repo}}
else
  echo "=== Repository is empty, intializing ==="
  echo "Yes" | eit init --quick ${repo}
  eit push --quick --force
fi

echo "=== Injecting packages ==="
#eit inject ${{built_pkgs}} || {{ echo "ouch unable to inject"; }}
eit commit --quick

echo "=== Pushing built packages locally ==="
eit push --quick --force

echo "=== Finished ==="
