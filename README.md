# Kantoo Devkit 0.4.1 #

Kantoo **is** Funtoo, with a twist.

This is a collection of tools modeled on the [Sabayon Devkit](https://github.com/Sabayon/devkit).

The idea is to facilitate the creation of 'Kantoo stage4s:' Funtoo stage3s that have been augmented to allow installation of binary packages (comprising a small subset of the total Portage universe) via the Entropy package manager. The first target architecture is `arm-32bit/raspi3` in Funtoo terms or `armv7l` in Sabayon terms. However, the implementation should work across all architectures and optimizations in true Funtoo fashion.

The `stalker` executable is used to create a graph of docker images connected by transformation of their filesystems, as described in an `hjson` configuration file. The graph knits together stalks, linear pipelines of operations on an operating system image.

You must have a working docker install on your development machine. Add yourself to the `docker` group to work without needing root privileges.  

## Why Not Just Use `RUN` in Dockerfiles? ##

I'm not sure exactly. But I feel I needed to structure the modification process of an image more explicitly, and modularize the common steps, especially with respect to the initial use case: building lots of binary packages with particular USE sets and managing repos of them.

## Setup and Configuration ##

### Clone It ###
```commandline
# git clone https://github.com/d4g33z/kantoo-devkit.git
```
### Use Virtualenv (Please) ###

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

### Create Static Sysroot Files ###
You can use a directory called `sysroot` in the `lib` directory to keep files and directories that give bind mounted to your containers automatically. You can keep things here that you always need: code libraries, configuration files, the Funtoo git repo, etc. The key one is the `/var/git` link. 
```commandline
(env3.6) # mkdir lib/var && ln -s /var/git lib/sysroot/var/
```  

Here is mine.

```commandline
(env3.6) # ls -lR lib/sysroot/
lib/sysroot/:
total 16
drwxr-xr-x 3 jeff jeff 4096 Mar 18 00:15 entropy
drwxr-xr-x 5 jeff jeff 4096 Mar 19 14:49 etc
drwxr-xr-x 3 jeff jeff 4096 Mar 18 14:09 root
drwxr-xr-x 2 jeff jeff 4096 Mar 17 23:06 var

lib/sysroot/entropy:
total 4
drwxr-xr-x 2 jeff jeff 4096 Apr 20 15:27 plugins

lib/sysroot/entropy/plugins:
total 0
lrwxrwxrwx 1 jeff jeff 29 Mar 18 00:16 kantoo -> ../../../../lib/python/kantoo
lrwxrwxrwx 1 jeff jeff 30 Apr 20 15:27 kantoo.sh -> ../../../../lib/bash/kantoo.sh

lib/sysroot/etc:
total 12
drwxr-xr-x 2 jeff jeff 4096 Apr  3 16:11 conf.d
drwxr-xr-x 2 jeff jeff 4096 Mar 19 14:49 entropy
drwxr-xr-x 3 jeff jeff 4096 Apr  3 15:43 portage

lib/sysroot/etc/conf.d:
total 0

lib/sysroot/etc/entropy:
total 8
-rw-r--r-- 1 jeff jeff 5082 Mar 19 14:35 client.conf

lib/sysroot/etc/portage:
total 12
drwxr-xr-x 2 jeff jeff 4096 Mar 18 14:29 env
-rw-r--r-- 1 jeff jeff  134 Mar 18 14:29 package.env
-rw-r--r-- 1 jeff jeff  209 Apr  3 15:43 package.use

lib/sysroot/etc/portage/env:
total 8
-rw-r--r-- 1 jeff jeff 33 Mar 18 14:29 nodistcc-pump.conf
-rw-r--r-- 1 jeff jeff 41 Mar 18 14:29 nodistcc.conf

lib/sysroot/root:
total 0

lib/sysroot/var:
total 0
lrwxrwxrwx 1 jeff jeff 8 Mar 17 23:06 git -> /var/git

```


## How To Use it ##

There are at least two [hjson](hjson.org) config files to write: one tree file and one stalk file. A tree is composed of stalks. The `hello_world.json` file in the `trees/hello_world` directory is a tree configuration file. It holds one stalk, who's configuration is found in `stalks/hello_world/hello_world.hjson`. Running the `stalker` program with the tree config as input results a sequence of Docker images being built to reflect the directives found in the stalk config file.

The stalk config files, and the necessary bash and python scripts it references, are used to feed the `command` argument of the `container.exec_run` method in the [python docker sdk](https://docker-py.readthedocs.io/en/stable/index.html). The `dockerdriver` sets up the container and runs the configured scripts in the container in sequence.

### Hello, world! ###
See `trees/hello_world/hello_world.hjson` and `stalks/hello_world/hello_world.hjson`. It demonstrates the many different ways to pass values from the `hjson` file to bash or python scripts running in a container.

```commandline
(env3.6) # rm -f logs/*
(env3.6) # ./stalker --config trees/hello_world/hello_world.hjson --watch_stdout
--------------------------------------------------------------------------------

* shell and f-string variables that are used in shell scripts used to modify this image must be declared here
* if they are set to the empty string, they are set by the tree config that this stalk is contained in

These are bash variables
TREE_CONFIG_VAR is set to hello from stalker config
STALK_CONFIG_VAR is set to hello from dockerdriver config

Python f-string subsitution is done on file plugins
e.g. {F_STRING_VAR} in /tmp/hello_file is set to
hello from f-string subsitution in a file

--------------------------------------------------------------------------------

hello from a python plugin via environment variables

--------------------------------------------------------------------------------

hello from a python plugin via arguments

--------------------------------------------------------------------------------

hello from a python plugin via explicit arguments

(env3.6) # cat logs/hello_world/*
* shell and f-string variables that are used in shell scripts used to modify this image must be declared here
* if they are set to the empty string, they are set by the tree config that this stalk is contained in

These are bash variables
TREE_CONFIG_VAR is set to hello from stalker config
STALK_CONFIG_VAR is set to hello from dockerdriver config

Python f-string subsitution is done on file plugins
e.g. {F_STRING_VAR} in /tmp/hello_file is set to
hello from f-string subsitution in a file
hello from a python plugin via arguments
hello from a python plugin via environment variables
hello from a python plugin via explicit arguments
(env3.6) # docker images | grep hello_world
funtoo/x86-64bit/amd64-k10/hello_world   hello_python_from_explicit_env   4b8ba4b31681        2 minutes ago       908MB
funtoo/x86-64bit/amd64-k10/hello_world   hello_python_from_arg            1996ea72dd49        2 minutes ago       908MB
funtoo/x86-64bit/amd64-k10/hello_world   hello_python_from_env            a2e1544db0fb        2 minutes ago       908MB
funtoo/x86-64bit/amd64-k10/hello_world   hello_from_sh                    4ca5a981c925        2 minutes ago       908MB
funtoo/x86-64bit/amd64-k10/hello_world   hello_from                       152c696cbd20        8 days ago          908MB
funtoo/x86-64bit/amd64-k10/hello_world   hello_world                      fb6bd72703ff        8 days ago          908MB
funtoo/x86-64bit/amd64-k10/hello_world   initial                          82aec17005f2        12 days ago         908MB

(env3.6) # eliot-tree logs/eliot.txt
522f484b-958e-4483-9a70-32f5c849dca6
└── Stalker/1 ⇒ started 2019-06-16 03:09:14 ⧖ 0.001s
    ├── config: trees/hello_world/hello_world.hjson
    ├── cwd: /mnt/vault/Workspace/kantoo-devkit.git
    └── Stalker/2 ⇒ succeeded 2019-06-16 03:09:14

b77ea984-2a89-4e2b-b475-015a192a6b0e
└── run/1 ⇒ started 2019-06-16 03:09:14 ⧖ 4.363s
    ├── hello_world/2 2019-06-16 03:09:14
    │   └── keychain: 
    │       ├── 0: stalks
    │       └── 1: hello_world
    ├── _set_config_attrs/3/1 ⇒ started 2019-06-16 03:09:14 ⧖ 0.000s
    │   ├── config vars/3/2 2019-06-16 03:09:14
    │   │   ├── ARCH: x86-64bit
    │   │   ├── DOCKER_OPTS: 
    │   │   │   ├── detach: True
    │   │   │   ├── entrypoint: /bin/bash
    │   │   │   ├── init: True
    │   │   │   ├── remove: False
    │   │   │   └── tty: True
    │   │   ├── ENTROPY_ARCH: amd64
    │   │   ├── LOG_DIR: logs
    │   │   ├── OS: funtoo
    │   │   ├── SUBARCH: amd64-k10
    │   │   ├── SYSROOT_DIR: lib/sysroot
    │   │   ├── TMPFS: tmpfs
    │   │   └── TREE_CONFIG_VAR: hello from stalker config
    │   └── _set_config_attrs/3/3 ⇒ succeeded 2019-06-16 03:09:14
    ├── _set_plugins/4/1 ⇒ started 2019-06-16 03:09:14 ⧖ 0.008s
    │   ├── _plugin_factory/4/2/1 ⇒ started 2019-06-16 03:09:14 ⧖ 0.002s
    │   │   └── _plugin_factory/4/2/2 ⇒ succeeded 2019-06-16 03:09:14
    │   └── _set_plugins/4/3 ⇒ succeeded 2019-06-16 03:09:14
    ├── _set_docker_opts/5/1 ⇒ started 2019-06-16 03:09:14 ⧖ 0.001s
    │   └── _set_docker_opts/5/2 ⇒ succeeded 2019-06-16 03:09:14
    ├── initialize/6/1 ⇒ started 2019-06-16 03:09:14 ⧖ 0.066s
    │   ├── info/6/2 2019-06-16 03:09:14
    │   │   └── msg: funtoo/x86-64bit/amd64-k10/hello_world:initial found
    │   └── initialize/6/3 ⇒ succeeded 2019-06-16 03:09:14
    ├── start/7/1 ⇒ started 2019-06-16 03:09:14 ⧖ 4.283s
    │   ├── info/7/2 2019-06-16 03:09:14
    │   │   └── msg: hello_from_sh : dreamy_bell created
    │   ├── log file path/7/3 2019-06-16 03:09:14
    │   │   └── log_file: /mnt/vault/Workspace/kantoo-devkit.git/logs/hello_world/x86-64bit-amd64-k10-hello_from_sh-19-06-15-2…
    │   ├── info/7/4 2019-06-16 03:09:15
    │   │   └── msg: hello_from_sh : sha256:b696b9b33b committed
    │   ├── info/7/5 2019-06-16 03:09:15
    │   │   └── msg: hello_python_from_env : vibrant_hodgkin created
    │   ├── log file path/7/6 2019-06-16 03:09:15
    │   │   └── log_file: /mnt/vault/Workspace/kantoo-devkit.git/logs/hello_world/x86-64bit-amd64-k10-hello_python_from_env-19…
    │   ├── info/7/7 2019-06-16 03:09:16
    │   │   └── msg: hello_python_from_env : sha256:a96b7c23e1 committed
    │   ├── info/7/8 2019-06-16 03:09:16
    │   │   └── msg: hello_python_from_arg : compassionate_blackburn created
    │   ├── log file path/7/9 2019-06-16 03:09:16
    │   │   └── log_file: /mnt/vault/Workspace/kantoo-devkit.git/logs/hello_world/x86-64bit-amd64-k10-hello_python_from_arg-19…
    │   ├── info/7/10 2019-06-16 03:09:17
    │   │   └── msg: hello_python_from_arg : sha256:dbc059439d committed
    │   ├── info/7/11 2019-06-16 03:09:17
    │   │   └── msg: hello_python_from_explicit_env : eager_poitras created
    │   ├── log file path/7/12 2019-06-16 03:09:18
    │   │   └── log_file: /mnt/vault/Workspace/kantoo-devkit.git/logs/hello_world/x86-64bit-amd64-k10-hello_python_from_explic…
    │   ├── info/7/13 2019-06-16 03:09:18
    │   │   └── msg: hello_python_from_explicit_env : sha256:f368b1ed4d committed
    │   └── start/7/14 ⇒ succeeded 2019-06-16 03:09:18
    └── run/8 ⇒ succeeded 2019-06-16 03:09:18

```

## How to Make a Stage4 with Entropy Repo##
This tool was created to facilitate building simple Funtoo stage4s with the Sabayon binary package management system called Entropy. Such system builds should be quick and modular, permitting continuous, integrated development.

The tool is not too complicated once it is set up. Here are some terminal sessions to give a feel for it.

The tree file is `trees/kantoo/kantoo.hjson`.  The tree is a simple pipeline of three stalks, `stage3`,`build_repo`, and `stage4`, the config files of which may be found in `stalks/<name>/<name>.hjson`.

Here we build the binaries, both Portage and Entropy versions. The packages to build are specifies in the config file. Portage uses distcc on the local network to build its binaries, which are re-packaged and injected into a repository by Entropy. The sequence can be restarted at any point. Portage uses its created binaries as a cache to speed things up. Linking consistency is aways checked on a pure Portage filesystem so that Entropy packages can be injected in to a repo without such checking.  

```commandline
(env3.6) #  ./stalker --config trees/kantoo/kantoo.hjson
..<much output>..
```

Here are the Portage packages.

```commandline
(env3.6) # ls sab_workspace/portage_artifacts/
Packages   app-doc      app-shells  dev-libs    dev-vcs      net-fs    net-wireless  sys-devel   virtual
app-admin  app-editors  app-text    dev-perl    gnome-extra  net-libs  sys-apps      sys-fs      www-client
app-arch   app-eselect  app-vim     dev-python  net-dialup   net-misc  sys-auth      sys-kernel  x11-misc
app-crypt  app-portage  dev-lang    dev-util    net-dns      net-nds   sys-block     sys-libs
```

Here are the Entropy packages.
```commandline
(env3.6) # ls sab_workspace/entropy_artifacts/standard/testing.kantoo.org/packages/amd64/5
app-admin  app-editors  app-shells  dev-lang    dev-util     net-dialup    net-libs      perl-core  sys-devel   sys-process
app-arch   app-eselect  app-text    dev-libs    dev-vcs      net-dns       net-misc      sys-apps   sys-fs      virtual
app-crypt  app-misc     app-vim     dev-perl    gnome-extra  net-firewall  net-nds       sys-auth   sys-kernel  www-client
app-doc    app-portage  dev-db      dev-python  mail-mta     net-fs        net-wireless  sys-block  sys-libs    x11-misc
```

Here are the created stage4 root and boot partitions. 

```commandline
(env3.6) # ls sab_workspace/stage4s/
boot.tar  stage4.tar
`````
