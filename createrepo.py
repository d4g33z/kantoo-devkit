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
META_REPO="/var/git"
REPOSITORY_NAME="testing.kantoo.org"
REPOSITORY_DESCRIPTION="Funtoo on RPI3!"
PORTAGE_ARTIFACTS=f"{SAB_WORKSPACE}/portage_artifacts"
ENTROPY_ARTIFACTS= f"{SAB_WORKSPACE}/entropy_artifacts"


class FilePlugin:
    def __init__(self,name,mode='ro'):
        self.path = pathlib.Path(tempfile.mkstemp()[1])
        self.volume = {'bind':f"/entropy/plugins/{name}.sh",'mode':mode}
    def bash(self,script):
        self.path.write_text(script)
    @property
    def DOCKER_SCRIPT(self):
        return self.volume.get('bind')


#file plugins
# take only the returned path of mkstemp and make a Path object
entropysrv=pathlib.Path(tempfile.mkstemp()[1])
createrepo=pathlib.Path(tempfile.mkstemp()[1])
makeconf=pathlib.Path(tempfile.mkstemp()[1])

#a generic file to plug into the container
#fileplugin=pathlib.Path(tempfile.mkstemp()[1])
fileplugin = FilePlugin('hello_world')

#env plugins
docker_env=[
    f"EDITOR=cat",
    f"LC_ALL=en_US.UTF-8",
]

#volume plugins
docker_volumes ={
    META_REPO:{'bind':"/var/git",'mode':'ro'},
    ENTROPY_ARTIFACTS:{'bind': "/entropy/artifacts", 'mode': "rw"},
    createrepo:{'bind':"/entropy/bin/create_repo.sh",'mode':"ro"},
    entropysrv:{'bind':"/etc/entropy/server.conf",'mode':"ro"},
    makeconf:{'bind':"/etc/portage/make.conf",'mode':"ro"},
    # fileplugin:{'bind':"/entropy/plugins/fileplugin.sh",'mode':"ro"},
    fileplugin.path:fileplugin.volume,

}

# see https://docker-py.readthedocs.io/en/stable/containers.html
client = docker.from_env()
if DOCKER_IMAGE in list(map(lambda x:x.pop(),(filter(lambda x:x != [],(map(lambda x:x.tags,client.images.list())))))):
    print(f"Found docker image {DOCKER_IMAGE}")
else:
    print(f"Did not find docker image {DOCKER_IMAGE}. Must be built.")
    client.images.build(path=DIR_PATH,dockerfile=DOCKER_FILE,tag=DOCKER_IMAGE,quiet=False,buildargs=DOCKER_BUILDARGS)




# only scriptname with no args
if len(sys.argv) == 1:
    docker_volumes.update({PORTAGE_ARTIFACTS:{'bind':"/root/packages",'mode':"rw"}})
else:
    print(f"Packages directory set to : {sys.argv[1]}")
    docker_volumes.update({sys.argv[1]:{'bind':"/root/packages",'mode':"rw"}})


print(f"Repository: {REPOSITORY_NAME}")
print(f"Repository Description: {REPOSITORY_DESCRIPTION}")

# Creating the building script on-the-fly
# Runs inside the container
createrepo_script =f"""#!/bin/bash
set -e
repo="{REPOSITORY_NAME}"

export DONT_MOUNT_BOOT=1
emerge -C debian-sources-lts
emerge equo entropy-server bsdiff

if [ ! -f /var/lib/entropy/client/database/{ENTROPY_ARCH}/equo.db ]; then
    echo "yes\nyes\nyes\n" | equo rescue generate
fi

equo rescue spmsync

built_pkgs=$(find /root/packages -name "*.tbz2" | xargs)

sed -e 's:python2.7:python:g' -i /usr/bin/eit

if [ -d "/entropy/artifacts/standard" ]; then
  echo "=== Repository already exists, syncronizing ==="
  eit unlock ${{repo}} || true
  eit pull --quick ${{repo}} || true
  #eit sync ${{repo}}
else
  echo "=== Repository is empty, intializing ==="
  echo "Yes" | eit init --quick ${{repo}}
  eit push --quick --force
fi

echo "=== Injecting packages ==="
#eit inject ${{built_pkgs}} || {{ echo "ouch unable to inject"; }}
eit commit --quick

echo "=== Pushing built packages locally ==="
eit push --quick --force

echo "=== Finished ==="
"""

#now write it in createrepo tempfile
createrepo.write_text(createrepo_script)
createrepo.chmod(0o744)


# Creating the entropy repository configuration on-the-fly
entropysrv_conf = f"""
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
"""

entropysrv.write_text(entropysrv_conf)

#configure portage
make_conf = f"""
EMERGE_DEFAULT_OPTS="--quiet-build=y --jobs=3"
"""

makeconf.write_text(make_conf)

DOCKER_OPTS={
    'tty':True,
    'init':True,
    'remove':False,
    'volumes':docker_volumes,
    'environment':docker_env,
    'entrypoint':"/bin/bash",
    'detach':True,
}

fileplugin.bash(
"""#!/bin/bash
echo hello world
""")

#fileplugin.path.write_text(fileplugin.bash)

#DOCKER_SCRIPT='/entropy/bin/create_repo.sh'
#DOCKER_SCRIPT='/entropy/plugins/fileplugin.sh'
# DOCKER_SCRIPT=None
container = client.containers.run(DOCKER_IMAGE,fileplugin.DOCKER_SCRIPT,**DOCKER_OPTS)
if container:
    print(f"{container.name} created")
    print(f"\tmake.conf: {makeconf}")
    print(f"\tcreate_repo.sh: {createrepo}")

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

