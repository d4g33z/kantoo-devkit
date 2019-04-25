# Kantoo Devkit 0.4 #

Kantoo **is** Funtoo, with a twist.

This is a collection of tools modeled on the [Sabayon Devkit](https://github.com/Sabayon/devkit).

The idea is to facilitate the creation of 'Kantoo stage4s:' Funtoo stage3s that have been augmented to allow installation of binary packages (comprising a small subset of the total Portage universe) via the Entropy package manager. The first target architecture is `arm-32bit/raspi3` in Funtoo terms or `armv7l` in Sabayon terms.

The `dockerdriver` executable is used to create a containers of of a choosen subarch, profile and mixins, attaching bind mounts (files and directorys on the host that become visible in the container at a choosen location) and environment variables, and executing a series of bash or python scripts to modify it and commit the result as a new image.

You must have a working docker install on your development machine. Add yourself to the `docker` group to work without needing root privileges.  

## Why Not Just Use Dockerfiles? ##

I'm not sure exactly. But I feel I needed to structure the modification process of an image more explicitly, and modularize the common steps, especially with respect to the initial use case: building lots of binary packages with particular USE sets and managing repos of them.

## Setup and Configuration ##

### Clone It ###
```commandline
# git clone https://code.funtoo.org/bitbucket/scm/~d4g33z/kantoo-devkit.git
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
dazzling_leakey : sha256:c97470add300df05698c0484865e98ec98f459ef580a713581d1a8de0947911d committed
>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
Creating container of funtoo/x86-64bit/amd64-k10/hello_world:hello_world to run hello_python_from_env on.
condescending_yalow : sha256:b6af51b550edfcbb8e229b9f90c2f28910ebe4010190e13f4616c607ae99537a committed
>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
Creating container of funtoo/x86-64bit/amd64-k10/hello_world:hello_python_from_env to run hello_python_from_arg on.
eager_curran : sha256:8a59bef5b79cce90932538e8b8772f536e7e2aaf7d20430a2a131b0349fbaa87 committed
>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
Creating container of funtoo/x86-64bit/amd64-k10/hello_world:hello_python_from_arg to run hello_python_from_explicit_env on.
nervous_euler : sha256:2a8d2189417ce401b155c93700d6fd285d5ed25e4e046d5a5c37b1b1dd3c81ed committed
(env3.6) # cat logs/hello_world/*
hello from a python plugin via arguments
hello from a python plugin via environment variables
hello from a python plugin via explicit arguments
hello globally
hello locally from bash
hello locally
hello via override
(env3.6) # docker images | grep hello_world
funtoo/x86-64bit/amd64-k10/hello_world      hello_python_from_explicit_env   2a8d2189417c        About a minute ago   892MB
funtoo/x86-64bit/amd64-k10/hello_world      hello_python_from_arg            8a59bef5b79c        About a minute ago   892MB
funtoo/x86-64bit/amd64-k10/hello_world      hello_python_from_env            b6af51b550ed        About a minute ago   892MB
funtoo/x86-64bit/amd64-k10/hello_world      hello_world                      c97470add300        About a minute ago   892MB
funtoo/x86-64bit/amd64-k10/hello_world      initial                          d0d31dc47745        2 weeks ago          892MB
```

## How to Make a Stage4 with Entropy Repo##
This tool was created to facilitate building simple Funtoo stage4s with the Sabayon binary package management system called Entropy. Such system builds should be quick and modular, permitting continuous, integrated development.

The tool is not too complicated once it is set up. Here are some terminal sessions to give a feel for it.

Here we build the binaries, both Portage and Entropy versions. The packages to build are specifies in the config file. Portage uses distcc on the local network to build its binaries, which are re-packaged and injected into a repository by Entropy. The sequence can be restarted at any point. Portage uses its created binaries as a cache to speed things up. Linking consistency is aways checked on a pure Portage filesystem so that Entropy packages can be injected in to a repo without such checking.  

```commandline
(env3.6) #  ./dockerdriver --config plugins/build_binaries/build_binaries.hjson
>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
Creating container of funtoo/x86-64bit/amd64-k10/build_binaries:initial to run install_distcc on.
confident_pare : sha256:d203a0261fa066053071fe6bc3a1a5f58370e56c3fbf87b788b879a5ca259d5f committed
>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
Creating container of funtoo/x86-64bit/amd64-k10/build_binaries:install_distcc to run emerge_world on.
objective_hypatia : sha256:001d2221f47a8ff77e792919c5e5198d97e333a7d87c267353b96fceef6f919b committed
>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
Creating container of funtoo/x86-64bit/amd64-k10/build_binaries:emerge_world to run install_portage_pkgs on.
optimistic_ritchie : sha256:868f88d7dba9c0fa3e68e532e60089d18f17c719db554f27c39c576753a41575 committed
>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
Creating container of funtoo/x86-64bit/amd64-k10/build_binaries:install_portage_pkgs to run patch_eit on.
wizardly_wright : sha256:df0d2eb8ba1db201e20274fbbafb42992732aea6d918a42cae2c0423e17cad71 committed
>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
Creating container of funtoo/x86-64bit/amd64-k10/build_binaries:patch_eit to run rebuild_entropy_database on.
practical_mcnulty : sha256:a4ecac61bb48e312286d47626267b79c6ca24c01d160f1c14f86574035b47b71 committed
>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
Creating container of funtoo/x86-64bit/amd64-k10/build_binaries:rebuild_entropy_database to run sync_or_create_local_repo on.
flamboyant_wing : sha256:5285c03f2d8f44b7394231254e9cfa42c3c52b33cf0a71a3be210b2edbc5fdd7
>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
Creating container of funtoo/x86-64bit/amd64-k10/build_binaries:sync_or_create_local_repo to run inject_pkgdir on.
eager_shirley : sha256:e59d001e03e3e5667a4412da49fac52d1d3e0e17af0f0d26221b095ffb0f2f58 committed
>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
Creating container of funtoo/x86-64bit/amd64-k10/build_binaries:inject_pkgdir to run push on.
cranky_ride : sha256:ea54e446510a0391a9138106e5dc7f1fc31a63c1e8e70eba6794312cbf13a73a committed
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

Here are the logs.
```commandline
(env3.6) # ls -lsrth logs/build_binaries/
total 2.9M
168K -rw-r--r-- 1 jeff jeff 165K Apr 23 14:37 x86-64bit-amd64-k10-install_distcc-19-04-23-14:37:07.txt
8.0K -rw-r--r-- 1 jeff jeff 6.8K Apr 23 14:38 x86-64bit-amd64-k10-emerge_world-19-04-23-14:38:18.txt
808K -rw-r--r-- 1 jeff jeff 806K Apr 23 14:46 x86-64bit-amd64-k10-install_portage_pkgs-19-04-23-14:46:01.txt
4.0K -rw-r--r-- 1 jeff jeff  613 Apr 23 14:46 x86-64bit-amd64-k10-patch_eit-19-04-23-14:46:19.txt
 16K -rw-r--r-- 1 jeff jeff  13K Apr 23 14:48 x86-64bit-amd64-k10-rebuild_entropy_database-19-04-23-14:48:18.txt
1.3M -rw-r--r-- 1 jeff jeff 1.3M Apr 23 14:48 x86-64bit-amd64-k10-sync_or_create_local_repo-19-04-23-14:48:53.txt
264K -rw-r--r-- 1 jeff jeff 261K Apr 23 14:54 x86-64bit-amd64-k10-inject_pkgdir-19-04-23-14:54:55.txt
364K -rw-r--r-- 1 jeff jeff 362K Apr 23 14:58 x86-64bit-amd64-k10-push-19-04-23-14:58:02.txt

```

Now we build the stage4, installing anything we need via `equo`, the Entropy package manager using the repo we created above. 
```commandline
(env3.6) #  ./dockerdriver --config plugins/stage4/stage4.hjson
>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
Creating container of funtoo/x86-64bit/amd64-k10/stage4:initial to run install_equo on.
stoic_panini : sha256:7329a1502eb4a999d00f7f2564cabe471b503fe232cb3a806ec18f19867b794c committed
>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
Creating container of funtoo/x86-64bit/amd64-k10/stage4:install_equo to run unmask_equo_pkgs on.
dazzling_easley : sha256:ef11d0eba15dbb56efa61caf03cdd6f83b0e03905bb1c8eddabf07d0b54f4eda committed
>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
Creating container of funtoo/x86-64bit/amd64-k10/stage4:unmask_equo_pkgs to run equo_upgrade on.
brave_babbage : sha256:334e6c168326061d62db35168aedc38ecec6413182958edb79b447b197f47146 committed
>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
Creating container of funtoo/x86-64bit/amd64-k10/stage4:equo_upgrade to run install_equo_packages on.
blissful_yalow : sha256:bf3b73c1e06a80c2eb46a9ed266fb1fe22ea83492b15a6bbcb0f31b3dbb048a3 committed
>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
Creating container of funtoo/x86-64bit/amd64-k10/stage4:install_equo_packages to run config_services on.
stoic_antonelli : sha256:a8b6655bb0a49d5b2e35e1e40f3d2a71b9a4c3e8dbd2953496dfb23b0b22a6e6 committed
>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
Creating container of funtoo/x86-64bit/amd64-k10/stage4:config_services to run config_system on.
cocky_blackburn : sha256:6624567da5eaba291f0bbe108bfc52f7912cbdeff9874754bb0d945a2cde2ca5 committed
>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
Creating container of funtoo/x86-64bit/amd64-k10/stage4:config_system to run install_firmware on.
epic_cohen : sha256:b099fd99cf46c277f3fd7a64105aa627a61fc8a8cfc3a8710bd057d2bded0176 committed
>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
Creating container of funtoo/x86-64bit/amd64-k10/stage4:install_firmware to run install_kernel on.
recursing_germain : sha256:b5097c9224f74dc0c1ddffece40620625fbb94f3aeb36fdf35d070b9dd495f2c committed
>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
Creating container of funtoo/x86-64bit/amd64-k10/stage4:install_kernel to run export_fs on.
vigilant_dirac : sha256:681eaca6b314f42f77ba87e6d03d1663e2c7fbc311ec3737cb69b1f4d6da50de committed
>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
Creating container of funtoo/x86-64bit/amd64-k10/stage4:export_fs to run export_profiles on.
trusting_booth : sha256:121e12f9cc28411e5ed2480ab19f5b549767c4d556309ca96affeddb3ddc9221 committed

```

Here are the created stage4 root and boot partitions. 

```commandline
(env3.6) # ls sab_workspace/stage4s/
boot.tar  stage4.tar
```

Here are the logs.
```commandline
(env3.6) #  ls -lsrth logs/stage4
total 152K
 16K -rw-r--r-- 1 jeff jeff  15K Apr 23 15:14 x86-64bit-amd64-k10-install_equo-19-04-23-15:14:55.txt
4.0K -rw-r--r-- 1 jeff jeff  666 Apr 23 15:15 x86-64bit-amd64-k10-unmask_equo_pkgs-19-04-23-15:15:01.txt
4.0K -rw-r--r-- 1 jeff jeff 2.7K Apr 23 15:15 x86-64bit-amd64-k10-equo_upgrade-19-04-23-15:15:05.txt
116K -rw-r--r-- 1 jeff jeff 114K Apr 23 15:16 x86-64bit-amd64-k10-install_equo_packages-19-04-23-15:16:37.txt
4.0K -rw-r--r-- 1 jeff jeff  418 Apr 23 15:16 x86-64bit-amd64-k10-config_services-19-04-23-15:16:45.txt
   0 -rw-r--r-- 1 jeff jeff    0 Apr 23 15:16 x86-64bit-amd64-k10-config_system-19-04-23-15:16:46.txt
4.0K -rw-r--r-- 1 jeff jeff   20 Apr 23 15:16 x86-64bit-amd64-k10-install_firmware-19-04-23-15:16:47.txt
   0 -rw-r--r-- 1 jeff jeff    0 Apr 23 15:16 x86-64bit-amd64-k10-install_kernel-19-04-23-15:16:51.txt
4.0K -rw-r--r-- 1 jeff jeff  340 Apr 23 15:17 x86-64bit-amd64-k10-export_fs-19-04-23-15:17:18.txt
   0 -rw-r--r-- 1 jeff jeff    0 Apr 23 15:17 x86-64bit-amd64-k10-export_profiles-19-04-23-15:17:29.txt
```

And `eliot` log is captured as well:
```commandline
(env3.6) # eliot-tree logs/eliot.txt
a5e3cd2c-47c7-4f0a-a783-c0a1d8ba7e05
└── DockerDriver/1 ⇒ started 2019-04-25 19:15:17 ⧖ 0.024s
    ├── config: plugins/hello_world/hello_world.hjson
    ├── cwd: /home/jeff/Workspace/kantoo-devkit.git
    ├── _set_config_attrs/2/1 ⇒ started 2019-04-25 19:15:17 ⧖ 0.000s
    │   ├── info/2/2 2019-04-25 19:15:17
    │   │   ├── ARCH: x86-64bit
    │   │   ├── DOCKER_INIT_IMG: stage3:initial
    │   │   ├── DOCKER_OPTS: 
    │   │   │   ├── detach: True
    │   │   │   ├── entrypoint: /bin/bash
    │   │   │   ├── init: True
    │   │   │   ├── remove: False
    │   │   │   └── tty: True
    │   │   ├── ENTROPY_ARCH: amd64
    │   │   ├── GLOBAL_VAR: hello globally
    │   │   ├── OS: funtoo
    │   │   ├── SUBARCH: amd64-k10
    │   │   └── SYSROOT_DIR: lib/sysroot
    │   └── _set_config_attrs/2/3 ⇒ succeeded 2019-04-25 19:15:17
    ├── _set_plugins/3/1 ⇒ started 2019-04-25 19:15:17 ⧖ 0.019s
    │   ├── _plugin_factory/3/2/1 ⇒ started 2019-04-25 19:15:17 ⧖ 0.003s
    │   │   ├── info/3/2/2 2019-04-25 19:15:17
    │   │   │   ├── hello_file: 
    │   │   │   │   ├── GLOBAL_VAR: hello via override
    │   │   │   │   ├── LOCAL_VAR: hello locally
    │   │   │   │   ├── bind: /tmp/hello_file
    │   │   │   │   └── text: {LOCAL_VAR}…
    │   │   │   ├── hello_python_from_arg: 
    │   │   │   │   ├── HELLO_MSG: hello from a python plugin via arguments
    │   │   │   │   ├── exec: True
    │   │   │   │   └── text: #!/usr/bin/env python3…
    │   │   │   ├── hello_python_from_env: 
    │   │   │   │   ├── HELLO_MSG: hello from a python plugin via environment variables
    │   │   │   │   ├── exec: True
    │   │   │   │   └── text: #!/usr/bin/env python3…
    │   │   │   ├── hello_python_from_explicit_env: 
    │   │   │   │   ├── HELLO_MSG: hello from a python plugin via explicit arguments
    │   │   │   │   ├── exec: True
    │   │   │   │   └── text: #!/usr/bin/env python3…
    │   │   │   └── hello_world: 
    │   │   │       ├── GLOBAL_VAR: 
    │   │   │       ├── LOCAL_VAR: hello locally from bash
    │   │   │       ├── exec: True
    │   │   │       └── text: #!/usr/bin/env sh…
    │   │   └── _plugin_factory/3/2/3 ⇒ succeeded 2019-04-25 19:15:17
    │   ├── info/3/3 2019-04-25 19:15:17
    │   │   ├── entropy/plugins/kantoo: 
    │   │   │   ├── bind: /entropy/plugins/kantoo
    │   │   │   ├── exec: False
    │   │   │   └── path: /home/jeff/Workspace/kantoo-devkit.git/lib/python/kantoo
    │   │   └── var/git: 
    │   │       ├── bind: /var/git
    │   │       ├── exec: False
    │   │       └── path: /var/git
    │   ├── info/3/4 2019-04-25 19:15:17
    │   │   ├── entropy/plugins/kantoo.sh: 
    │   │   │   ├── bind: /entropy/plugins/kantoo.sh
    │   │   │   ├── exec: False
    │   │   │   └── path: /home/jeff/Workspace/kantoo-devkit.git/lib/bash/kantoo.sh
    │   │   ├── etc/entropy/client.conf: 
    │   │   │   ├── bind: /etc/entropy/client.conf
    │   │   │   ├── exec: False
    │   │   │   └── path: /home/jeff/Workspace/kantoo-devkit.git/lib/sysroot/etc/entropy/client.conf
    │   │   ├── etc/portage/env/nodistcc-pump.conf: 
    │   │   │   ├── bind: /etc/portage/env/nodistcc-pump.conf
    │   │   │   ├── exec: False
    │   │   │   └── path: /home/jeff/Workspace/kantoo-devkit.git/lib/sysroot/etc/portage/env/nodistcc-pump.conf
    │   │   ├── etc/portage/env/nodistcc.conf: 
    │   │   │   ├── bind: /etc/portage/env/nodistcc.conf
    │   │   │   ├── exec: False
    │   │   │   └── path: /home/jeff/Workspace/kantoo-devkit.git/lib/sysroot/etc/portage/env/nodistcc.conf
    │   │   ├── etc/portage/package.env: 
    │   │   │   ├── bind: /etc/portage/package.env
    │   │   │   ├── exec: False
    │   │   │   └── path: /home/jeff/Workspace/kantoo-devkit.git/lib/sysroot/etc/portage/package.env
    │   │   ├── etc/portage/package.use: 
    │   │   │   ├── bind: /etc/portage/package.use
    │   │   │   ├── exec: False
    │   │   │   └── path: /home/jeff/Workspace/kantoo-devkit.git/lib/sysroot/etc/portage/package.use
    │   │   ├── root/.inputrc: 
    │   │   │   ├── bind: /root/.inputrc
    │   │   │   ├── exec: False
    │   │   │   └── path: /home/jeff/Workspace/kantoo-devkit.git/lib/sysroot/root/.inputrc
    │   │   ├── root/.ssh/authorized_keys: 
    │   │   │   ├── bind: /root/.ssh/authorized_keys
    │   │   │   ├── exec: False
    │   │   │   └── path: /home/jeff/Workspace/kantoo-devkit.git/lib/sysroot/root/.ssh/authorized_keys
    │   │   ├── root/.ssh/docker_login: 
    │   │   │   ├── bind: /root/.ssh/docker_login
    │   │   │   ├── exec: False
    │   │   │   └── path: /home/jeff/Workspace/kantoo-devkit.git/lib/sysroot/root/.ssh/docker_login
    │   │   ├── root/.ssh/docker_login.pub: 
    │   │   │   ├── bind: /root/.ssh/docker_login.pub
    │   │   │   ├── exec: False
    │   │   │   └── path: /home/jeff/Workspace/kantoo-devkit.git/lib/sysroot/root/.ssh/docker_login.pub
    │   │   └── root/.ssh/known_hosts: 
    │   │       ├── bind: /root/.ssh/known_hosts
    │   │       ├── exec: False
    │   │       └── path: /home/jeff/Workspace/kantoo-devkit.git/lib/sysroot/root/.ssh/known_hosts
    │   └── _set_plugins/3/5 ⇒ succeeded 2019-04-25 19:15:17
    ├── _set_docker_opts/4/1 ⇒ started 2019-04-25 19:15:17 ⧖ 0.001s
    │   ├── info/4/2 2019-04-25 19:15:17
    │   │   ├── detach: True
    │   │   ├── entrypoint: /bin/bash
    │   │   ├── environment: 
    │   │   │   ├── 0: EDITOR=cat
    │   │   │   └── 1: LC_ALL=en_US.UTF-8
    │   │   ├── init: True
    │   │   ├── remove: False
    │   │   ├── tty: True
    │   │   ├── volumes: 
    │   │   │   ├── /home/jeff/Workspace/kantoo-devkit.git/lib/python/kantoo: 
    │   │   │   │   ├── bind: /entropy/plugins/kantoo
    │   │   │   │   └── mode: ro
    │   │   │   ├── /tmp/tmp02knxch4: 
    │   │   │   │   ├── bind: /etc/portage/env/nodistcc-pump.conf
    │   │   │   │   └── mode: ro
    │   │   │   ├── /tmp/tmp2hjiawt6: 
    │   │   │   │   ├── bind: /root/.ssh/known_hosts
    │   │   │   │   └── mode: ro
    │   │   │   ├── /tmp/tmp55y87xgv: 
    │   │   │   │   ├── bind: /etc/portage/env/nodistcc.conf
    │   │   │   │   └── mode: ro
    │   │   │   ├── /tmp/tmp58c69k_n: 
    │   │   │   │   ├── bind: /entropy/bin/hello_python_from_env
    │   │   │   │   └── mode: ro
    │   │   │   ├── /tmp/tmp67hgltju: 
    │   │   │   │   ├── bind: /root/.ssh/docker_login.pub
    │   │   │   │   └── mode: ro
    │   │   │   ├── /tmp/tmp8ww2par8: 
    │   │   │   │   ├── bind: /entropy/plugins/hello_python_from_env
    │   │   │   │   └── mode: ro
    │   │   │   ├── /tmp/tmpa9jq2kfa: 
    │   │   │   │   ├── bind: /etc/portage/package.use
    │   │   │   │   └── mode: ro
    │   │   │   ├── /tmp/tmpaarpctxo: 
    │   │   │   │   ├── bind: /entropy/bin/hello_python_from_explicit_env
    │   │   │   │   └── mode: ro
    │   │   │   ├── /tmp/tmpdmds_69p: 
    │   │   │   │   ├── bind: /entropy/plugins/hello_python_from_arg
    │   │   │   │   └── mode: ro
    │   │   │   ├── /tmp/tmpefqawczy: 
    │   │   │   │   ├── bind: /etc/entropy/client.conf
    │   │   │   │   └── mode: ro
    │   │   │   ├── /tmp/tmpgjn0jupj: 
    │   │   │   │   ├── bind: /etc/portage/package.env
    │   │   │   │   └── mode: ro
    │   │   │   ├── /tmp/tmphuuhkvji: 
    │   │   │   │   ├── bind: /entropy/bin/hello_world
    │   │   │   │   └── mode: ro
    │   │   │   ├── /tmp/tmpjor_n_1x: 
    │   │   │   │   ├── bind: /root/.inputrc
    │   │   │   │   └── mode: ro
    │   │   │   ├── /tmp/tmpjoyltc8_: 
    │   │   │   │   ├── bind: /entropy/plugins/hello_world
    │   │   │   │   └── mode: ro
    │   │   │   ├── /tmp/tmpks7rh30z: 
    │   │   │   │   ├── bind: /tmp/hello_file
    │   │   │   │   └── mode: ro
    │   │   │   ├── /tmp/tmpnjdgx78f: 
    │   │   │   │   ├── bind: /entropy/plugins/kantoo.sh
    │   │   │   │   └── mode: ro
    │   │   │   ├── /tmp/tmpph08va95: 
    │   │   │   │   ├── bind: /entropy/bin/hello_python_from_arg
    │   │   │   │   └── mode: ro
    │   │   │   ├── /tmp/tmprn8wqria: 
    │   │   │   │   ├── bind: /entropy/plugins/hello_python_from_explicit_env
    │   │   │   │   └── mode: ro
    │   │   │   ├── /tmp/tmptlxl99m6: 
    │   │   │   │   ├── bind: /root/.ssh/docker_login
    │   │   │   │   └── mode: ro
    │   │   │   ├── /tmp/tmpwkkxf9c1: 
    │   │   │   │   ├── bind: /root/.ssh/authorized_keys
    │   │   │   │   └── mode: ro
    │   │   │   └── /var/git: 
    │   │   │       ├── bind: /var/git
    │   │   │       └── mode: ro
    │   │   └── working_dir: /
    │   └── _set_docker_opts/4/3 ⇒ succeeded 2019-04-25 19:15:17
    └── DockerDriver/5 ⇒ succeeded 2019-04-25 19:15:17

ce96a7da-b72d-4b4e-a314-812b9742d557
└── initialize/1 ⇒ started 2019-04-25 19:15:17 ⧖ 0.176s
    ├── info/2 2019-04-25 19:15:17
    │   └── msg: funtoo/x86-64bit/amd64-k10/hello_world:initial found
    └── initialize/3 ⇒ succeeded 2019-04-25 19:15:17

5f5d3531-3525-415d-bf2a-28b92edc3cee
└── start/1 ⇒ started 2019-04-25 19:15:17 ⧖ 4.420s
    ├── info/2 2019-04-25 19:15:18
    │   └── msg: hello_world : stoic_germain created
    ├── info/3 2019-04-25 19:15:18
    │   └── log_file: /home/jeff/Workspace/kantoo-devkit.git/logs/hello_world/x86-64bit-amd64-k10-hello_world-19-04-25-15:…
    ├── info/4 2019-04-25 19:15:18
    │   └── msg: hello_world : sha256:dda04cb3cd committed
    ├── info/5 2019-04-25 19:15:19
    │   └── msg: hello_python_from_env : objective_villani created
    ├── info/6 2019-04-25 19:15:19
    │   └── log_file: /home/jeff/Workspace/kantoo-devkit.git/logs/hello_world/x86-64bit-amd64-k10-hello_python_from_env-19…
    ├── info/7 2019-04-25 19:15:19
    │   └── msg: hello_python_from_env : sha256:6232728915 committed
    ├── info/8 2019-04-25 19:15:20
    │   └── msg: hello_python_from_arg : trusting_cray created
    ├── info/9 2019-04-25 19:15:20
    │   └── log_file: /home/jeff/Workspace/kantoo-devkit.git/logs/hello_world/x86-64bit-amd64-k10-hello_python_from_arg-19…
    ├── info/10 2019-04-25 19:15:20
    │   └── msg: hello_python_from_arg : sha256:975af3ade3 committed
    ├── info/11 2019-04-25 19:15:21
    │   └── msg: hello_python_from_explicit_env : priceless_franklin created
    ├── info/12 2019-04-25 19:15:21
    │   └── log_file: /home/jeff/Workspace/kantoo-devkit.git/logs/hello_world/x86-64bit-amd64-k10-hello_python_from_explic…
    ├── info/13 2019-04-25 19:15:21
    │   └── msg: hello_python_from_explicit_env : sha2
```
