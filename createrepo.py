# License: http://www.gnu.org/licenses/gpl-2.0.txt GNU General Public License v2

# Copyright 2016-2018 See AUTHORS file
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

#utility functions
from kantoo import *

import docker
import pathlib
import tempfile
import sys
import os
from datetime import datetime

#these are supplied to the dockerfile via build-args
OS="funtoo"
#ARCH="arm-32bit"
#SUBARCH="rpi3"
#ENTROPY_ARCH="armv7l"
ARCH="x86-64bit"
SUBARCH="amd64-k10"
ENTROPY_ARCH="amd64"

DOCKER_IMAGE=f"{OS}/{ARCH}/{SUBARCH}:stage3"
DOCKER_FILE='funtoo.dockerfile'
DOCKER_BUILDARGS = {
    'ARCH':ARCH,
    'SUBARCH':SUBARCH,
}
DIR_PATH = os.path.dirname(os.path.realpath(__file__))
SAB_WORKSPACE=f"{DIR_PATH}/sab_workspace"
REPOSITORY_NAME="testing.kantoo.org"
REPOSITORY_DESCRIPTION="Funtoo on RPI3!"

class DirPlugin:
    def __init__(self,bind,mode='ro'):
        self.path = pathlib.Path(bind)
        self.volume = {'bind': bind, 'mode':mode}
    @property
    def docker_env(self):
        return []

class BashPlugin:
    def __init__(self,name,mode='ro'):
        self.path = pathlib.Path(tempfile.mkstemp()[1])
        self.volume = {'bind':f"/entropy/plugins/{name}.sh",'mode':mode}
        self.env = {}
    def write(self,txt,**env):
        self.path.write_text(txt)
        self.env = {**self.env,**env}
    @property
    def docker_env(self):
        return [f"{env_var}={value}" for env_var,value in self.env.items()]

    @property
    def DOCKER_SCRIPT(self):
        return self.volume.get('bind')

class FilePlugin:
    def __init__(self,bind,mode='ro'):
        self.path = pathlib.Path(tempfile.mkstemp()[1])
        self.volume = {'bind':bind,'mode':mode}
        self.env = {}
    def write(self,txt,**env):
        self.path.write_text(txt)
        self.env = {**self.env,**env}
    @property
    def docker_env(self):
        return [f"{env_var}={value}" for env_var,value in self.env.items()]

helloworldplugin = BashPlugin('hello_world')
helloworldplugin.write(
"""#!/bin/bash
echo hello world
""")

#the main script to create the repo
createrepo = BashPlugin('create_repo')
createrepo.write(open(f"{DIR_PATH}/plugins/bash/create_repo",'r').read(),REPOSITORY_NAME=REPOSITORY_NAME,ENTROPY_ARCH=ENTROPY_ARCH)
createrepo.path.chmod(0o744)

#conifiguring local entropy server
entropysrv = FilePlugin('/etc/entropy/server.conf')
entropysrv.write(
"""
# expiration-days = <internal value>
community-mode = disable
weak-package-files = disable
database-format = bz2
# sync-speed-limit =
# server-basic-languages = en_US C
# disabled-eapis = 1,2
# expiration-based-scope = disable
# nonfree-packages-directory-support = disable
rss-feed = enable
changelog = enable
rss-name = packages.rss
rss-base-url = http://packages.sabayon.org/?quicksearch=
rss-website-url = http://www.sabayon.org/
max-rss-entries = 10000
# max-rss-light-entries = 100
rss-light-name = updates.rss
managing-editor =
broken-reverse-deps = disable
default-repository = {REPOSITORY_NAME}
repository={REPOSITORY_NAME}|{REPOSITORY_DESCRIPTION}|file:///entropy/artifacts
""")

#configure portage
makeconf = FilePlugin('/etc/portage/make.conf')
makeconf.write(
f"""
EMERGE_DEFAULT_OPTS="--quiet-build=y --jobs=3"
""")

PORTAGE_ARTIFACTS= DirPlugin(f"{SAB_WORKSPACE}/portage_artifacts")
ENTROPY_ARTIFACTS = DirPlugin(f"{SAB_WORKSPACE}/entropy_artifacts",'rw')
META_REPO=DirPlugin("/var/git")

#env plugins
docker_env=[
    f"EDITOR=cat",
    f"LC_ALL=en_US.UTF-8",
]
all_plugins = [helloworldplugin,createrepo,entropysrv,makeconf,PORTAGE_ARTIFACTS,ENTROPY_ARTIFACTS,META_REPO]

# see https://docker-py.readthedocs.io/en/stable/containers.html
client = docker.from_env()
if DOCKER_IMAGE in list(map(lambda x:x.pop(),(filter(lambda x:x != [],(map(lambda x:x.tags,client.images.list())))))):
    print(f"Found docker image {DOCKER_IMAGE}")
else:
    print(f"Did not find docker image {DOCKER_IMAGE}. Must be built.")
    client.images.build(path=DIR_PATH,dockerfile=DOCKER_FILE,tag=DOCKER_IMAGE,quiet=False,buildargs=DOCKER_BUILDARGS)


print(f"Repository: {REPOSITORY_NAME}")
print(f"Repository Description: {REPOSITORY_DESCRIPTION}")




from functools import reduce
DOCKER_OPTS={
    'tty':True,
    'init':True,
    'remove':False,
    'volumes':{x.path:x.volume for x in all_plugins},
    'environment':list(reduce(lambda x,y:x+y,[z.docker_env for z in all_plugins])),
    'entrypoint':"/bin/bash",
    'detach':True,
}


container = client.containers.run(DOCKER_IMAGE, helloworldplugin.DOCKER_SCRIPT, **DOCKER_OPTS)
#container = client.containers.run(DOCKER_IMAGE, createrepo.DOCKER_SCRIPT, **DOCKER_OPTS)
if container:
    print(f"{container.name} created")
    print(f"\tmake.conf: {makeconf.path}")
    print(f"\tcreate_repo.sh: {createrepo.path}")

#for l in container.logs(stream=True):
#    print(l)

container.wait()

if pathlib.Path(f"{DIR_PATH}/logs").exists():
    open(f"{DIR_PATH}/last_logs.txt",'wb').write(container.logs())
    open(f"{DIR_PATH}/logs/{ARCH}-{SUBARCH}-{datetime.now().strftime('%y-%m-%d-%H:%M:%S')}.txt",'wb').write(container.logs())
else:
    print("create a logs/ directory to save as a timestamped file")

repo_conf = f"""
[{REPOSITORY_NAME}]
desc = {REPOSITORY_DESCRIPTION}
repo=file://{ENTROPY_ARTIFACTS}#bz2
enabled = true
pkg = file://{ENTROPY_ARTIFACTS}
"""

if os.path.exists(f"{ENTROPY_ARTIFACTS}/standard"):
    print(f"The kantoo repository files are in {ENTROPY_ARTIFACTS}")
    print("Now you can upload its content where you want")
    print("")
    print("Here it is the repository file how will look like ")
    print("(if you plan to upload it to a webserver, modify the URI accordingly)")
    print("This is an example of repo configuration in Entropy")
    print(repo_conf)
else:
    print("Something failed :(")
    print("check the log")


container.stop()
container.remove()

