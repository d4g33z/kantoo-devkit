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

DIR_PATH = os.path.dirname(os.path.realpath(__file__))

SAB_WORKSPACE="/root/sab_workspace"
META_REPO="/var/git"

# take only the returned path of mkstemp and make a Path object
entropysrv=pathlib.Path(tempfile.mkstemp()[1])
createrepo=pathlib.Path(tempfile.mkstemp()[1])

REPOSITORY_NAME="testing.kantoo.org"
REPOSITORY_DESCRIPTION="Funtoo on RPI3!"

#this has to match the funtoo.dockerfile
# ARCH="arm-32bit"
# SUBARCH="rpi3"
ARCH="x86-64bit"
SUBARCH="amd64-k10"

DOCKER_IMAGE=f"{ARCH}/{SUBARCH}:stage3"
# see https://docker-py.readthedocs.io/en/stable/containers.html
client = docker.from_env()
if DOCKER_IMAGE in list(map(lambda x:x.pop(),(filter(lambda x:x != [],(map(lambda x:x.tags,client.images.list())))))):
    print(f"Found docker image {DOCKER_IMAGE}")
else:
    print(f"Did not find docker image {DOCKER_IMAGE}. Must be built.")
    client.images.build(path=DIR_PATH,dockerfile='funtoo.dockerfile',tag=DOCKER_IMAGE)


PORTAGE_ARTIFACTS=f"{SAB_WORKSPACE}/portage_artifacts"
ENTROPY_ARTIFACTS=f"{SAB_WORKSPACE}/sabayon/artifacts"
OUTPUT_DIR=f"{SAB_WORKSPACE}/entropy_artifacts"

DOCKER_OPTS="--ti --rm"

EDITOR="cat"
LC_ALL="en_US.UTF-8"

# all prefixed with -e on docker cmd line
docker_env=(
    f"EDITOR={EDITOR}",
    f"REPOSITORY={REPOSITORY_NAME}",
    f"LC_ALL={LC_ALL}")

# all prefixed with -v on docker cmd line
docker_volumes=[
    f"{OUTPUT_DIR}:/sabayon/artifacts",
    f"{createrepo}:/sabayon/bin/create_repo.sh",
    f"{entropysrv}:/etc/entropy/server.conf",
    f"{META_REPO}:/var/git"]

# only scriptname with no args
if len(sys.argv) == 1:
    docker_volumes.append(f"{PORTAGE_ARTIFACTS}:/root/packages")
else:
    print(f"Packages directory set to : {sys.argv[1]}")
    docker_volumes.append(f"{sys.argv[1]}:/root/packages")


print(f"Repository: {REPOSITORY_NAME}")
print(f"Repository Description: {REPOSITORY_DESCRIPTION}")

# Creating the building script on-the-fly
# Runs inside the container

import fnmatch
def make_built_pkgs():
    #built_pkgs=\$(find /root/packages -name "*.tbz2" | xargs)
    built_pks = ""

    for dirpath, dirnames, filenames in os.walk(PORTAGE_ARTIFACTS):
        for filename in filenames:
            if fnmatch.fnmatch(filename, "*.tbz2"): # Match search string
                built_pks += (os.path.join(dirpath, filename) + " ")
    return built_pks

createrepo1 =f"""
#!/bin/bash
set -e
built_pkgs={make_built_pkgs()}
repo="{REPOSITORY_NAME}"
mkdir -p /sabayon/artifacts"""

createrepo2 = """
[[ -z "\${built_pkgs}" ]] && echo "ERROR: no tbz2s found" && exit 2

equo rescue generate

sed -e 's:python2.7:python:g' -i /usr/bin/eit

if [ -d "/sabayon/artifacts/standard" ]; then
  echo "=== Repository already exists, syncronizing ==="
  eit unlock \$repo || true
  eit pull --quick \$repo || true
  #eit sync \$repo
else
  echo "=== Repository is empty, intializing ==="
  echo "Yes" | eit init --quick \$repo
  eit push --quick --force
fi

echo "=== Injecting packages ==="
eit inject \${built_pkgs} || { echo "ouch unable to inject" && exit 3; }
eit commit --quick

echo "=== Pushing built packages locally ==="
eit push --quick --force
"""
createrepo_script = createrepo1 + createrepo2
print(createrepo_script)


#now write it in createrepo tempfile
print(f"writing to {createrepo}")
createrepo.write_text(createrepo_script)
createrepo.chmod(0o744)

# Creating the entropy repository configuration on-the-fly
entropysrv = f"""
# expiration-days = <internal value>
community-mode = enable
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
repository={REPOSITORY_NAME}|{REPOSITORY_DESCRIPTION}|file://{ENTROPY_ARTIFACTS}
"""

print(entropysrv)

docker_cmd = f"docker {DOCKER_OPTS} { ' -e ' + ' -e '.join(docker_env)} {' -v ' + ' -v '.join(docker_volumes)} {DOCKER_IMAGE} /sabayon/bin/create_repo.sh"

print(docker_cmd)


#run_print_output_error(docker_cmd)
#
repo_conf = f"""
[{REPOSITORY_NAME}]
desc = {REPOSITORY_DESCRIPTION}
repo=file://{OUTPUT_DIR}#bz2
enabled = true
pkg = file://{OUTPUT_DIR}
"""

if os.path.exists("$OUTPUT_DIR/standard"):
    print("The Sabayon repository files are in $OUTPUT_DIR")
    print("Now you can upload its content where you want")
    print("")
    print("Here it is the repository file how will look like ")
    print("(if you plan to upload it to a webserver, modify the URI accordingly)")
    print(repo_conf)
else:
  print("Something failed :(")

