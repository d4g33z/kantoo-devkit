#!/usr/bin/env sh

echo "=== commiting all installed packages locally ==="
eit commit --quick
echo "=== Pushing built packages locally ==="
eit push --quick --force

