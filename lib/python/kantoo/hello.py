#!/usr/bin/env python3
import os
def hello_python_from_env():
    HELLO_MSG =  os.environ.get('HELLO_MSG')
    os.sys.stdout.write(HELLO_MSG+'\n')

def hello_python_from_arg(HELLO_MSG):
    os.sys.stdout.write(HELLO_MSG+'\n')
