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
import os
from datetime import datetime


c = Config(os.path.dirname(os.path.realpath(__file__)), 'configs/create_repo.hjson')


# see https://docker-py.readthedocs.io/en/stable/containers.html
client = docker.from_env()
#there's a filter for this on the images list
if c.DOCKER_IMAGE in list(map(lambda x:x.pop(),(filter(lambda x:x != [],(map(lambda x:x.tags,client.images.list())))))):
    print(f"Found docker image {c.DOCKER_IMAGE}")
else:
    print(f"Did not find docker image {c.DOCKER_IMAGE}. Must be built.")
    client.images.build(path=c.SCRIPT_PWD, dockerfile=c.DOCKER_FILE,tag=c.DOCKER_IMAGE,quiet=False,buildargs=c.DOCKER_BUILDARGS)


print(f"Repository: {c.REPOSITORY_NAME}")
print(f"Repository Description: {c.REPOSITORY_DESCRIPTION}")



for bash_plugin in c.bash_plugins:
    container = client.containers.run(c.DOCKER_IMAGE, bash_plugin.DOCKER_SCRIPT, **c.DOCKER_OPTS)
    if container:
        print(c.file_plugins)
        print(c.dir_plugins)
        print(c.env_plugins)

    container.wait()

    if pathlib.Path(f"{c.SCRIPT_PWD}/logs").exists():
        open(f"{c.SCRIPT_PWD}/last_logs.txt", 'wb').write(container.logs())
        open(f"{c.SCRIPT_PWD}/logs/{c.ARCH}-{c.SUBARCH}-{datetime.now().strftime('%y-%m-%d-%H:%M:%S')}.txt", 'wb').write(container.logs())
    else:
        print("create a logs/ directory to save as a timestamped file")

    container.stop()
    container.remove()

# repo_conf = f"""
# [{REPOSITORY_NAME}]
# desc = {REPOSITORY_DESCRIPTION}
# repo=file://{entropy_artifacts}#bz2
# enabled = true
# pkg = file://{entropy_artifacts}
# """
#
# if os.path.exists(f"{entropy_artifacts}/standard"):
#     print(f"The kantoo repository files are in {entropy_artifacts}")
#     print("Now you can upload its content where you want")
#     print("")
#     print("Here it is the repository file how will look like ")
#     print("(if you plan to upload it to a webserver, modify the URI accordingly)")
#     print("This is an example of repo configuration in Entropy")
#     print(repo_conf)
# else:
#     print("Something failed :(")
#     print("check the log")
#


