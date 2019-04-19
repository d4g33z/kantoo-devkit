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
import json
import hashlib
import pathlib
import tempfile

from functools import reduce
from collections import OrderedDict
from datetime import datetime

def dd(cwd, config, skip, pretend, interactive):
    client = docker.from_env()

    config = DockerDriver(pathlib.Path(config).absolute())

    if pretend:
        [setattr(p, 'skip', True) for p in filter(lambda x: x.exec, config.plugins)]

    # use cli --skip to set certain exec plugins to skip=True
    [setattr(p, 'skip', True) for p in filter(lambda x: getattr(x, 'name') in skip, config.plugins)]


    # try to find initial image or create it
    if not pretend:
        config.initialize(cwd)

    if interactive:
        config.interact('initial')

    #start the sequence of operations
    config.start(cwd,interactive)

TMPFS_PATH=pathlib.Path('tmpfs').absolute()
class DockerDriver:
    def __init__(self,config_path):
        self.name = config_path.parts[-1].split('.')[0]
        self.client = docker.from_env()
        self.config = hjson.load(open(config_path, 'r'))
        self._set_config_attrs()
        self._set_plugins()
        self._set_docker_opts()

    def initialize(self,working_dir_path):
        if self.client.images.list(f"{self.DOCKER_REPO}:initial"):
            return
        try:
            print(f"Initializing image from {self.DOCKER_INITIAL_IMAGE}")
            self._rm_mounts(self.client.images.list(f"{self.DOCKER_INITIAL_IMAGE}").pop(),f"{self.DOCKER_REPO}:initial")
        except IndexError:
            yn = input(f"{self.DOCKER_INITIAL_IMAGE} not found. Build it from Funtoo stage3?")
            if yn == 'y' or yn =='Y':
                self.client.images.build(path=working_dir_path, dockerfile=self.DOCKER_FILE, tag=f"{self.DOCKER_INITIAL_IMAGE}",
                                    quiet=False, buildargs=self.DOCKER_BUILDARGS)
                self._rm_mounts(self.client.images.list(f"{self.DOCKER_INITIAL_IMAGE}"),f"{self.DOCKER_REPO}:initial")
            else:
                print('No image to work from.')
                raise Exception

    def start(self,cwd,interactive=False):
        CURRENT_DOCKER_IMAGE=f"{self.DOCKER_REPO}:initial"
        prompt = ">>>"
        for exec_plugin in filter(lambda x: x.exec, self.plugins):
            print(f"{prompt}" * 20)
            if not self.client.images.list(f"{self.DOCKER_REPO}:{exec_plugin.name}") and exec_plugin.skip:
                print(f"You requested skipping {exec_plugin.name} but no image exists yet. Exiting.")
                return

            # images must exist at this point for each exec_plugin
            if not (self.client.images.list(f"{self.DOCKER_REPO}:{exec_plugin.name}") and exec_plugin.skip):
                print(f"Creating container of {CURRENT_DOCKER_IMAGE} to run {exec_plugin.name} on.")
                container = self.run(CURRENT_DOCKER_IMAGE)
                CURRENT_DOCKER_IMAGE = f"{self.DOCKER_REPO}:{exec_plugin.name}"
            else:
                # skipping and a container of this exec_plugin exists
                print(f"Not creating container of existing image {self.DOCKER_REPO}:{exec_plugin.name} to run plugin on.")
                print(f"{exec_plugin.name} skipped")
                CURRENT_DOCKER_IMAGE = f"{self.DOCKER_REPO}:{exec_plugin.name}"
                continue

            # not exec_plugin.skip has to be true
            exit_code, output = self.exec_run(container,exec_plugin)
            # TODO test the exec_result and decide whether to proceed, report or fix a problem
            with open(f"{cwd}/output.txt", 'wb') as f:
                for chunk in output:
                    f.write(chunk)

            if pathlib.Path(f"{cwd}/logs").exists():
                open(
                    f"{cwd}/logs/{self.ARCH}-{self.SUBARCH}-{exec_plugin.name}-{datetime.now().strftime('%y-%m-%d-%H:%M:%S')}.txt",
                    'wb').write(open(f"{cwd}/output.txt", 'rb').read())
            else:
                print("Create a logs/ directory to save a timestamped file of container logs")

            image = container.commit(self.DOCKER_REPO, exec_plugin.name)
            print(f"{container.name} : {image.id} committed")

            if interactive:
                self.interact(exec_plugin.name)

    def run(self,docker_image):
        container = self.client.containers.run(docker_image, None, **self.DOCKER_OPTS)
        return container

    def exec_run(self,container,exec_plugin):
        exit_code, output = container.exec_run(
            ['sh', '-c', f". {exec_plugin.docker_exe}"],environment=exec_plugin.docker_env,detach=False,stream=True)
        return exit_code, output

    def _set_plugins(self):
        self.plugins = self._plugin_factory(self.config.get('plugins',{}))
        self.env_plugins = [EnvPlugin(var, value) for var, value in self.config.get('envplugins', {}).items()]
        if hasattr(self,'SYSROOT_DIR'):
            self.plugins += self._sysroot_plugin_factory(pathlib.Path(self.SYSROOT_DIR).absolute())

    def _plugin_factory(self, plugin_block):
        return list(map(lambda x, y, z: x.write(y, **z),
                        # create the objs
                        [Plugin(k, **v) for k, v in plugin_block.items()],
                        # get the text from the hjson file or a file on disk
                        # [x.get('text', open(self.SCRIPT_PWD.joinpath(x.get('path', '/dev/null')), 'r').read()) \
                        [x.get('text', open(pathlib.Path(x.get('path', '/dev/null')).absolute(), 'r').read()) \
                                if not pathlib.Path(x.get('path', '/dev/null')).is_dir() else None \
                         for x in plugin_block.values()],
                        # get the env or f-string vars using value on Config obj or those set in the block itself
                        [{i[0]: i[1] if i[1] != '' else getattr(self, i[0]) \
                          for i in filter(lambda y: y[0] == y[0].upper(), x.items())} for x in plugin_block.values()]))

    def _sysroot_plugin_factory(self, sysroot_path):
        dir_configs_objs = {}
        file_configs_objs = {}
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

    def _set_config_attrs(self):
        # all-caps root level keys become attributes
        [setattr(self, y, self.config.get(y)) for y in filter(lambda x: x == x.upper(), self.config.keys())]

        # a default value
        if not hasattr(self, 'DOCKER_FILE'): setattr(self, 'DOCKER_FILE', 'Dockerfile')
        if not hasattr(self, 'DOCKER_INIT_IMG'): setattr(self, 'DOCKER_INIT_IMG', None)

        if self.DOCKER_INIT_IMG:
            assert  ':' in self.DOCKER_INIT_IMG

        self.plugins = self._plugin_factory(self.config.get('plugins',{}))

        self.env_plugins = [EnvPlugin(var, value) for var, value in self.config.get('envplugins', {}).items()]

        if hasattr(self,'SYSROOT_DIR'):
            self.plugins += self._sysroot_plugin_factory(pathlib.Path(self.SYSROOT_DIR).absolute())

    def _set_docker_opts(self):
        # DOCKER_OPTS is created in the hjson config file
        self.DOCKER_OPTS.update(
            {'volumes': {
                **{str(x.exe_path): x.exe_volume for x in self.plugins if x.exec},
                **{str(pathlib.Path(
                    x.tmp_path if not pathlib.Path(x.path).is_dir() else x.path)): x.volume for x in
                   filter(lambda x: x.tmp_path is not None, self.plugins)}},
            })

        self.DOCKER_OPTS.update(
            {'environment': list(reduce(lambda x, y: x + y, [z.docker_env for z in self.env_plugins], []))})
        self.DOCKER_OPTS.update({'working_dir': '/'})

    def _update(self, **kwargs):
        [setattr(self, k, v) for k, v in kwargs.items()]

    @property
    def DOCKER_BUILDARGS(self):
        return {'ARCH': self.ARCH, 'SUBARCH': self.SUBARCH}

    @property
    def TMPFS(self):
        return TMPFS_PATH
    @property
    def DOCKER_REPO(self):
        return f"{self.OS}/{self.ARCH}/{self.SUBARCH}/{self.name}"

    @property
    def DOCKER_INITIAL_IMAGE(self):
        return f"{self.OS}/{self.ARCH}/{self.SUBARCH}/{self.DOCKER_INIT_IMG}"

    def _rm_mounts(self,image,tag):
        data_dir = self.TMPFS.joinpath('data') if self.TMPFS else pathlib.Path(tempfile.mkdtemp())
        input_file = self.TMPFS.joinpath('input_file') if self.TMPFS else pathlib.Path(tempfile.mkstemp()[1])
        output_file = self.TMPFS.joinpath('output_file') if self.TMPFS else pathlib.Path(tempfile.mkstemp()[1])

        os.system(f"mkdir -p {data_dir}")
        os.system(f"docker save {image.tags[0]} > {input_file}")
        os.system(f"tar xf {input_file} -C {data_dir}")

        manifest_file = "manifest.json"
        manifest_filename = data_dir.joinpath(manifest_file)
        with open(manifest_filename) as fp:
            manifest = json.load(fp)
        replaced = {}
        for item in range(len(manifest)):
            config_file = manifest[item]["Config"]
            config_filename = data_dir.joinpath(config_file)
            replaced[config_filename] = None
        #
        for item in range(len(manifest)):
            config_file = manifest[item]["Config"]
            config_filename = data_dir.joinpath(config_file)
            with open(config_filename) as fp:
                config = json.load(fp)
            old_config_text = json.dumps(config).encode('utf-8') # to compare later

            for CONFIG in ['config','Config','container_config']:
                if CONFIG not in config:
                    #logg.debug("no section '%s' in config", CONFIG)
                    continue
                #logg.debug("with %s: %s", CONFIG, config[CONFIG])
                if config[CONFIG]['Volumes'] is not None:
                    del config[CONFIG]['Volumes']

        new_config_text = json.dumps(config).encode('utf-8')

            # for CONFIG in ['history']:
            #     if CONFIG in config:
            #         myself = os.path.basename(sys.argv[0])
            #         config[CONFIG] += [ {"empty_layer": True,
            #             "created_by": "%s #(%s)" % (myself, __version__),
            #             "created": datetime.datetime.utcnow().isoformat() + "Z"} ]
            #         new_config_text = json.dumps(config)
        new_config_md = hashlib.sha256()
        new_config_md.update(new_config_text)
        for collision in range(1, 100):
            new_config_hash = new_config_md.hexdigest()
            new_config_file = f"{new_config_hash}.json"
            new_config_filename = data_dir.joinpath(new_config_file)
            if new_config_filename in list(replaced.keys()) or new_config_filename in list(replaced.values()):
                new_config_md.update(" ")
                continue
            break
        with open(new_config_filename, "wb") as fp:
            fp.write(new_config_text)
        manifest[item]["Config"] = new_config_file
        replaced[config_filename] = new_config_filename
        if manifest[item]["RepoTags"]:
            manifest[item]["RepoTags"] = [tag]
        manifest_text = json.dumps(manifest).encode('utf-8')
        manifest_filename = data_dir.joinpath(manifest_file)

        with open(manifest_filename, "wb") as fp:
            fp.write(manifest_text)

        os.system(f"cd {data_dir} && tar cf {output_file} .")
        os.system(f"docker load -i {output_file}")
        os.system(f"rm -rf {data_dir} {input_file} {output_file}")



    def _interactive_run_cmd(self, tag):
        volumes = [f"-v {str(path)}:{info.get('bind')}:{info.get('mode')}" for path, info in
                   self.DOCKER_OPTS.get('volumes').items()]
        envs = [f"-e {env}" for env in self.DOCKER_OPTS.get('environment')]
        return f"docker run --rm {' '.join(volumes)} {' '.join(envs)} -ti {self.DOCKER_REPO}:{tag}"


    def interact(self, tag='initial'):
        try:
            ip = get_ipython()
            ip.system(self._interactive_run_cmd(tag))
        except NameError:
            os.system(self._interactive_run_cmd(tag))
        except:
            print('cannot interact')
        return

    def images(self):
        return self.client.images.list(self.DOCKER_REPO)

    def image_cleanup(self):
        # remove danglers
        [self.client.images.remove(image.id) for image in self.client.images.list(filters={'dangling': True})]

        # TODO: remove all running containers first
        class RemovalFinished(Exception):
            pass

        def _image_cleanup(image):
            print(f"about to remove image {image.tags.pop()}")
            if input('remove image? [y/N]') == 'y':
                try:
                    self.client.images.remove(image.id)
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
                       [[x, x.tags.pop().split(':').pop()] for x in self.images()]))))]
        except RemovalFinished:
            pass

        yn = input(f"Remove {self.DOCKER_INITIAL_IMAGE} as well?")
        if yn == 'y' or yn =='Y':
        #remove DOCKER_INITIAL_IMAGE
            self.client.images.remove(self.images().pop().id)
        return
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
        # self.exe_volume = {'bind': f"/entropy/bin/{self.name}", 'mode': 'ro'} if exec else None
        self.exe_volume = {'bind': f"/entropy/bin/{self.name}", 'mode': 'ro'} if exec else None
        # ignored if self.path.is_dir()
        self.tmp_path = pathlib.Path(tempfile.mkstemp()[1]) if path or text else None
        # self.volume = {'bind': self.bind, 'mode': self.mode} if path or text else None
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



