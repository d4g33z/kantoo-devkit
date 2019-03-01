#!/bin/sh

if [ ! -f /var/lib/entropy/client/database/${ENTROPY_ARCH}/equo.db ]; then
    echo "yes\nyes\nyes\n" | equo rescue generate
fi

equo rescue spmsync

