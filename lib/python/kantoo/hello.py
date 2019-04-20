#!/usr/bin/env python3
import os
def hello_python():
    HELLO_MSG =  os.environ.get('HELLO_MSG')
    os.sys.stdout.write(HELLO_MSG+'\n')
