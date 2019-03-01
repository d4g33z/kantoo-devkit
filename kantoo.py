
# License: http://www.gnu.org/licenses/gpl-2.0.txt GNU General Public License v2
import subprocess
import signal
import sys
import fnmatch
import os
import pathlib
import tempfile
import hjson
from functools import reduce

class Config:
    def __init__(self,script_pwd,config_rel_path):
        self.SCRIPT_PWD = str(pathlib.Path(script_pwd).absolute())
        self.config = hjson.load(open(os.path.join(self.SCRIPT_PWD,config_rel_path),'r'))
        #all-caps root level keys become attributes
        [ setattr(self,y,self.config.get(y)) for y in filter(lambda x:x == x.upper(),self.config.keys()) ]
        self.file_plugins = self._bash_or_file_plugins('fileplugins')
        self.bash_plugins = self._bash_or_file_plugins('bashplugins')
        self.env_plugins = [EnvPlugin(var,value) for var,value in self.config.get('envplugins',{}).items()]
        self.dir_plugins = [DirPlugin(**value) for value in self.config.get('dirplugins',{}).values()]
        self.all_plugins = self.file_plugins + self.dir_plugins + self.bash_plugins + self.env_plugins

        # DOCKER_OPTS is define in the hjson config file
        self.DOCKER_OPTS.update({'volumes':{x.path if x.path.is_absolute() else os.path.join(self.SCRIPT_PWD,x.path):x.volume for x in self.all_plugins if x.path is not None}})
        # self.DOCKER_OPTS.update({'environment':list(reduce(lambda x,y:x+y,[z.docker_env for z in self.all_plugins],[]))})
        self.DOCKER_OPTS.update({'environment':list(reduce(lambda x,y:x+y,[z.docker_env for z in self.env_plugins],[]))})
        self.DOCKER_OPTS.update({'working_dir':self.SCRIPT_PWD})

        self.DOCKER_BUILDARGS = {
            'ARCH':self.ARCH,
            'SUBARCH':self.SUBARCH,}

    def _bash_or_file_plugins(self,type):
        fps = self.config.get(type)
        if fps is None: return []
        return list(map(lambda x,y,z:x.write(y,**z),
            [FilePlugin(**fps.get(x)) if type == 'fileplugins' else BashPlugin(x,**fps.get(x)).chmod(0o744) for x in fps.keys()],
            [x.get('text',open(x.get('path','/dev/null'),'r').read()) for x in fps.values()],
            [{y.strip():getattr(self,y.strip(),0) for y in x.get('env','DUMMY').split(',') } for x in fps.values()]))

    @property
    def DOCKER_REPO(self):
        return f"{self.OS}/{self.ARCH}/{self.SUBARCH}"
    @property
    def DOCKER_IMAGE(self):
        return f"{self.DOCKER_REPO}:{self.DOCKER_TAG}"

#Docker plugins
class Plugin:
    @property
    def docker_env(self):
        return []
    def write(self,txt,**env):
        raise NotImplementedError

class EnvPlugin(Plugin):
    def __init__(self,var,value):
        self.var = var
        self.value = value
        self.path = None # not needed if we don't try to update docker volumes with this obj
    @property
    def docker_env(self):
        return  [f"{self.var}={self.value}"]
    def __repr__(self):
        return f"{self.var} = {self.value}"

class DirPlugin(Plugin):
    def __init__(self, path, bind=None, mode='ro'):
        self.path = pathlib.Path(path)
        self.volume = {'bind': bind if bind is not None else path, 'mode':mode}
    def __repr__(self):
        return f"{self.path} : {self.volume.get('bind')}"

class BashPlugin(Plugin):
    def __init__(self, name, mode='ro', text=None, path=None, **kwargs):
        #dummy init args needed in Config contructor
        self.path = pathlib.Path(tempfile.mkstemp()[1])
        self.volume = {'bind':f"/entropy/plugins/{name}.sh",'mode':mode}
        self.name = name
        self.env = kwargs

    def write(self,txt,**env):
        self.path.write_text(txt)
        self.env = {**self.env,**env}
        return self
    def chmod(self,mode):
        self.path.chmod(mode)
        return self
    @property
    def docker_env(self):
        return [f"{var}={value}" for var,value in self.env.items()]
    @property
    def DOCKER_SCRIPT(self):
        return self.volume.get('bind')
    def __repr__(self):
        return f"{self.volume.get('bind')}"

class FilePlugin(Plugin):
    def __init__(self, bind, mode='ro', text=None, path=None, env=None):
        self.path = pathlib.Path(tempfile.mkstemp()[1])
        self.volume = {'bind':bind,'mode':mode}
    def write(self,txt,**fvars):
        self.path.write_text(txt.format(**fvars))
        return self
    def chmod(self,mode):
        self.path.chmod(mode)
        return self
    def __repr__(self):
        return f"{self.volume.get('bind')}"



