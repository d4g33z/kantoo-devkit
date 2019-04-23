# Kantoo Devkit 0.3 #

Kantoo **is** Funtoo, with a twist.

This is a collection of tools modeled on the [Sabayon Devkit](https://github.com/Sabayon/devkit).

The idea is to facilitate the creation of 'Kantoo stage4s:' Funtoo stage3s that have been augmented to allow installation of binary packages (comprising a small subset of the total Portage universe) via the Entropy package manager. The first target architecture is `arm-32bit/raspi3` in Funtoo terms or `armv7l` in Sabayon terms.

The `dockerdriver` executable is used to create a containers of of a choosen subarch, profile and mixins, attaching bind mounts (files and directorys on the host that become visible in the container at a choosen location) and environment variables, and executing a series of bash or python scripts to modify it and commit the result as a new image.

You must have a working docker install on your development machine. Add yourself to the `docker` group to work without needing root privileges.  

## Why Not Just Use Dockerfiles? ##

I'm not sure exactly. But I feel I needed to structure the modification process of an image more explicitly, and modularize the common steps, especially with respect to the initial use case: building lots of binary packages with particular USE sets and managing repos of them.

## Use Virtualenv (Please) ##

Use `virtualenv` to isolate everything nicely and in a disposable way. This preferable for most small projects, as opposed to installing and maintaining system wide packages.

```commandline
# cd kantoo-devkit
# virtualenv -p /usr/bin/python3.6 env3.6
# source env3.6/bin/activate
(env3.6) # pip install -r requirements.txt
```

### Hook In Your Python Portage API ###
This project uses `portage` with Python 3.6. see [Portage API](https://www.funtoo.org/Portage_API). It is not available as a package, and we don't want to all system wide packages in our virtual environment. So we just symlink to the required libraries.

```commandline
(env3.6) # ln -s /usr/lib64/python3.6/site-packages/portage lib/python/portage
(env3.6) # ln -s /usr/lib64/python3.6/site-packages/_emerge lib/python/_emerge

```
## Quick Start to Interact with a Funtoo Stage3 ##

Use `ipython` or the `dockerdriver` to work with images interactively in a simple way, using [`hjson`](hjson.org) files that are marshalled into a `kantoo.config` object.


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
    remove:false,
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

In [1]: from dockerdriver import * 
In [2]:  c = DockerDriver('../..','plugins/stage3/stage3.hjson')
In [3]: c.interact('initial') 
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

Everything can be done by writing an [hjson](hjson.org) configuration file, and the necessary bash and python scripts it references and runs as the `command` argument to the `container.exec_run` method in the [python docker sdk](https://docker-py.readthedocs.io/en/stable/index.html). The `dockerdriver` sets up the container and runs the configured scripts in the container in sequence.

### Hello, world! ###
See `plugins/hello_world/hello_world.hjson`. It demonstrates the many different ways to pass values from the `hjson` file to bash or python scripts on a container.

```commandline
(env3.6) # rm -f logs/*
(env3.6) # ./dockerdriver --config plugins/hello_world/hello_world.hjson
>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
Creating container of funtoo/x86-64bit/amd64-k10/hello_world:initial to run hello_world on.
affectionate_yalow : sha256:1c4373473983f02cc5db362c1396037ad650428f6d3b580c834a070e6f62a180 committed
>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
Creating container of funtoo/x86-64bit/amd64-k10/hello_world:hello_world to run hello_python_from_env on.
affectionate_ride : sha256:6aef0a015c624079eba1e73b118d4443116c54ba7b43ef9f6382de81fd077242 committed
>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
Creating container of funtoo/x86-64bit/amd64-k10/hello_world:hello_python_from_env to run hello_python_from_arg on.
kind_burnell : sha256:59e6921caf861fe317210e6f37f079f8b54931c71dcab76e75b5daef0646b366 committed
>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
Creating container of funtoo/x86-64bit/amd64-k10/hello_world:hello_python_from_arg to run hello_python_from_explicit_env on.
hungry_goldwasser : sha256:1995a8a7104703910bcc9c0a196fcbb51a79bb0f2f290d659eb5b8934f094bf7 committed
(env3.6) # cat logs/*
hello from a python plugin via arguments
hello from a python plugin via environment variables
hello from a python plugin via explicit arguments
hello globally
hello locally from bash
hello locally
hello via override
(env3.6) # docker images
funtoo/x86-64bit/amd64-k10/hello_world      hello_python_from_explicit_env   600fe0922b60        2 minutes ago       892MB
funtoo/x86-64bit/amd64-k10/hello_world      hello_python_from_arg            f3cecf52899e        2 minutes ago       892MB
funtoo/x86-64bit/amd64-k10/hello_world      hello_python_from_env            e25b675a79bd        2 minutes ago       892MB
funtoo/x86-64bit/amd64-k10/hello_world      hello_world                      09a594a56622        2 minutes ago       892MB
funtoo/x86-64bit/amd64-k10/hello_world      initial                          d0d31dc47745        2 weeks ago         892MB
funtoo/x86-64bit/amd64-k10/stage3           initial                          e79e25dfae8d        2 weeks ago         892MB
 


```

## How to Make a Stage4 with Entropy Repo##

```commandline
(env3.6) #  ./dockerdriver --config plugins/build_binaries/build_binaries.hjson
```

```commandline
(env3.6) # ls sab_workspace/portage_artifacts/
Packages   app-doc      app-shells  dev-libs    dev-vcs      net-fs    net-wireless  sys-devel   virtual
app-admin  app-editors  app-text    dev-perl    gnome-extra  net-libs  sys-apps      sys-fs      www-client
app-arch   app-eselect  app-vim     dev-python  net-dialup   net-misc  sys-auth      sys-kernel  x11-misc
app-crypt  app-portage  dev-lang    dev-util    net-dns      net-nds   sys-block     sys-libs
```

```commandline
(env3.6) # ls sab_workspace/entropy_artifacts/standard/testing.kantoo.org/packages/amd64/5
app-admin  app-editors  app-shells  dev-lang    dev-util     net-dialup    net-libs      perl-core  sys-devel   sys-process
app-arch   app-eselect  app-text    dev-libs    dev-vcs      net-dns       net-misc      sys-apps   sys-fs      virtual
app-crypt  app-misc     app-vim     dev-perl    gnome-extra  net-firewall  net-nds       sys-auth   sys-kernel  www-client
app-doc    app-portage  dev-db      dev-python  mail-mta     net-fs        net-wireless  sys-block  sys-libs    x11-misc
```

```commandline
(env3.6) #  ./dockerdriver --config plugins/stage4/stage4.hjson
```

```commandline
(env3.6) # ls sab_workspace/stage4s/
boot.tar  stage4.tar
```


