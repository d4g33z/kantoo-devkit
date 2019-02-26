
# License: http://www.gnu.org/licenses/gpl-2.0.txt GNU General Public License v2
import subprocess
import signal
import sys
import fnmatch
import os
import pathlib
import tempfile
import hjson


class Config:
    def __init__(self,path):
        self.config = hjson.load(open(path,'r'))
        #all-caps root level keys become attributes
        [ setattr(self,y,self.config.get(y)) for y in filter(lambda x:x == x.upper(),self.config.keys()) ]
        self.file_plugins = self._bash_or_file_plugins('fileplugins')
        self.bash_plugins = self._bash_or_file_plugins('bashplugins')
        self.env_plugins = [EnvPlugin(var,value) for var,value in self.config.get('envplugins').items()]
        self.dir_plugins = [DirPlugin(**value) for value in self.config.get('dirplugins').values()]

    def _bash_or_file_plugins(self,type):
        fps = self.config.get(type)
        return list(map(lambda x,y,z:x.write(y,**z),
            [FilePlugin(**fps.get(x)) if type == 'fileplugins' else BashPlugin(x,**fps.get(x)) for x in fps.keys()],
            [x.get('text',open(x.get('path','/dev/null'),'r').read()) for x in fps.values()],
            [{y:getattr(self,y,{}) for y in x.get('env','').split(',') } for x in fps.values()]))

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

class DirPlugin(Plugin):
    def __init__(self, path, bind=None, mode='ro'):
        self.path = pathlib.Path(path)
        self.volume = {'bind': bind if bind is not None else path, 'mode':mode}

class BashPlugin(Plugin):
    def __init__(self,name,mode='ro',text=None,path=None,env=None):
        self.tmp = pathlib.Path(tempfile.mkstemp()[1])
        self.volume = {'bind':f"/entropy/plugins/{name}.sh",'mode':mode}
        self.env={}
    def write(self,txt,**env):
        self.tmp.write_text(txt)
        self.env = {**self.env,**env}
        return self
    def chmod(self,mode):
        self.tmp.chmod(mode)
        return self
    @property
    def docker_env(self):
        return [f"{env_var}={value}" for env_var,value in self.env.items()]
    @property
    def DOCKER_SCRIPT(self):
        return self.volume.get('bind')

class FilePlugin(Plugin):
    def __init__(self,bind,mode='ro',text=None,path=None,env=None):
        self.tmp = pathlib.Path(tempfile.mkstemp()[1])
        self.volume = {'bind':bind,'mode':mode}
    def write(self,txt,**fvars):
        self.tmp.write_text(txt.format(**fvars))
        return self
    def chmod(self,mode):
        self.tmp.chmod(mode)
        return self

#os utilities
def make_built_pkgs(dir_to_walk):
    #built_pkgs=\$(find /root/packages -name "*.tbz2" | xargs)
    built_pks = ""

    for dirpath, dirnames, filenames in os.walk(dir_to_walk):
        for filename in filenames:
            if fnmatch.fnmatch(filename, "*.tbz2"): # Match search string
                built_pks += (os.path.join(dirpath, filename) + " ")
    return built_pks

#os utilities borrowed from kano
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

def run_and_watch(cmd):
    process = subprocess.Popen(cmd, shell=True,
                               stdout=sys.stdout, stderr=subprocess.PIPE,
                               preexec_fn=restore_signals)

    stderr = process.communicate()
    returncode = process.returncode
    return stderr, returncode


def run_print_output_error(cmd):
    o, e, rc = run_cmd(cmd)
    if o or e:
        print('\ncommand: {}'.format(cmd))
    if o:
        print('output:\n{}'.format(o.strip()))
    if e:
        print('\nerror:\n{}'.format(e.strip()))
    return o, e, rc


