
# License: http://www.gnu.org/licenses/gpl-2.0.txt GNU General Public License v2
import subprocess
import signal
import sys
import fnmatch
import os
import pathlib
import tempfile

#Docker plugins
class Plugin:
    @property
    def docker_env(self):
        return []
    def write(self,txt,**env):
        raise NotImplementedError
    def chmod(self,mode):
        self.path.chmod(mode)
        return self

class EnvPlugin(Plugin):
    def __init__(self,env_var,value):
        self.env_var = env_var
        self.value = value
        self.path = None
    @property
    def docker_env(self):
        return  [f"{self.env_var}={self.value}"]
    def chmod(self,mode):
        raise NotImplementedError

class DirPlugin(Plugin):
    def __init__(self, path, bind=None, mode='ro'):
        self.path = pathlib.Path(path)
        self.volume = {'bind': bind if bind is not None else path, 'mode':mode}

class BashPlugin(Plugin):
    def __init__(self,name,mode='ro'):
        self.path = pathlib.Path(tempfile.mkstemp()[1])
        self.volume = {'bind':f"/entropy/plugins/{name}.sh",'mode':mode}
        self.env = {}
    def write(self,txt,**env):
        self.path.write_text(txt)
        self.env = {**self.env,**env}
        return self
    @property
    def docker_env(self):
        return [f"{env_var}={value}" for env_var,value in self.env.items()]
    @property
    def DOCKER_SCRIPT(self):
        return self.volume.get('bind')

class FilePlugin(Plugin):
    def __init__(self,bind,mode='ro'):
        self.path = pathlib.Path(tempfile.mkstemp()[1])
        self.volume = {'bind':bind,'mode':mode}
        self.env = {}
    def write(self,txt,**fvars):
        self.path.write_text(txt.format(**fvars))
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


