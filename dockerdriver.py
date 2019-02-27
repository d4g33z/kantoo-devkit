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
import click
from datetime import datetime


@click.command()
@click.option('--config',default='configs/hello_world.hjson', help='A relative path to an hjson file')
@click.option('--commit',default=True,type=bool,help='Preserve the result of each script plugin as an image')
def dockerdriver(config,commit):

    # c = Config(os.path.dirname(os.path.realpath(__file__)), 'configs/hello_goodbye_world.hjson')
    c = Config(os.path.dirname(os.path.realpath(__file__)), config)


    # see https://docker-py.readthedocs.io/en/stable/containers.html
    client = docker.from_env()
    #there's a filter for this on the images list
    if c.DOCKER_IMAGE in list(map(lambda x:x.pop(),(filter(lambda x:x != [],(map(lambda x:x.tags,client.images.list())))))):
        print(f"Found docker image {c.DOCKER_IMAGE}")
    else:
        print(f"Did not find docker image {c.DOCKER_IMAGE}. Must be built.")
        client.images.build(path=c.SCRIPT_PWD, dockerfile=c.DOCKER_FILE,tag=c.DOCKER_IMAGE,quiet=False,buildargs=c.DOCKER_BUILDARGS)

    prompt = ">>>"
    for bash_plugin in c.bash_plugins:
        container = client.containers.run(c.DOCKER_IMAGE, bash_plugin.DOCKER_SCRIPT, **c.DOCKER_OPTS)
        print(f"{prompt}"*10)
        print(f"{prompt}BashPlugin: {bash_plugin}")
        if container:
            print(f"{prompt}FilePlugins: {c.file_plugins}")
            print(f"{prompt}DirPlugins: {c.dir_plugins}")
            print(f"{prompt}EnvPlugins: {c.env_plugins}")

        container.wait()

        open(f"{c.SCRIPT_PWD}/last_logs.txt", 'wb').write(container.logs())
        if pathlib.Path(f"{c.SCRIPT_PWD}/logs").exists():
            open(f"{c.SCRIPT_PWD}/logs/{c.ARCH}-{c.SUBARCH}-{datetime.now().strftime('%y-%m-%d-%H:%M:%S')}.txt", 'wb').write(container.logs())
        else:
            print("create a logs/ directory to save as a timestamped file")

        if commit:
            container.commit(c.DOCKER_REPO,f"{bash_plugin.name}")
            c.DOCKER_TAG= f"{bash_plugin.name}"

        container.stop()
        container.remove()
    # else:
    #     print('no commit')
    #     container = client.containers.run(c.DOCKER_IMAGE, None, **c.DOCKER_OPTS)
    #     for bash_plugin in c.bash_plugins:
    #         exec_result = container.exec_run(bash_plugin.DOCKER_SCRIPT, environment=bash_plugin.docker_env)
    #         print(f"{prompt}"*10)
    #         print(f"{prompt}BashPlugin: {bash_plugin}")
    #         if container:
    #             print(f"{prompt}FilePlugins: {c.file_plugins}")
    #             print(f"{prompt}DirPlugins: {c.dir_plugins}")
    #             print(f"{prompt}EnvPlugins: {c.env_plugins}")
    #
    #
    #         open(f"{c.SCRIPT_PWD}/last_logs.txt", 'wb').write(exec_result.output)
    #         if pathlib.Path(f"{c.SCRIPT_PWD}/logs").exists():
    #             open(f"{c.SCRIPT_PWD}/logs/{c.ARCH}-{c.SUBARCH}-{datetime.now().strftime('%y-%m-%d-%H:%M:%S')}.txt", 'wb').write(exec_result.output)
    #         else:
    #             print("create a logs/ directory to save as a timestamped file")
    #
    #     container.stop()
    #     container.remove()
if __name__ == '__main__':
    dockerdriver()
