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

# local

import docker
import hjson

# system
import os
import pathlib
import tempfile

from functools import reduce
from collections import OrderedDict
from datetime import datetime


# TODO if an image exists with the name of an executalbe plugin, should it be automatically skipped?

def dd(cwd, config, skip, pretend, interactive):
    client = docker.from_env()
    config = PluginConfig(cwd, config)

    if pretend:
        [setattr(p, 'skip', True) for p in filter(lambda x: x.exec, config.plugins)]

    # use cli --skip to set certain exec plugins to skip=True
    [setattr(p, 'skip', True) for p in filter(lambda x: getattr(x, 'name') in skip, config.plugins)]

    # https://docs.docker.com/engine/api/v1.29/#tag/Image
    # there's a filter for this on the images list, probably. can't figure out the api
    if config.DOCKER_IMAGE in list(
            map(lambda x: x.pop(), (filter(lambda x: x != [], (map(lambda x: x.tags, client.images.list())))))):
        print(f"Found docker image {config.DOCKER_IMAGE}.")
    else:
        print(f"Did not find docker image {config.DOCKER_IMAGE}. Will be initialized as a Funtoo stage3.")
        client.images.build(path=str(config.SCRIPT_PWD), dockerfile=config.DOCKER_FILE, tag=config.DOCKER_IMAGE,
                            quiet=False, buildargs=config.DOCKER_BUILDARGS)
    if interactive:
        config.interact()

    prompt = ">>>"
    for exec_plugin in filter(lambda x: x.exec, config.plugins):
        print(f"{prompt}" * 20)
        if not client.images.list(f"{config.DOCKER_REPO}:{exec_plugin.name}") and exec_plugin.skip:
            print(f"You requested skipping {exec_plugin.name} but no image exists yet. Exiting.")
            return

        # images must exist at this point for each exec_plugin
        if not (client.images.list(f"{config.DOCKER_REPO}:{exec_plugin.name}") and exec_plugin.skip):
            print(f"Creating container of {config.DOCKER_TAG} to run {exec_plugin.name} on.")
            container = client.containers.run(config.DOCKER_IMAGE, None, **config.DOCKER_OPTS)
            config._update(DOCKER_TAG=f"{exec_plugin.name}")
        else:
            # skipping and a container of this exec_plugin exists
            print(f"Not creating container of existing image {config.DOCKER_REPO}:{exec_plugin.name} to run plugin on.")
            print(f"{exec_plugin.name} skipped")
            config._update(DOCKER_TAG=f"{exec_plugin.name}")
            continue

        # not exec_plugin.skip has to be true
        exec_result = container.exec_run(['sh', '-c', f". {exec_plugin.docker_exe}"],
                                         environment=exec_plugin.docker_env)

        # TODO test the exec_result and decide whether to proceed, report or fix a problem

        open(f"{config.SCRIPT_PWD}/logs/last_logs.txt", 'wb').write(exec_result.output)
        if pathlib.Path(f"{config.SCRIPT_PWD}/logs").exists():
            open(
                f"{config.SCRIPT_PWD}/logs/{config.ARCH}-{config.SUBARCH}-{datetime.now().strftime('%y-%m-%d-%H:%M:%S')}.txt",
                'wb').write(exec_result.output)
        else:
            print("Create a logs/ directory to save a timestamped file of container logs")

        image = container.commit(config.DOCKER_REPO, config.DOCKER_TAG)
        print(f"{container.name} : {image.id} committed")

        if interactive:
            config.interact(exec_plugin.name)



# -----------------------------------------------------------------------------------------
# unified exec,file and dir plugin
class Plugin:
    def __init__(self, name, text=None, path=None, bind=None, mode='ro', exec=False, skip=False, tmpfs=None, **kwargs):
        assert not (text and path)
        assert not (bind and exec)
        assert not (tmpfs and (path or text))
        # what happens if there is just bind?
        self.path = pathlib.Path(path) if path else '/dev/null'  # it has a text element
        self.bind = bind if bind else f"/entropy/plugins/{name}"
        self.text = text
        self.name = name
        self.mode = mode
        self.exec = exec
        self.skip = skip
        self.tmpfs = tmpfs if tmpfs else ''

        self.exe_path = pathlib.Path(tempfile.mkstemp()[1]) if exec else None
        self.exe_volume = {'bind': f"/entropy/bin/{self.name}", 'mode': 'ro'} if exec else None
        # ignored if self.path.is_dir()
        self.tmp_path = pathlib.Path(tempfile.mkstemp()[1]) if path or text else None
        self.volume = {'bind': self.bind, 'mode': self.mode} if path or text else None
        # see https://docker-py.readthedocs.io/en/stable/api.html#docker.types.Mount
        # set the arguements to create a new Mount object
        # self.tmpfs = {self.bind:self.tmpfs} if not (path or text) else {}
        # self.tmpfs = {
        #     'target':self.bind,
        #     'source':'',
        #     'type':'tmpfs',
        #     # 'read_only': False,
        #     # 'tmpfs_size':'',
        #     # 'tmpfs_mode':0o775,
        # } if not (path or text) else {}

    def write(self, txt, **vars):
        if txt is None: return self
        if self.tmp_path is None: return self
        # extract mandatory shebang
        executable = txt.split('\n')[0].split(' ').pop() if self.exec else None
        if not executable:
            # use f-string subsitution
            self.tmp_path.write_text(txt.format(**vars))
        else:
            self.docker_env = [f"{var}={value}" for var, value in vars.items()]
            self.docker_exe = self.exe_volume.get('bind')
            self.tmp_path.write_text(txt)
            self.exe_path.write_text(f"#!/usr/bin/env sh\n {executable} {self.volume.get('bind') }\n")
        return self

    def __repr__(self):
        return f"{self.volume.get('bind')}"


class EnvPlugin:
    def __init__(self, var, value):
        self.var = var
        self.value = value
        self.path = None  # not needed if we don't try to update docker volumes with this obj

    @property
    def docker_env(self):
        return [f"{self.var}={self.value}"]

    def __repr__(self):
        return f"{self.var} = {self.value}"


class PluginConfig:
    'A configuration object for docker containers'

    def __init__(self, script_pwd, config_rel_path):
        self.SCRIPT_PWD = pathlib.Path(script_pwd).absolute().resolve()
        self.config = hjson.load(open(self.SCRIPT_PWD.joinpath(config_rel_path), 'r'))

        # all-caps root level keys become attributes
        [setattr(self, y, self.config.get(y)) for y in filter(lambda x: x == x.upper(), self.config.keys())]

        # a default value
        if not hasattr(self, 'DOCKER_FILE'): setattr(self, 'DOCKER_FILE', 'Dockerfile')

        self.plugins = self._plugin_factory(self.config.get('plugins'))

        self.env_plugins = [EnvPlugin(var, value) for var, value in self.config.get('envplugins', {}).items()]

        if hasattr(self,'SYSROOT_DIR'):
            self.plugins += self._sysroot_plugin_factory(self.SYSROOT_DIR)

        # DOCKER_OPTS is created in the hjson config file
        self.DOCKER_OPTS.update(
            {'volumes': {
                **{str(x.exe_path): x.exe_volume for x in self.plugins if x.exec},
                **{str(self.SCRIPT_PWD.joinpath(
                    x.tmp_path if not self.SCRIPT_PWD.joinpath(x.path).is_dir() else x.path)): x.volume for x in
                   filter(lambda x: x.tmp_path is not None, self.plugins)}},
            })

        self.DOCKER_OPTS.update(
            {'environment': list(reduce(lambda x, y: x + y, [z.docker_env for z in self.env_plugins], []))})
        self.DOCKER_OPTS.update({'working_dir': '/'})

        # see https://docs.docker.com/storage/tmpfs/
        # self.DOCKER_OPTS.update({'tmpfs':reduce(lambda x,y:{**x,**y},map(lambda x:x.tmpfs,self.plugins))})
        # see https://docker-py.readthedocs.io/en/stable/api.html#docker.types.Mount
        # self.DOCKER_OPTS.update({'mount':list(map(lambda x:docker.types.Mount(**x),map(lambda x:x.tmpfs,filter(lambda x:x.tmpfs != {},self.plugins))))})

        self.DOCKER_BUILDARGS = {
            'ARCH': self.ARCH,
            'SUBARCH': self.SUBARCH, }

    def _plugin_factory(self, plugin_block):
        return list(map(lambda x, y, z: x.write(y, **z),
                        # create the objs
                        [Plugin(k, **v) for k, v in plugin_block.items()],
                        # get the text from the hjson file or a file on disk
                        [x.get('text', open(self.SCRIPT_PWD.joinpath(x.get('path', '/dev/null')), 'r').read()) \
                             if not self.SCRIPT_PWD.joinpath(x.get('path', '/dev/null')).is_dir() else None \
                         for x in plugin_block.values()],
                        # get the env or f-string vars using value on Config obj or those set in the block itself
                        [{i[0]: i[1] if i[1] != '' else getattr(self, i[0]) \
                          for i in filter(lambda y: y[0] == y[0].upper(), x.items())} for x in plugin_block.values()]))

    def _sysroot_plugin_factory(self, sysroot_path='lib/sysroot'):
        dir_configs_objs = {}
        file_configs_objs = {}
        sysroot_path = self.SCRIPT_PWD.joinpath(pathlib.Path(sysroot_path))
        for dirpath, dirs_to_bind, files_to_bind in os.walk(sysroot_path, followlinks=False):
            rel_link_paths = map(lambda x: x.relative_to(sysroot_path),
                                 filter(lambda x: x.is_symlink(),
                                        [pathlib.Path(dirpath).joinpath(pathlib.Path(dir_to_bind)) for dir_to_bind in
                                         dirs_to_bind]))
            dir_configs_objs = \
                {
                    **dir_configs_objs,
                    **OrderedDict(**{
                        str(rel_link_path): OrderedDict(
                            path=str(sysroot_path.joinpath(rel_link_path).resolve()),
                            bind=str(pathlib.Path('/').joinpath(rel_link_path)),
                            exec=False) for rel_link_path in rel_link_paths})
                }

            rel_file_paths = map(lambda x: x.relative_to(sysroot_path),
                                 [pathlib.Path(dirpath).joinpath(pathlib.Path(file_to_bind)) for file_to_bind in
                                  files_to_bind])

            file_configs_objs = \
                {
                    **file_configs_objs,
                    **OrderedDict(**{
                        str(rel_file_path): OrderedDict(
                            path=str(sysroot_path.joinpath(rel_file_path).resolve()),
                            bind=str(pathlib.Path('/').joinpath(rel_file_path)),
                            exec=False) for rel_file_path in rel_file_paths})

                }

        return self._plugin_factory(dir_configs_objs) + self._plugin_factory(file_configs_objs)


    def _update(self, **kwargs):
        [setattr(self, k, v) for k, v in kwargs.items()]

    @property
    def DOCKER_REPO(self):
        return f"{self.OS}/{self.ARCH}/{self.SUBARCH}"

    @property
    def DOCKER_IMAGE(self):
        return f"{self.DOCKER_REPO}:{self.DOCKER_TAG}"

    def interactive_run_cmd(self, tag):
        volumes = [f"-v {str(path)}:{info.get('bind')}:{info.get('mode')}" for path, info in
                   self.DOCKER_OPTS.get('volumes').items()]
        envs = [f"-e {env}" for env in self.DOCKER_OPTS.get('environment')]
        # return f"docker run --rm {' '.join(volumes)} {' '.join(envs)} -ti {self.DOCKER_REPO}:{self.DOCKER_TAG}"
        return f"docker run --rm {' '.join(volumes)} {' '.join(envs)} -ti {self.DOCKER_REPO}:{tag}"

    def interact(self, tag='stage3'):
        "drop to an interactive shell of a container of self.DOCKER_IMAGE"
        try:
            ip = get_ipython()
            ip.system(self.interactive_run_cmd(tag))
        except NameError:
            os.system(self.interactive_run_cmd(tag))
        except:
            print('cannot interact')
        return

    def images(self, client):
        return list(filter(lambda x: x in client.images.list(f"{self.DOCKER_REPO}"), client.images.list()))

    def image_cleanup(self, client):
        # remove danglers
        [client.images.remove(image.id) for image in client.images.list(filters={'dangling': True})]

        # TODO: remove all running containers first
        class RemovalFinished(Exception):
            pass

        def _image_cleanup(image):
            print(f"about to remove image {image.tags.pop()}")
            if input('remove image? [y/N]') == 'y':
                try:
                    client.images.remove(image.id)
                except:
                    print(f"images can only be removed in the reverse order they were created")
                    raise RemovalFinished
                print('image removed')
            else:
                print('image not removed and can only be removed in the reverse order to creation. you are done')
                raise RemovalFinished

        try:
            [_image_cleanup(im) for im in list(map(lambda a: a.pop(), (
                filter(lambda y: y.pop() in map(lambda z: z.name, filter(lambda x: x.exec, self.plugins)),
                       [[x, x.tags.pop().split(':').pop()] for x in self.images(client)]))))]
        except RemovalFinished:
            return
