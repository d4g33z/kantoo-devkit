#!/usr/bin/env sh

echo "=== removing portage packages ${RM_PORT_PKGS} ==="
emerge -C ${RM_PORT_PKGS}
emerge --depclean

