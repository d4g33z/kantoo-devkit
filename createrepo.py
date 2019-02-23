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

import pathlib
import tempfile
import sys
import os

SAB_WORKSPACE="/root/sab_workspace"
META_REPO="/var/git"

#take only the returned path of mkstemp
entropysrv=pathlib.Path(tempfile.mkstemp()[1])
createrepo=pathlib.Path(tempfile.mkstemp()[1])

REPOSITORY_NAME="testing.kantoo.org"
REPOSITORY_DESCRIPTION="Funtoo on RPI3!"

ARCH="arm-32bit"
SUBARCH="rpi3"

DOCKER_IMAGE=f"funtoo/{ARCH}/{SUBARCH}"

PORTAGE_ARTIFACTS=f"{SAB_WORKSPACE}/portage_artifacts"
ENTROPY_ARTIFACTS=f"{SAB_WORKSPACE}/sabayon/artifacts"
OUTPUT_DIR=f"{SAB_WORKSPACE}/entropy_artifacts"

DOCKER_OPTS="--ti --rm"

EDITOR="cat"
LC_ALL="en_US.UTF-8"

#all prefixed with -e on docker cmd line
docker_env=(
    f"EDITOR={EDITOR}",
    f"REPOSITORY={REPOSITORY_NAME}",
    f"LC_ALL={LC_ALL}")

#all prefixed with -v on docker cmd line
docker_volumes=[
    f"{OUTPUT_DIR}:/sabayon/artifacts",
    f"{createrepo}:/sabayon/bin/create_repo.sh",
    f"{entropysrv}:/etc/entropy/server.conf",
    f"{META_REPO}:/var/git"]

#only scriptname with no args
if len(sys.argv) == 1:
    docker_volumes.append(f"{PORTAGE_ARTIFACTS}:/root/packages")
else:
    print(f"Packages directory set to : {sys.argv[1]}")
    docker_volumes.append(f"{sys.argv[1]}:/root/packages")


print(f"Repository: {REPOSITORY_NAME}")
print(f"Repository Description: {REPOSITORY_DESCRIPTION}")

# Creating the building script on-the-fly
# Runs inside the container

def make_built_pkgs():
    #built_pkgs=\$(find /root/packages -name "*.tbz2" | xargs)
    return ''

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

import subprocess
import signal
def restore_signals():
        signals = ('SIGPIPE', 'SIGXFZ', 'SIGXFSZ')
        for sig in signals:
            if hasattr(signal, sig):
                signal.signal(getattr(signal, sig), signal.SIG_DFL)

def run_cmd(cmd):
    process = subprocess.Popen(cmd, shell=True,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               preexec_fn=restore_signals)

    stdout, stderr = process.communicate()
    returncode = process.returncode
    return stdout, stderr, returncode


def run_term_on_error(cmd):
    o, e, rc = run_cmd(cmd)
    if e:
        sys.exit('\nCommand:\n{}\n\nterminated with error:\n{}'.format(cmd, e.strip()))
    return o, e, rc


def run_print_output_error(cmd):
    o, e, rc = run_cmd(cmd)
    if o or e:
        print '\ncommand: {}'.format(cmd)
    if o:
        print 'output:\n{}'.format(o.strip())
    if e:
        print '\nerror:\n{}'.format(e.strip())
    return o, e, rc

run_print_output_error(docker_cmd)
#
repo_conf = f"""
[{REPOSITORY_NAME}]
desc = {REPOSITORY_DESCRIPTION}
repo=file://{OUTPUT_DIR}#bz2
enabled = true
pkg = file://{OUTPUT_DIR}
"""

if os.exists("$OUTPUT_DIR/standard"):
    print("The Sabayon repository files are in $OUTPUT_DIR")
    print("Now you can upload its content where you want")
    print("")
    print("Here it is the repository file how will look like ")
    print("(if you plan to upload it to a webserver, modify the URI accordingly)")
    print(repo_conf)
else:
  print("Something failed :(")
#
# rm -rf $createrepo
# rm -rf $entropysrv

