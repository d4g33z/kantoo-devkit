#!/bin/sh

if [ ! -f /var/lib/entropy/client/database/${ENTROPY_ARCH}/equo.db ]; then
    echo "=== rebuilding the entropy database ==="
    echo "yes\nyes\nyes\n" | equo rescue generate
fi

echo "=== registering all portage installed packages ==="
equo rescue spmsync

