# Kantoo Devkit #

Kantoo **is** Funtoo, with a twist.

This is a collection of tools modeled on the [Sabayon Devkit](https://github.com/Sabayon/devkit).

The idea is to facilitate the creation of 'Kantoo stage4s:' Funtoo stage3s that have been augmented to allow
installation of binary packages via the Entropy package manager.

Docker containers are used to create images of each choosen subarch, profile and mixins, with a predefined list of 
packages to build with portage and package with entropy.

The `dockerdriver.py` is used to create a container(s) and Funtoo stage3 image if required, attaching volumes and environment variables as needed, and 
execute a series of bash or python scripts to modify it. The steps can be atomized by commit intermediate containers 
to images.

## How To Use it ##

Everything can be done by writing an [hjson](hjson.org) configuration file, and the necessary bash and python scripts it
references and runs as the `command` argument to the `container.exec_run` method in the 
[python docker sdk](https://docker-py.readthedocs.io/en/stable/index.html). The driver sets up the container, and runs 
the configured scripts in the container.

Use `virtualenv` to isolate everything nicely. You must have a working docker install on your development machine.

```commandline
# cd kantoo-devkit
# virtualenv -p /usr/bin/python3.6 env3.6
# source env3.6/bin/activate
# pip install -r requirements.txt
# vim configs/hello_world.hjson
# ./dockerdriver.py --config configs/hello_world.hjson --commit false
Found docker image funtoo/x86-64bit/amd64-k10:stage3
>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
>>>BashPlugin: /entropy/plugins/hello_world.sh
>>>FilePlugins: [/tmp/hello_file]
>>>DirPlugins: [/var/git : /var/git]
>>>EnvPlugins: [EDITOR = cat, LC_ALL = en_US.UTF-8]
# cat last_logs.txt
hello globally
hello locally
hello via override
# vim configs/hello_goodbye_world.hjson
# ./dockerdriver.py --config configs/hello_goodbye_world.hjson --commit true
Found docker image funtoo/x86-64bit/amd64-k10:stage3
>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
>>>BashPlugin: /entropy/plugins/hello_world.sh
>>>FilePlugins: [/tmp/hello_file, /tmp/goodbye_file]
>>>DirPlugins: [/var/git : /var/git]
>>>EnvPlugins: [EDITOR = cat, LC_ALL = en_US.UTF-8]
>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
>>>BashPlugin: /entropy/plugins/goodbye_world.sh
>>>FilePlugins: [/tmp/hello_file, /tmp/goodbye_file]
>>>DirPlugins: [/var/git : /var/git]
>>>EnvPlugins: [EDITOR = cat, LC_ALL = en_US.UTF-8]
# cat last_logs.txt
goodbye world
goodbye, file world!!!
```

Hello, world!

