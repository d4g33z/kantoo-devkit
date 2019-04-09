#!/usr/bin/env sh

if [ ! -e /var/lib/entropy/client/database/${ENTROPY_ARCH}/equo.db ]; then
    echo "=== rebuilding the entropy database ==="
    equo rescue generate <<EOF
Yes
Yes
Yes
EOF

fi

echo "=== registering all portage installed packages ==="
equo rescue spmsync

