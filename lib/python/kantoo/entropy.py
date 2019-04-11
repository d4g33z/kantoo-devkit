#!/usr/bin/env python3

import os
from functools import reduce
from kantoo.utils import *
import portage
import pathlib


def unmask_packages(PKGDIR=None,_UNMASK_FILE=None):
    PKGDIR = os.environ.get('PKGDIR') if PKGDIR is None else PKGDIR
    UNMASK_FILE = os.environ.get('ENTR_UNMASK_FILE') if _UNMASK_FILE is None else _UNMASK_FILE
    port_pkgs = []
    for dir_path,dir_names,file_names in os.walk(PKGDIR):
        port_pkgs += map(lambda x:f"{pathlib.Path(dir_path).parts[-1]}/{x[:-5]}",filter(lambda x:'tbz2' in x,file_names))
    p = portage.db[portage.root]["porttree"].dbapi
    kws = {k:v for k,v in {port_pkg:p.aux_get(port_pkg,['KEYWORDS']) for port_pkg in port_pkgs}.items() if v[0] in ['*','~*','']}

    pathlib.Path(UNMASK_FILE).touch(mode=0o644,exist_ok=True)
    with open(UNMASK_FILE,'a') as f:
        for entr_pkg in kws.keys():
            write_docker_stdout(f"appending {entr_pkg} to unmask file\n")
            f.write(f"{entr_pkg}\n")

def equo_install():
    PRETEND = bool(os.environ.get('ENTR_PRETEND',False))
    IN_ENTR_PKGS= os.environ.get('IN_ENTR_PKGS')
    for in_entr_pkg in IN_ENTR_PKGS.splitlines():
        run_write_docker_output(f"equo install {'--pretend' if PRETEND else ''} {in_entr_pkg}")

def spawn_local_entropy_server(repository_dir):
    PKGDIR = None
    PORTAGE_BINHOST = None

    HTTP_SERVER_HOST = 'masterpi.local'
    HTTP_SERVER_PORT = 3030
    #start local static web server
    #TODO this is not needed if the --usepkg option to emerge is used
    KeyboardInterrupt
    os.chdir(repository_dir)
    http_server_subprocess = subprocess.Popen(f"python3 -m http.server -b {HTTP_SERVER_HOST} {HTTP_SERVER_PORT}",
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=PKGDIR)
    return http_server_subprocess
