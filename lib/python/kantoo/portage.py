#!/usr/bin/env python3

import re
import portage
from kantoo.utils import *
from urllib.parse import urlparse
import sys

#get all profile info
def profile_info():
    print("\n".join(portage.settings.profiles))

def all_wildcard_keywords():
    p = portage.db[portage.root]["porttree"].dbapi
    #flatten list
    cpvs = [item for sublist in list(map(lambda x:p.xmatch("match-visible",x),p.cp_all())) for item in sublist]
    kws = list(map(lambda x:p.aux_get(x,['KEYWORDS']),cpvs))
    return list(filter(lambda x:len(x[1])==1 and x[1][0] in ['','*','~*','**'],zip(cpvs,kws)))

def emerge_local_binaries():
    IN_PORT_PKGS = os.environ.get('IN_PORT_PKGS')
    for in_port_pkg in IN_PORT_PKGS.splitlines():
        run_write_docker_output(f"emerge --keep-going --usepkg {in_port_pkg}")

#not necessary, but interesting
def spawn_local_binhost_server(make_conf='/etc/portage/make.conf'):
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
        #TODO this is not needed if the --usepkg option to emerge is used
        KeyboardInterrupt
        http_server_subprocess = subprocess.Popen(f"python3 -m http.server -b {HTTP_SERVER_HOST} {HTTP_SERVER_PORT}",
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=PKGDIR)
        return http_server_subprocess
    return None




