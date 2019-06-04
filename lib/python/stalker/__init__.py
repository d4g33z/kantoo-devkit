import hjson
from collections import OrderedDict
from copy import copy
import tempfile
import eliot
import pathlib
from dockerdriver import dd, DockerDriver


def sd(cwd, config):
    # eliot.to_file(open(f"{cwd}/logs/eliot-{datetime.now().strftime('%y-%m-%d-%H:%M:%S')}.txt",'wb'))

    with eliot.start_action(action_type='Stalker',cwd=str(cwd),config=str(config)):
        config = Stalker(cwd,pathlib.Path(config))

    with eliot.start_action(action_type='run'):
        config.run()

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
        config.update(overrides)

        config_path = pathlib.Path(tempfile.mkdtemp()).joinpath(f"{stalk_name}.hjson")
        hjson.dump(config,config_path.open('w',encoding='utf-8'))

        return DockerDriver(self.cwd,config_path)

    def run(self):
        def _run(node,keychain):
            if 'stalks' not in keychain[:-1]: return

            #eliot.Message.log(message_type=f"{keychain[-1]}",**{k:v  for k,v in node.items() if k.upper() == k})
            eliot.Message.log(message_type=f"{keychain[-1]}",keychain=keychain)
            dd = self._get_dockerdriver(keychain[-1],**{k:v  for k,v in node.items() if k.upper() == k})

            pretend = node.get('pretend',False)
            interactive = node.get('interactive',False)
            skip_until = node.get('skip_until','')

            if pretend:
                [setattr(p, 'skip', True) for p in filter(lambda x: x.exec, dd.plugins)]

            if skip_until:
                for plugin in dd.plugins:
                    if plugin.name == skip_until: break
                    plugin.skip = True

            # try to find initial image or create it
            if not pretend:
                with eliot.start_action(action_type='initialize'):
                    dd.initialize()

            if interactive:
                dd.interact('initial')

            #start the sequence of operations
            with eliot.start_action(action_type='start'):
                dd.start(interactive)

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


