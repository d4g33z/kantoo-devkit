#!/usr/bin/env python3
import os

from kantoo.utils import *

IN_PORT_PKGS = os.environ.get('IN_PORT_PKGS')
os.sys.stdout.write(' '.join(map(lambda x:x.strip(),IN_PORT_PKGS)))
#stdout, stderr, rc = run_cmd(f"emerge {' '.join(map(lambda x:x.strip(),IN_PORT_PKGS))}")




