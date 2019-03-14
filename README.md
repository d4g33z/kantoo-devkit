# Kantoo Devkit #

Kantoo **is** Funtoo, with a twist.

This is a collection of tools modeled on the [Sabayon Devkit](https://github.com/Sabayon/devkit).

The idea is to facilitate the creation of 'Kantoo stage4s:' Funtoo stage3s that have been augmented to allow
installation of binary packages via the Entropy package manager.

Docker containers are used to create images of a choosen subarch, profile and mixins, with a predefined list of 
packages to build with portage and distribute with entropy.

The `dockerdriver` executable is used to create a container(s) (creating a Funtoo stage3 image if required), attaching 
volumes and environment variables as needed, and execute a series of bash or python scripts to modify it. The steps are 
atomized by committing intermediate containers to images.

You must have a working docker install on your development machine. Add yourself to the `docker` group to work without 
needing root privileges.  

## Why Not Just Use Dockerfiles? ##

I'm not sure exactly. But I feel I needed to structure the modification process of an image more explicitly, and modularize
the common steps, especially with respect to the initial use case: building lots of binary packages and managing repos of them.

## Use Virtualenv (Please) ##

Use `virtualenv` to isolate everything nicely and in a disposable way. This preferable for most small projects, as 
opposed to installing and maintaining system wide packages.

```commandline
# cd kantoo-devkit
# virtualenv -p /usr/bin/python3.6 env3.6
# source env3.6/bin/activate
(env3.6) # pip install -r requirements.txt
```

## Quick Start to Interact with a Funtoo Stage3 ##

Use the bash shell or `ipython` to work with images interactively in a simple way.using [`hjson`](hjson.org) files that are turned 
into a `kantoo.config` object which the `dockerdriver` script uses to build the images and create containers.


```commandline
(env3.6) # configs/stage3.hjson << EOF
OS: funtoo
ARCH: x86-64bit
SUBARCH: amd64-k10
ENTROPY_ARCH: amd64

DOCKER_TAG: stage3

DOCKER_OPTS:
{
    tty:true,
    init:true,
    remove:true,
    entrypoint:"/bin/bash",
    detach:true,
}
EOF
(env3.6) # ./dockerdriver --config configs/stage3.hjson --interactive
c02bccc99f27 / # cat /etc/os-release 
ID="funtoo"
NAME="Funtoo GNU/Linux"
PRETTY_NAME="Linux"
VERSION="2019-02-05"
VERSION_ID="amd64-k10-2019-02-05"
ANSI_COLOR="0;34"
HOME_URL="www.funtoo.org"
BUG_REPORT_URL="bugs.funtoo.org"
c02bccc99f27 / # exit
exit
(env3.6) # cd lib/python
(env3.6) # ipython
Python 3.6.6 (default, Dec  8 2018, 03:41:35) 
Type 'copyright', 'credits' or 'license' for more information
IPython 7.3.0 -- An enhanced Interactive Python. Type '?' for help.

In [1]: from kantoo import Config
In [2]:  c = Config('../..','configs/stage3.hjson')
In [3]: c.interact() 
24d9f7f71407 / # cat etc/os-release
ID="funtoo"
NAME="Funtoo GNU/Linux"
PRETTY_NAME="Linux"
VERSION="2019-02-05"
VERSION_ID="amd64-k10-2019-02-05"
ANSI_COLOR="0;34"
HOME_URL="www.funtoo.org"
BUG_REPORT_URL="bugs.funtoo.org"
24d9f7f71407 / # exit
exit
```

## How To Use it ##

Everything can be done by writing an [hjson](hjson.org) configuration file, and the necessary bash and python scripts it
references and runs as the `command` argument to the `container.exec_run` method in the 
[python docker sdk](https://docker-py.readthedocs.io/en/stable/index.html). The `dockerdriver` sets up the container and runs 
the configured scripts in the container in sequence.

### Hello, world! ###

```commandline
(env3.6) # vim configs/hello_world.hjson
(env3.6) # ./dockerdriver --config configs/hello_world.hjson
Found docker image funtoo/x86-64bit/amd64-k10:stage3.
>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
Creating container of stage3 to run hello_world on.
vigorous_mclean : sha256:14d879ecbd0828598add5ef6458c22ebb3d0d7ee54a2f265c65bcc1aa81803ad committed
(env3.6) # cat logs/last_logs.txt
hello globally
hello locally from bash
hello locally
hello via override
(env3.6) # vim configs/hello_goodbye_world.hjson
(env3.6) # ./dockerdriver --config configs/hello_goodbye_world.hjson
Found docker image funtoo/x86-64bit/amd64-k10:stage3.
>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
Creating container of stage3 to run hello_world on.
festive_mendel : sha256:8a674e1cc5344275a48e8eb24f95801b2b9c3b3c61b605f32ca7e4c53965c980 committed
>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
Creating container of hello_world to run goodbye_world on.
stoic_engelbart : sha256:71116737a08920fe1045e450b29373257bf54cefbb22b300094eae58a6f1c63d committed
(env3.6) # cat logs/last_logs.txt
goodbye world
goodbye, file world!!!
```
