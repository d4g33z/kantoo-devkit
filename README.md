# Kantoo Devkit 0.3-r1 #

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
>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
Creating container of funtoo/x86-64bit/amd64-k10/stage4:initial to run install_equo on.
brave_driscoll : sha256:49660d62df859a3ca3bc7603544eec711b20a68a888e7625e29cecd74e283220 committed
>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
Creating container of funtoo/x86-64bit/amd64-k10/stage4:install_equo to run unmask_equo_pkgs on.
nifty_edison : sha256:24f94a6e242eeb1fa58d3a5696b0bd9b6fb8d4784f8de3a8387bd6fd5ffa7b34 committed
>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
Creating container of funtoo/x86-64bit/amd64-k10/stage4:unmask_equo_pkgs to run equo_upgrade on.
laughing_vaughan : sha256:79396daeeaf03299dd3b6cbfd3895fe8d73ee1831ba42a21ad8fbad4a5fd3f0e committed
>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
Creating container of funtoo/x86-64bit/amd64-k10/stage4:equo_upgrade to run install_equo_packages on.
competent_mahavira : sha256:9f2bd92a74ce30351f04014f90552210b1db32786892724f114e73a1971c87b4 committed
>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
Creating container of funtoo/x86-64bit/amd64-k10/stage4:install_equo_packages to run config_services on.
condescending_napier : sha256:771e8645c27e461356bd6d4ec5d3fe07afb30582f2986dbfed5a18df007584fa committed
>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
Creating container of funtoo/x86-64bit/amd64-k10/stage4:config_services to run config_system on.
loving_nightingale : sha256:7f8db2568d2fe06933763b2cd2bab53ab7e59bd54102a53f69216b9d8659d9ec committed
>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
Creating container of funtoo/x86-64bit/amd64-k10/stage4:config_system to run install_firmware on.
admiring_franklin : sha256:6a2e4dad288773eb3cf1940260b468ba6b00baba923039ed97f592c596302bbf committed
>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
Creating container of funtoo/x86-64bit/amd64-k10/stage4:install_firmware to run install_kernel on.
frosty_lamport : sha256:344834f6a06e1f7cc900fe34d117f549f3c390de2c717c890668ae6a1a77f13b committed
>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
Creating container of funtoo/x86-64bit/amd64-k10/stage4:install_kernel to run export_fs on.
admiring_babbage : sha256:41c6b74042d3daf9e260131486b15581fe4e575ba160d260124bde02445907f2 committed
>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
Creating container of funtoo/x86-64bit/amd64-k10/stage4:export_fs to run export_profiles on.
```

```commandline
(env3.6) # ls sab_workspace/stage4s/
boot.tar  stage4.tar
```

```commandline
(env3.6) #  ls -lsrth logs
total 4.1M
132K -rw-r--r-- 1 jeff jeff 130K Apr 22 15:59 x86-64bit-amd64-k10-emerge_world-19-04-22-15:59:41.txt
924K -rw-r--r-- 1 jeff jeff 921K Apr 22 16:08 x86-64bit-amd64-k10-install_portage_pkgs-19-04-22-16:08:47.txt
4.0K -rw-r--r-- 1 jeff jeff  613 Apr 22 16:09 x86-64bit-amd64-k10-patch_eit-19-04-22-16:09:05.txt
 16K -rw-r--r-- 1 jeff jeff  13K Apr 22 16:10 x86-64bit-amd64-k10-rebuild_entropy_database-19-04-22-16:10:57.txt
1.1M -rw-r--r-- 1 jeff jeff 1.1M Apr 22 16:11 x86-64bit-amd64-k10-sync_or_create_local_repo-19-04-22-16:11:20.txt
1.1M -rw-r--r-- 1 jeff jeff 1.1M Apr 22 16:35 x86-64bit-amd64-k10-sync_or_create_local_repo-19-04-22-16:35:18.txt
264K -rw-r--r-- 1 jeff jeff 261K Apr 22 17:01 x86-64bit-amd64-k10-inject_pkgdir-19-04-22-17:01:23.txt
364K -rw-r--r-- 1 jeff jeff 361K Apr 22 17:04 x86-64bit-amd64-k10-push-19-04-22-17:04:26.txt
 16K -rw-r--r-- 1 jeff jeff  15K Apr 22 18:59 x86-64bit-amd64-k10-install_equo-19-04-22-18:59:21.txt
4.0K -rw-r--r-- 1 jeff jeff  666 Apr 22 18:59 x86-64bit-amd64-k10-unmask_equo_pkgs-19-04-22-18:59:26.txt
4.0K -rw-r--r-- 1 jeff jeff 2.7K Apr 22 18:59 x86-64bit-amd64-k10-equo_upgrade-19-04-22-18:59:30.txt
116K -rw-r--r-- 1 jeff jeff 114K Apr 22 19:00 x86-64bit-amd64-k10-install_equo_packages-19-04-22-19:00:56.txt
4.0K -rw-r--r-- 1 jeff jeff  418 Apr 22 19:01 x86-64bit-amd64-k10-config_services-19-04-22-19:01:04.txt
   0 -rw-r--r-- 1 jeff jeff    0 Apr 22 19:01 x86-64bit-amd64-k10-config_system-19-04-22-19:01:06.txt
4.0K -rw-r--r-- 1 jeff jeff   20 Apr 22 19:01 x86-64bit-amd64-k10-install_firmware-19-04-22-19:01:07.txt
   0 -rw-r--r-- 1 jeff jeff    0 Apr 22 19:01 x86-64bit-amd64-k10-install_kernel-19-04-22-19:01:11.txt
4.0K -rw-r--r-- 1 jeff jeff  340 Apr 22 19:01 x86-64bit-amd64-k10-export_fs-19-04-22-19:01:30.txt
   0 -rw-r--r-- 1 jeff jeff    0 Apr 22 19:01 x86-64bit-amd64-k10-export_profiles-19-04-22-19:01:40.txt

```

