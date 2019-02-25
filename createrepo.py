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

DIR_PATH = os.path.dirname(os.path.realpath(__file__))
SAB_WORKSPACE=f"{DIR_PATH}/sab_workspace"
META_REPO="/var/git"

# take only the returned path of mkstemp and make a Path object
entropysrv=pathlib.Path(tempfile.mkstemp()[1])
createrepo=pathlib.Path(tempfile.mkstemp()[1])
makeconf=pathlib.Path(tempfile.mkstemp()[1])

REPOSITORY_NAME="testing.kantoo.org"
REPOSITORY_DESCRIPTION="Funtoo on RPI3!"

#this has to match the funtoo.dockerfile
OS="funtoo"
ARCH="arm-32bit"
SUBARCH="rpi3"
ENTROPY_ARCH="armv7l"
# ARCH="x86-64bit"
# SUBARCH="amd64-k10"
# ENTROPY_ARCH="amd64"


DOCKER_IMAGE=f"{OS}/{ARCH}/{SUBARCH}:stage3"
DOCKER_FILE='funtoo.dockerfile'
DOCKER_BUILDARGS = {
    'ARCH':ARCH,
    'SUBARCH':SUBARCH,
}
# see https://docker-py.readthedocs.io/en/stable/containers.html
client = docker.from_env()
if DOCKER_IMAGE in list(map(lambda x:x.pop(),(filter(lambda x:x != [],(map(lambda x:x.tags,client.images.list())))))):
    print(f"Found docker image {DOCKER_IMAGE}")
else:
    print(f"Did not find docker image {DOCKER_IMAGE}. Must be built.")
    client.images.build(path=DIR_PATH,dockerfile=DOCKER_FILE,tag=DOCKER_IMAGE,quiet=False,buildargs=DOCKER_BUILDARGS)


PORTAGE_ARTIFACTS=f"{SAB_WORKSPACE}/portage_artifacts"
OUTPUT_DIR=f"{SAB_WORKSPACE}/entropy_artifacts"


docker_env=[
    f"EDITOR=cat",
    f"LC_ALL=en_US.UTF-8",
]

docker_volumes ={
    META_REPO:{'bind':"/var/git",'mode':'ro'},
    OUTPUT_DIR:{'bind':"/entropy/artifacts",'mode':"rw"},
    createrepo:{'bind':"/entropy/bin/create_repo.sh",'mode':"ro"},
    entropysrv:{'bind':"/etc/entropy/server.conf",'mode':"ro"},
    makeconf:{'bind':"/etc/portage/make.conf",'mode':"ro"},

}
# only scriptname with no args
if len(sys.argv) == 1:
    docker_volumes.update({PORTAGE_ARTIFACTS:{'bind':"/root/packages",'mode':"rw"}})
else:
    print(f"Packages directory set to : {sys.argv[1]}")
    docker_volumes.update({sys.argv[1]:"/root/packages"})


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

print(entropysrv_conf)
entropysrv.write_text(entropysrv_conf)

#configure a local binhost for portage
make_conf = f"""
EMERGE_DEFAULT_OPTS="--quiet-build=y --jobs=3"
"""
print(make_conf)
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

DOCKER_SCRIPT='/entropy/bin/create_repo.sh'
container = client.containers.run(DOCKER_IMAGE,DOCKER_SCRIPT,**DOCKER_OPTS)
if container:
    print(f"{container.name} created")
    print(f"\tmake.conf: {makeconf}")
    print(f"\tcreate_repo.sh: {createrepo}")

container.wait()
open(f"log-{ARCH}-{SUBARCH}-{datetime.now().strftime('%y-%m-%d-%H:%M:%S')}.txt",'wb').write(container.logs())

repo_conf = f"""
[{REPOSITORY_NAME}]
desc = {REPOSITORY_DESCRIPTION}
repo=file://{OUTPUT_DIR}#bz2
enabled = true
pkg = file://{OUTPUT_DIR}
"""

if os.path.exists(f"{OUTPUT_DIR}/standard"):
    print(f"The Sabayon repository files are in {OUTPUT_DIR}")
    print("Now you can upload its content where you want")
    print("")
    print("Here it is the repository file how will look like ")
    print("(if you plan to upload it to a webserver, modify the URI accordingly)")
    print(repo_conf)
else:
    print("Something failed :(")
    print("check the log")


container.stop()

