
# License: http://www.gnu.org/licenses/gpl-2.0.txt GNU General Public License v2
import os
import pathlib
import tempfile
import hjson
from functools import reduce
from collections import OrderedDict
#-----------------------------------------------------------------------------------------
#unified exec,file and dir plugin
class Plugin:
    def __init__(self,name,text=None,path=None,bind=None,mode='ro',exec=False,**kwargs):
        assert not (text and path)
        assert not (bind and exec)
        self.path = path if path else '/dev/null' #it has a text element
        self.bind = bind if bind else f"/entropy/plugins/{name}"
        self.text = text
        self.name = name
        self.mode = mode
        self.exec = exec

        self.exe_path = pathlib.Path(tempfile.mkstemp()[1]) if exec else None
        self.exe_volume = {'bind':f"/entropy/bin/{self.name}",'mode':'ro'} if exec else None
        self.tmp_path = pathlib.Path(tempfile.mkstemp()[1]) if not os.path.isdir(self.path) else None
        self.volume = {'bind':self.bind,'mode':self.mode}

    def write(self,txt,**vars):
        if txt is None: return self
        #extract mandatory shebang
        executable = txt.split('\n')[0].split(' ').pop() if self.exec else None
        if not executable:
            #use f-string subsitution
            self.exec_path.write_text(txt.format(**vars))
        else:
            self.docker_env = [f"{var}={value}" for var,value in vars.items()]
            self.path.write_text(txt)
            self.exec_path.write_text(
f"""#!/usr/bin/env sh
{executable} {self.volume.get('bind') }
""")
        return self


class PluginConfig:
    'A configuration object for docker containers'
    def __init__(self,script_pwd,config_rel_path):
        self.SCRIPT_PWD = str(pathlib.Path(script_pwd).absolute())
        self.config = hjson.load(open(os.path.join(self.SCRIPT_PWD,config_rel_path),'r'))

        #all-caps root level keys become attributes
        [ setattr(self,y,self.config.get(y)) for y in filter(lambda x:x == x.upper(),self.config.keys()) ]

        #a default value
        if not hasattr(self,'DOCKER_FILE'): setattr(self,'DOCKER_FILE','Dockerfile')


        self.plugins = self._plugin_factory(self.config.get('plugins'))

        self.env_plugins = [EnvPlugin(var, value) for var, value in self.config.get('envplugins', {}).items()]

        #bind the contents of DOT_DIR as hidden files and dirs in /root
        if hasattr(self,'DOT_DIR') and pathlib.Path(os.path.join(self.SCRIPT_PWD,self.DOT_DIR)).exists():
            self.plugins += self._dot_plugin_factory(self.DOT_DIR)

        # DOCKER_OPTS is created in the hjson config file
        self.DOCKER_OPTS.update(
                {'volumes':{
                    **{x.exe_path:x.exe_volume for x in self.plugins if x.exec},
                    **{os.path.join(self.SCRIPT_PWD,x.tmp_path if x.tmp_path else x.path):x.volume for x in self.plugins }},
                })

        self.DOCKER_OPTS.update({'environment':list(reduce(lambda x,y:x+y,[z.docker_env for z in self.env_plugins],[]))})
        self.DOCKER_OPTS.update({'working_dir':'/'})

        self.DOCKER_BUILDARGS = {
            'ARCH':self.ARCH,
            'SUBARCH':self.SUBARCH,}

    def _plugin_factory(self,plugin_block):

        return list(map(lambda x,y,z:x.write(y,**z),
                        #create the objs
                        [Plugin(k, **v) for k,v in plugin_block.items()],
                        #get the text from the hjson file or a file on disk
                        [x.get('text',open(os.path.join(self.SCRIPT_PWD,x.get('path','/dev/null')),'r').read()) if x.get('tmp_path') else None\
                                                                                        for x in plugin_block.values()],
                        #get the env or f-string vars using value on Config obj or those set in the block itself
                        [{i[0]:i[1] if i[1] != '' else getattr(self,i[0]) \
                                for i in filter(lambda y:y[0]==y[0].upper(),x.items())} for x in plugin_block.values()]))

    def _dot_plugin_factory(self,dot_path='lib/dot'):
        dot_path = os.path.join(self.SCRIPT_PWD,dot_path)
        _,dirs_to_bind,files_to_bind = [x for x in os.walk(dot_path)][0]
        dir_configs_objs = OrderedDict(**{dir_to_bind:OrderedDict(path=os.path.join(dot_path,dir_to_bind),bind=os.path.join('/root','.'+dir_to_bind),exec=False) for dir_to_bind in dirs_to_bind})
        file_configs_objs = OrderedDict(**{os.path.basename(file_to_bind):OrderedDict(path=os.path.join(dot_path,file_to_bind),bind=os.path.join('/root','.'+file_to_bind),exec=False) for file_to_bind in files_to_bind})
        return self._plugin_factory(dir_configs_objs) + self._plugin_factory(file_configs_objs)

    @property
    def DOCKER_REPO(self):
        return f"{self.OS}/{self.ARCH}/{self.SUBARCH}"
    @property
    def DOCKER_IMAGE(self):
        return f"{self.DOCKER_REPO}:{self.DOCKER_TAG}"

    def update(self,**kwargs):
        [setattr(self,k,v) for k,v in kwargs.items()]

    def interactive_run_cmd(self,tag):
        volumes = [f"-v {str(path)}:{info.get('bind')}:{info.get('mode')}" for path,info in self.DOCKER_OPTS.get('volumes').items()]
        envs = [f"-e {env}" for env in self.DOCKER_OPTS.get('environment')]
        #return f"docker run --rm {' '.join(volumes)} {' '.join(envs)} -ti {self.DOCKER_REPO}:{self.DOCKER_TAG}"
        return f"docker run --rm {' '.join(volumes)} {' '.join(envs)} -ti {self.DOCKER_REPO}:{tag}"

    def interact(self,tag='stage3'):
        "drop to an interactive shell of a container of self.DOCKER_IMAGE"
        try:
            ip = get_ipython()
            ip.system(self.interactive_run_cmd(tag))
        except NameError:
            os.system(self.interactive_run_cmd(tag))
        except:
            print('cannot interact')
        return

    def images(self,client):
        return list(filter(lambda x: x in client.images.list(f"{self.DOCKER_REPO}"),client.images.list()))

    def image_cleanup(self,client):
        #remove danglers
        [client.images.remove(image.id) for image in client.images.list(filters={'dangling':True})]

        #TODO: remove all running containers first
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
            [_image_cleanup(im) for im in list(map(lambda a:a.pop(), (filter(lambda y:y.pop() in map(lambda z:z.name, self.exec_plugins), [[x, x.tags.pop().split(':').pop()] for x in self.images(client)]))))]
        except RemovalFinished:
            return

#-----------------------------------------------------------------------------------------------------------------------
#old Config style of seperate file,exec,dir and env blocks
class Config:
    'A configuration object for docker containers'
    def __init__(self,script_pwd,config_rel_path):
        self.SCRIPT_PWD = str(pathlib.Path(script_pwd).absolute())
        self.config = hjson.load(open(os.path.join(self.SCRIPT_PWD,config_rel_path),'r'))

        #all-caps root level keys become attributes
        [ setattr(self,y,self.config.get(y)) for y in filter(lambda x:x == x.upper(),self.config.keys()) ]

        #a default value
        if not hasattr(self,'DOCKER_FILE'): setattr(self,'DOCKER_FILE','Dockerfile')

        self.file_plugins = self._exec_or_file_plugins('fileplugins')
        self.exec_plugins = self._exec_or_file_plugins('execplugins')
        self.env_plugins = [EnvPlugin(var, value) for var, value in self.config.get('envplugins', {}).items()]
        self.dir_plugins = [DirPlugin(**value) for value in self.config.get('dirplugins', {}).values()]

        #bind the contents of DOT_DIR as hidden files and dirs in /root
        if hasattr(self,'DOT_DIR') and pathlib.Path(os.path.join(self.SCRIPT_PWD,self.DOT_DIR)).exists():
            dot_dir_configs,dot_file_configs = self._dot_plugins(self.DOT_DIR)
            [self.dir_plugins.append(DirPlugin(**dirplugin_values)) for dirplugin_values in dot_dir_configs.values()]
            [self.file_plugins.append(FilePlugin(**fileplugin_values).write(open(os.path.join(self.SCRIPT_PWD, fileplugin_values.get('path'))).read(), '')) for fileplugin_values in dot_file_configs.values()]

        self.all_plugins = self.file_plugins + self.dir_plugins + self.exec_plugins + self.env_plugins

        # DOCKER_OPTS is created in the hjson config file
        self.DOCKER_OPTS.update(
                {'volumes':{
                    **{x.exec_path:x.exec_volume for x in self.exec_plugins},
                    **{os.path.join(self.SCRIPT_PWD,x.path):x.volume for x in self.all_plugins if x.path is not None}},
                })

        self.DOCKER_OPTS.update({'environment':list(reduce(lambda x,y:x+y,[z.docker_env for z in self.env_plugins],[]))})
        self.DOCKER_OPTS.update({'working_dir':'/'})

        self.DOCKER_BUILDARGS = {
            'ARCH':self.ARCH,
            'SUBARCH':self.SUBARCH,}

    def _dot_plugins(self,dot_path='lib/dot'):
        dot_path = os.path.join(self.SCRIPT_PWD,dot_path)
        _,dirs_to_bind,files_to_bind = [x for x in os.walk(dot_path)][0]
        dir_configs_objs = OrderedDict(**{dir_to_bind:OrderedDict(path=os.path.join(dot_path,dir_to_bind),bind=os.path.join('/root','.'+dir_to_bind)) for dir_to_bind in dirs_to_bind})
        file_configs_objs = OrderedDict(**{os.path.basename(file_to_bind):OrderedDict(path=os.path.join(dot_path,file_to_bind),bind=os.path.join('/root','.'+file_to_bind)) for file_to_bind in files_to_bind})
        return dir_configs_objs,file_configs_objs

    def _exec_or_file_plugins(self, type):
        pluginblock = self.config.get(type)
        if pluginblock is None: return []

        return list(map(lambda x,y,z,a:x.write(y,a,**z),
                        #create the objs
                        [FilePlugin(**pluginblock.get(x)) if type == 'fileplugins' else ExecPlugin(x, **pluginblock.get(x)).chmod(0o744) for x in pluginblock.keys()],
                        #get the text from the hjson file or a file on disk
                        [x.get('text',open(os.path.join(self.SCRIPT_PWD,x.get('path','/dev/null')),'r').read()) for x in pluginblock.values()],
                        #get the env or f-string vars using value on Config obj or those set in the block itself
                        [{i[0]:i[1] if i[1] != '' else getattr(self,i[0]) for i in filter(lambda y:y[0]==y[0].upper(),x.items())} for x in pluginblock.values()],
                        #extract the executable of the script from the shebang notation
                        [os.path.basename(x.get('path')).split('.').pop() if x.get('path') is not None else x.get('text').split('\n')[0].split(' ').pop() for x in pluginblock.values()]),)

    @property
    def DOCKER_REPO(self):
        return f"{self.OS}/{self.ARCH}/{self.SUBARCH}"
    @property
    def DOCKER_IMAGE(self):
        return f"{self.DOCKER_REPO}:{self.DOCKER_TAG}"

    def update(self,**kwargs):
        [setattr(self,k,v) for k,v in kwargs.items()]

    def interactive_run_cmd(self,tag):
        volumes = [f"-v {str(path)}:{info.get('bind')}:{info.get('mode')}" for path,info in self.DOCKER_OPTS.get('volumes').items()]
        envs = [f"-e {env}" for env in self.DOCKER_OPTS.get('environment')]
        #return f"docker run --rm {' '.join(volumes)} {' '.join(envs)} -ti {self.DOCKER_REPO}:{self.DOCKER_TAG}"
        return f"docker run --rm {' '.join(volumes)} {' '.join(envs)} -ti {self.DOCKER_REPO}:{tag}"

    def interact(self,tag='stage3'):
        "drop to an interactive shell of a container of self.DOCKER_IMAGE"
        try:
            ip = get_ipython()
            ip.system(self.interactive_run_cmd(tag))
        except NameError:
            os.system(self.interactive_run_cmd(tag))
        except:
            print('cannot interact')
        return

    def images(self,client):
        return list(filter(lambda x: x in client.images.list(f"{self.DOCKER_REPO}"),client.images.list()))

    def image_cleanup(self,client):
        #remove danglers
        [client.images.remove(image.id) for image in client.images.list(filters={'dangling':True})]

        #TODO: remove all running containers first
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
            [_image_cleanup(im) for im in list(map(lambda a:a.pop(), (filter(lambda y:y.pop() in map(lambda z:z.name, self.exec_plugins), [[x, x.tags.pop().split(':').pop()] for x in self.images(client)]))))]
        except RemovalFinished:
            return

#Docker plugins
class PluginBase:
    @property
    def docker_env(self):
        return []
    def write(self,txt,**env):
        raise NotImplementedError

class EnvPlugin(PluginBase):
    def __init__(self,var,value):
        self.var = var
        self.value = value
        self.path = None # not needed if we don't try to update docker volumes with this obj
    @property
    def docker_env(self):
        return  [f"{self.var}={self.value}"]
    def __repr__(self):
        return f"{self.var} = {self.value}"

class DirPlugin(PluginBase):
    def __init__(self, path, bind=None, mode='ro'):
        self.path = pathlib.Path(path)
        self.volume = {'bind': bind if bind is not None else path, 'mode':mode}
    def __repr__(self):
        return f"{self.path} : {self.volume.get('bind')}"

#force isolation of scripts on the image
class ExecPlugin(PluginBase):
    #allowing skipping of steps in hjson file or programmatically
    def __init__(self, name, mode='ro', text=None, path=None, skip=False,**kwargs):
        #the actual code
        self.path = pathlib.Path(tempfile.mkstemp()[1])
        #the executable wrapper to call the code
        self.exec_path = pathlib.Path(tempfile.mkstemp()[1])
        self.volume = {'bind':f"/entropy/plugins/{name}",'mode':mode}
        self.exec_volume = {'bind':f"/entropy/bin/{name}",'mode':'ro'}
        self.name = name
        self.skip = skip

    def write(self, txt, executable, **env):
        self.path.write_text(txt)
        self.env = env
        self.exec_path.write_text(
f"""#!/usr/bin/env sh
{executable} {self.volume.get('bind') }
"""
        )
        return self
    def chmod(self,mode):
        self.exec_path.chmod(mode)
        return self
    @property
    def docker_env(self):
        return [f"{var}={value}" for var,value in self.env.items()]
    @property
    def DOCKER_SCRIPT(self):
        return self.exec_volume.get('bind')
    def __repr__(self):
        return f"{self.volume.get('bind')}"

class FilePlugin(PluginBase):
    def __init__(self, bind, mode='ro', text=None, path=None, **kwargs):
        self.path = pathlib.Path(tempfile.mkstemp()[1])
        self.volume = {'bind':bind,'mode':mode}
    def write(self,txt,dummy,**fvars):
        self.path.write_text(txt.format(**fvars))
        return self
    def chmod(self,mode):
        self.path.chmod(mode)
        return self
    def __repr__(self):
        return f"{self.volume.get('bind')}"
