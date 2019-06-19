import os
import hjson
from collections import OrderedDict
from copy import copy
import tempfile
import eliot
import pathlib
from dockerdriver import dd, DockerDriver


def sd(cwd, config,watch_stdout):
    # eliot.to_file(open(f"{cwd}/logs/eliot-{datetime.now().strftime('%y-%m-%d-%H:%M:%S')}.txt",'wb'))

    with eliot.start_action(action_type='Stalker',cwd=str(cwd),config=str(config)):
        config = Stalker(cwd,pathlib.Path(config))

    with eliot.start_action(action_type='run'):
        config.run(watch_stdout)

    return config

class Stalker:

    def __init__(self,cwd,config):
        self.cwd = cwd
        self.config = hjson.load(open(cwd.joinpath(config), 'r'))

    def _visit(self,process_node,node,keychain=None):
        keychain = [] if keychain is None else keychain
        if isinstance(node,OrderedDict):
            if keychain:
                process_node(node,copy(keychain))
            for chikey in node.keys():
                keychain.append(chikey)
                self._visit(process_node,node.get(chikey),copy(keychain))
                keychain.pop()

    def _get_dockerdriver(self, stalk_name, **overrides):
        config_path = pathlib.Path(f"stalks/{stalk_name}/{stalk_name}.hjson")
        config = hjson.load(open(self.cwd.joinpath(config_path), 'r'))


        config.update(self.config.get('architecture'))
        config.update(self.config.get('paths'))
        config.update({**overrides,**self._get_overrides(stalk_name)})

        config_path = pathlib.Path(tempfile.mkdtemp()).joinpath(f"{stalk_name}.hjson")
        hjson.dump(config,config_path.open('w',encoding='utf-8'))

        return DockerDriver(self.cwd,config_path)

    def _get_overrides(self,stalk_name):
        _overrides = {}
        def _f(node,keychain):
            if 'stalks' not in keychain[:-1] or keychain[-1] != stalk_name: return
            _overrides.update({k:v  for k,v in node.items() if k.upper() == k})
        self._visit(_f,self.config)
        return _overrides

    def _fetch_stage3(self,dist,arch,subarch,stage3_archive):
        os.chdir(self.cwd)
        os.environ.update(DIST=dist,ARCH=arch,SUBARCH=subarch,STAGE3_ARCHIVE=stage3_archive)
        if os.system('. lib/bash/kantoo.sh && stage3_fetch') == 1:
            raise('failed to execute internal shell function')
        map(lambda x:os.environ.pop(x), ('DIST', 'ARCH', 'SUBARCH', 'STAGE3_ARCHIVE'))

    def cleanup(self,stalk_name):
        def _cleanup(node,keychain):
            if 'stalks' not in keychain[:-1] or keychain[-1] != stalk_name: return
            dd = self._get_dockerdriver(keychain[-1],**{k:v  for k,v in node.items() if k.upper() == k})
            dd.container_cleanup()
            dd.image_cleanup()
        self._visit(_cleanup,self.config)

    def run(self,watch_stdout):
        def _run(node,keychain):
            if 'stalks' not in keychain[:-1]: return

            #eliot.Message.log(message_type=f"{keychain[-1]}",**{k:v  for k,v in node.items() if k.upper() == k})
            eliot.Message.log(message_type=f"{keychain[-1]}",keychain=keychain)
            dd = self._get_dockerdriver(keychain[-1],**{k:v  for k,v in node.items() if k.upper() == k})

            pretend = node.get('pretend',False)
            skip_until = node.get('skip_until','')

            if pretend:
                [setattr(p, 'skip', True) for p in filter(lambda x: x.exec, dd.plugins)]

            if skip_until:
                for plugin in dd.plugins:
                    if plugin.name == skip_until: break
                    plugin.skip = True

            if not pretend:
                with eliot.start_action(action_type='initialize'):
                    dd.initialize()

            #start the sequence of operations
            with eliot.start_action(action_type='start'):
                dd.start(watch_stdout)

        self._visit(_run,self.config)

    def show_config(self):
        def f(node,keychain):
            k_spacer = len(keychain) + 1
            k_max = max(map(len,node.keys()),default=0)
            print(' '*len(keychain) + f"{keychain[-1]}")
            for k,v in node.items():
                if k.upper() == k:
                    print("{0}{1}{2}{3}".format(' '*k_spacer,str(k) + ' ',' '*(k_max- len(k)),': ' + str(v)))
        self._visit(f,self.config)


