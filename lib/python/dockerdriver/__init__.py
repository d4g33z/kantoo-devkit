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
import eliot

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
    eliot.to_file(open(f"{cwd}/logs/eliot.txt",'w'))
    # eliot.to_file(open(f"{cwd}/logs/eliot-{datetime.now().strftime('%y-%m-%d-%H:%M:%S')}.txt",'wb'))

    with eliot.start_action(action_type='DockerDriver',cwd=str(cwd),config=config):
        config_path = pathlib.Path(config)
        config = hjson.load(open(cwd.joinpath(config_path), 'r'))
        name = config_path.parts[-1].split('.')[0]
        config = DockerDriver(cwd,name,config)

    if pretend:
        [setattr(p, 'skip', True) for p in filter(lambda x: x.exec, config.plugins)]

    # use cli --skip to set certain exec plugins to skip=True
    [setattr(p, 'skip', True) for p in filter(lambda x: getattr(x, 'name') in skip, config.plugins)]

    # try to find initial image or create it
    if not pretend:
        with eliot.start_action(action_type='initialize'):
            config.initialize()

    if interactive:
        config.interact('initial')

    #start the sequence of operations

    with eliot.start_action(action_type='start'):
        config.start(interactive)

TMPFS_PATH=pathlib.Path('tmpfs').absolute()
class DockerDriver:

    @property
    def DOCKER_TMPFS(self):
        return pathlib.Path(self.TMPFS).absolute() if self.TMPFS else TMPFS_PATH

    @property
    def DOCKER_BUILDARGS(self):
        return {'ARCH': self.ARCH, 'SUBARCH': self.SUBARCH, 'DIST': self.DIST, 'STAGE3_ARCHIVE': self.STAGE3_ARCHIVE}

    @property
    def DOCKER_REPO(self):
        return f"{self.OS}/{self.ARCH}/{self.SUBARCH}/{self.name}"

    @property
    def DOCKER_INITIAL_IMAGE(self):
        return f"{self.OS}/{self.ARCH}/{self.SUBARCH}/{self.DOCKER_INIT_IMG}"

    def __init__(self,cwd_path,config_path):
        self.cwd = cwd_path
        self.config = hjson.load(open(cwd_path.joinpath(config_path), 'r'))
        self.name = config_path.parts[-1].split('.')[0]
        self.client = docker.from_env()
        with eliot.start_action(action_type='_set_config_attrs'):
            self._set_config_attrs()
        with eliot.start_action(action_type='_set_plugins'):
            self._set_plugins()
        with eliot.start_action(action_type='_set_docker_opts'):
            self._set_docker_opts()

    def initialize(self):
        if self.client.images.list(f"{self.DOCKER_REPO}:initial"):
            eliot.Message.log(message_type='info',msg=f"{self.DOCKER_REPO}:initial found")
            return
        try:
            eliot.Message.log(message_type='info',msg=f"Initializing image {self.DOCKER_REPO}:initial from {self.DOCKER_INITIAL_IMAGE}")
            self._rm_mounts(self.client.images.list(f"{self.DOCKER_INITIAL_IMAGE}").pop(),f"{self.DOCKER_REPO}:initial")
        except IndexError:
            yn = input(f"{self.DOCKER_INITIAL_IMAGE} not found. Build it from Funtoo stage3?")
            if yn == 'y' or yn =='Y':
                eliot.Message.log(message_type='info',msg=f"Initializing image from Funtoo stage3")
                self.client.images.build(path=str(self.cwd), dockerfile=self.DOCKER_FILE, tag=f"{self.DOCKER_INITIAL_IMAGE}",
                                    quiet=False, buildargs=self.DOCKER_BUILDARGS,nocache=True)
                self._rm_mounts(self.client.images.list(f"{self.DOCKER_INITIAL_IMAGE}").pop(),f"{self.DOCKER_REPO}:initial")
            else:
                eliot.Message.log(message_type='info',msg=f"No image to work from")
                raise Exception

    def start(self,interactive=False,watch_stdout=False):
        CURRENT_DOCKER_IMAGE=f"{self.DOCKER_REPO}:initial"
        for exec_plugin in filter(lambda x: x.exec, self.plugins):
            print('-'*80)
            if not self.client.images.list(f"{self.DOCKER_REPO}:{exec_plugin.name}") and exec_plugin.skip:
                eliot.Message.log(message_type='info',msg=f"You requested skipping {exec_plugin.name} but no image exists yet. Exiting.")
                print()
                return

            # images must exist at this point for each exec_plugin
            if not (self.client.images.list(f"{self.DOCKER_REPO}:{exec_plugin.name}") and exec_plugin.skip):
                container = self._run(CURRENT_DOCKER_IMAGE)
                eliot.Message.log(message_type='info',msg=f"{exec_plugin.name} : {container.name} created")
                print()
                CURRENT_DOCKER_IMAGE = f"{self.DOCKER_REPO}:{exec_plugin.name}"
            else:
                # skipping and a container of this exec_plugin exists
                eliot.Message.log(messsage_type='info',msg=f"{exec_plugin.name} skipped")
                print()
                CURRENT_DOCKER_IMAGE = f"{self.DOCKER_REPO}:{exec_plugin.name}"
                continue

            # not exec_plugin.skip has to be true
            exit_code, output = self._exec_run(container,exec_plugin)
            # TODO test the exec_result and decide whether to proceed, report or fix a problem
            with open(f"{self.cwd}/output.txt", 'wb') as f:
                for chunk in output:
                    f.write(chunk)
                    if watch_stdout:
                        print(chunk.decode())
                        # eliot.Message.log(message_type='info',msg=chunk.decode())

            log_file = f"{self.cwd}/logs/{self.name}/{self.ARCH}-{self.SUBARCH}-{exec_plugin.name}-{datetime.now().strftime('%y-%m-%d-%H:%M:%S')}.txt"

            if pathlib.Path(f"{self.cwd}/logs").exists():
                pathlib.Path(f"{self.cwd}/logs/{self.name}").mkdir(exist_ok=True)
                open(log_file,'wb').write(open(f"{self.cwd}/output.txt", 'rb').read())
                eliot.Message.log(message_type='log file path',log_file=log_file)
            else:
                eliot.Message.log(message_type='info',msg="Create a logs/ directory to save a timestamped file of container logs")

            image = container.commit(self.DOCKER_REPO, exec_plugin.name)
            eliot.Message.log(message_type='info',msg=f"{exec_plugin.name} : {image.short_id} committed")

            if not exec_plugin.daemonize:
                container.stop()
                container.remove()
            else:
                eliot.Message.log(message_type='info',msg=f"{exec_plugin.name} : {container.name} daemonized")

            if interactive:
                self.interact(exec_plugin.name)


    def interact(self,tag):
        #this should should a shell prompt with exec_plugin.name, not hostname
        try:
            ip = get_ipython()
            ip.system(self._interactive_run_cmd(tag))
        except NameError:
            os.system(self._interactive_run_cmd(tag))
        except:
            eliot.Message.log(message_type='info',msg='cannot interact')
        return

    def container_cleanup(self):
        [c.stop() for c in self.client.containers.list()]
        [c.remove() for c in self.client.containers.list()]

    def images(self):
        return self.client.images.list(self.DOCKER_REPO)

    def image_cleanup(self):
        # remove danglers
        [self.client.images.remove(image.id) for image in self.client.images.list(filters={'dangling': True})]

        self.container_cleanup()

        class RemovalFinished(Exception):
            pass

        def _image_cleanup(image):
            image_tag = image.tags.pop()
            print(f"about to remove image {image_tag}")
            if input('remove image? [y/N]') == 'y':
                try:
                    self.client.images.remove(image.id)
                    eliot.Message.log(message_type='info',msg=f"{image_tag} removed")
                except:
                    eliot.Message.log(message_type='info',msg=f"{image_tag} removal failed.")
                    raise RemovalFinished
            else:
                eliot.Message.log(message_type='info',msg='image not removed and can only be removed in the reverse order to creation. you are done')
                raise RemovalFinished

        try:
            [_image_cleanup(im) for im in list(map(lambda a: a.pop(), (
                filter(lambda y: y.pop() in map(lambda z: z.name, filter(lambda x: x.exec, self.plugins)),
                       [[x, x.tags.pop().split(':').pop()] for x in self.images()]))))]

        except RemovalFinished:
            pass
        if len(self.images()) == 1 and self.images().pop().tags.pop().split(':').pop() == 'initial':
            yn = input(f"Remove {self.DOCKER_REPO}:initial as well?")
            if yn == 'y' or yn =='Y':
                self.client.images.remove(self.images().pop().id)
        return

    def _run(self,docker_image):
        container = self.client.containers.run(docker_image, None, **self.DOCKER_OPTS)
        return container

    def _exec_run(self,container,exec_plugin):
        exit_code, output = container.exec_run(
            ['sh', '-c', f". {exec_plugin.docker_exe}"],environment=exec_plugin.docker_env,detach=False,stream=True)
        return exit_code, output

    def _set_plugins(self):
        with eliot.start_action(action_type='_plugin_factory'):
            self.plugins = self._plugin_factory(self.config.get('plugins',{}))
        self.env_plugins = [EnvPlugin(var, value) for var, value in self.config.get('envplugins', {}).items()]
        if hasattr(self,'SYSROOT_DIR'):
            self.plugins += self._sysroot_plugin_factory(self.cwd.joinpath(pathlib.Path(self.SYSROOT_DIR)))

    def _plugin_factory(self, plugin_block):
        #verbose
        #eliot.Message.log(message_type='plugins',**plugin_block)
        return list(map(lambda x, y, z: x.write(y, **z),
                        # create the objs
                        [Plugin(k, **v) for k, v in plugin_block.items()],
                        # get the text from the hjson file or a file on disk
                        [x.get('text', open(self.cwd.joinpath(x.get('path', '/dev/null')), 'r').read()) \
                                if not self.cwd.joinpath(x.get('path', '/dev/null')).is_dir() else None \
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

        # default values
        if not hasattr(self, 'SYSROOT_DIR'): setattr(self, 'SYSROOT_DIR', 'lib/sysroot')
        if not hasattr(self, 'DOCKER_FILE'): setattr(self, 'DOCKER_FILE', 'Dockerfile')
        if not hasattr(self, 'DOCKER_INIT_IMG'): setattr(self, 'DOCKER_INIT_IMG', 'stage3:initial')

        if self.DOCKER_INIT_IMG:
            assert  ':' in self.DOCKER_INIT_IMG

        eliot.Message.log(message_type='config vars',**{k:self.config.get(k) for k in filter(lambda x: x == x.upper(), self.config.keys())})

    def _set_docker_opts(self):
        # DOCKER_OPTS is created in the hjson config file
        self.DOCKER_OPTS.update(
            {'volumes': {
                **{str(x.exe_path): x.exe_volume for x in self.plugins if x.exec},
                **{str(x.tmp_path if not self.cwd.joinpath(x.path).is_dir() else self.cwd.joinpath(x.path)): x.volume for x in
                   filter(lambda x: x.tmp_path is not None, self.plugins)}},
            })

        self.DOCKER_OPTS.update(
            {'environment': list(reduce(lambda x, y: x + y, [z.docker_env for z in self.env_plugins], []))})
        self.DOCKER_OPTS.update({'working_dir': '/'})

        #verbose
        # eliot.Message.log(message_type='DOCKER_OPTS',**self.DOCKER_OPTS)

    def _update(self, **kwargs):
        [setattr(self, k, v) for k, v in kwargs.items()]


    def _rm_mounts(self,image,tag=None):
        data_dir = self.DOCKER_TMPFS.joinpath('data') if self.DOCKER_TMPFS else pathlib.Path(tempfile.mkdtemp())
        input_file = self.DOCKER_TMPFS.joinpath('input_file') if self.DOCKER_TMPFS else pathlib.Path(tempfile.mkstemp()[1])
        output_file = self.DOCKER_TMPFS.joinpath('output_file') if self.DOCKER_TMPFS else pathlib.Path(tempfile.mkstemp()[1])
        if tag is None: tag = image.tags[0]

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

# -----------------------------------------------------------------------------------------
# unified exec,file and dir plugin
class Plugin:
    def __init__(self, name, text=None, path=None, bind=None, mode='ro', exec=False, skip=False, tmpfs=None, daemonize=False, **kwargs):
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
        self.daemonize = daemonize

        self.exe_path = pathlib.Path(tempfile.mkstemp()[1]) if exec else None
        self.exe_volume = {'bind': f"/entropy/bin/{self.name}", 'mode': 'ro'} if exec else None
        # ignored if self.path.is_dir()
        self.tmp_path = pathlib.Path(tempfile.mkstemp()[1]) if path or text else None
        self.volume = {'bind': self.bind, 'mode': self.mode} if path or text else None


    def write(self, txt, **vars):
        if txt is None: return self
        if self.tmp_path is None: return self
        # extract mandatory shebang
        executable = txt.split('\n')[0].split(' ').pop() if self.exec else None
        if not executable:
            try:
                self.tmp_path.write_text(txt.format(**vars)+'\n')
            except KeyError:
                #a sh file
                self.tmp_path.write_text(txt+'\n')

        else:
            self.docker_env = [f"{var}={value}" for var, value in vars.items()]
            self.docker_exe = self.exe_volume.get('bind')
            # use f-string subsitution if not bash file
            self.tmp_path.write_text(txt.format(**vars)+'\n' if executable != 'sh' else txt+'\n')
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



