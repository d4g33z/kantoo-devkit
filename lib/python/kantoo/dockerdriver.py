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

import docker
import pathlib
from datetime import datetime
from .kantoo import Config

def dockerdriver(cwd,config,skip,pretend,interactive):

    client = docker.from_env()
    config = Config(cwd,config)

    if pretend:
        [setattr(bp,'skip',True) for bp in config.exec_plugins]

    #use cli --skip to set certain exec plugins to skip=True
    [setattr(bp,'skip',True) for bp in filter(lambda x:getattr(x,'name') in skip,config.exec_plugins)]


    #https://docs.docker.com/engine/api/v1.29/#tag/Image
    #there's a filter for this on the images list, probably. can't figure out the api
    if config.DOCKER_IMAGE in list(map(lambda x:x.pop(),(filter(lambda x:x != [],(map(lambda x:x.tags,client.images.list())))))):
        print(f"Found docker image {config.DOCKER_IMAGE}")
    else:
        print(f"Did not find docker image {config.DOCKER_IMAGE}. Will be initialized as a Funtoo stage3.")
        client.images.build(path=config.SCRIPT_PWD, dockerfile=config.DOCKER_FILE,tag=config.DOCKER_IMAGE,quiet=False,buildargs=config.DOCKER_BUILDARGS)

    prompt = ">>>"
    for exec_plugin in config.exec_plugins:
        print(f"{prompt}"*20)
        if not client.images.list(f"{config.DOCKER_REPO}:{exec_plugin.name}") and  exec_plugin.skip:
            print(f"you requested skipping {exec_plugin.name} but not image exists; exiting.")
            return

        #images must exist at this point for each exec_plugin
        if not (client.images.list(f"{config.DOCKER_REPO}:{exec_plugin.name}") and exec_plugin.skip):
            print(f"creating container of {config.DOCKER_TAG} to run plugin on")
            container = client.containers.run(config.DOCKER_IMAGE, None, **config.DOCKER_OPTS)
            config.update(DOCKER_TAG=f"{exec_plugin.name}")
        else :
            #skipping and a container of this exec_plugin exists
            print(f"not creating container of existing image {config.DOCKER_REPO}:{exec_plugin.name} to run plugin on")
            print(f"{exec_plugin.name} skipped" )
            config.update(DOCKER_TAG=f"{exec_plugin.name}")
            continue

        print(f"{prompt} ExecPlugin: {exec_plugin}")
        print(f"{prompt} FilePlugins: {config.file_plugins}")
        print(f"{prompt} DirPlugins: {config.dir_plugins}")
        print(f"{prompt} EnvPlugins: {config.env_plugins}")

        # not exec_plugin.skip has to be true
        exec_result = container.exec_run(['sh','-c',f". {exec_plugin.DOCKER_SCRIPT}"] , environment=exec_plugin.docker_env)



        open(f"{config.SCRIPT_PWD}/logs/last_logs.txt", 'wb').write(exec_result.output)
        if pathlib.Path(f"{config.SCRIPT_PWD}/logs").exists():
            open(f"{config.SCRIPT_PWD}/logs/{config.ARCH}-{config.SUBARCH}-{datetime.now().strftime('%y-%m-%d-%H:%M:%S')}.txt", 'wb').write(exec_result.output)
        else:
            print("create a logs/ directory to save as a timestamped file")



        image = container.commit(config.DOCKER_REPO,config.DOCKER_TAG)
        print(f"{container.name} : {image.id} committed")

        if interactive:
            config.interact(exec_plugin.name)




