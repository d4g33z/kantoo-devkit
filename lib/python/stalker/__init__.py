import hjson
from collections import OrderedDict
from copy import copy

from dockerdriver import dd

class Stalker:
    def __init__(self,cwd,config_path):
        self.cwd = cwd
        self.name = config_path.parts[-1].split('.')[0]
        self.config = hjson.load(open(cwd.joinpath(config_path), 'r'))

    def _visit(self,process_node,node,keychain=None):
        keychain = [] if keychain is None else keychain
        if isinstance(node,OrderedDict):
            if keychain:
                process_node(node,copy(keychain))
            for chikey in node.keys():
                keychain.append(chikey)
                self._visit(process_node,node.get(chikey),copy(keychain))
                keychain.pop()

    def run(self):
        def _run(node,keychain):
            if 'stalks' in keychain[:-1]:
                config = hjson.load(open(self.cwd.joinpath(f"stalks/{keychain[-1]}/{keychain[-1]}.hjson"), 'r'))
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


