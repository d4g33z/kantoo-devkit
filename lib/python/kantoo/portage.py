#!/usr/bin/env python3

import re
import portage
from kantoo.utils import *
from urllib.parse import urlparse

#get all profile info
def profile_info():
    print("\n".join(portage.settings.profiles))

def emerge(make_conf='/etc/portage/make.conf'):
    IN_PORT_PKGS = os.environ.get('IN_PORT_PKGS')
    PKGDIR = None
    PORTAGE_BINHOST = None
    for line in read_file_contents_as_lines(make_conf):
       m = re.match('^PKGDIR=(.*)$',line)
       if m is not None:
           PKGDIR = m.groups()[0]
       else:
            m = re.match('^PORTAGE_BINHOST=(.*)$',line)
            if m is not None:
                PORTAGE_BINHOST = urlparse(m.groups()[0]).netloc
                HTTP_SERVER_HOST,HTTP_SERVER_PORT = PORTAGE_BINHOST.split(':')


    if PKGDIR:
        #start local static web server
        KeyboardInterrupt
        http_server_subprocess = subprocess.Popen(f"python3 -m http.server -b {HTTP_SERVER_HOST} {HTTP_SERVER_PORT}",
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=PKGDIR)


    stdout, stderr, rc = run_cmd(f"emerge {' '.join(IN_PORT_PKGS.splitlines())}")



    if PKGDIR:
        http_server_subprocess.kill()

