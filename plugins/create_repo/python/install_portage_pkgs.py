#!/usr/bin/env python3

from kano.utils import *

IN_PORT_PKGS = os.environ.get('IN_PORT_PKGS')
stdout, stderr, rc = run_cmd(f"emerge {' '.join(IN_PORT_PKGS.splitlines())}")




