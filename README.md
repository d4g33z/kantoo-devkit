# Kantoo Devkit #

This is a collection of tools modeled on the [Sabayon Devkit](https://github.com/Sabayon/devkit).

The idea is to fascilitate the creation of 'Kantoo stage4s:' Funtoo stage3s that have been augmented to allow
installation of binary packages via the Entropy package manager.

Docker containers are used to create images of each choosen subarch, profile and mixins, with a predefined list of 
packages to build with portage and package with entropy. 

## How To Use it ##

It's a python script. Run it to get some uninformative output. Please note that the`DOCKERFILE` variable comes set to `None.` Set it to `/entropy/bin/create_repo.sh` to run the process.

```commandline
# python createrepo.py
Found docker image funtoo/x86-64bit/amd64-k10:stage3
Repository: testing.kantoo.org
Repository Description: Funtoo on RPI3!
quirky_roentgen created
	make.conf: /tmp/tmpmvombigl
	create_repo.sh: /tmp/tmpgjw9lfsl
The Sabayon repository files are in /home/jeff/Workspace/kantoo-devkit.git/sab_workspace/entropy_artifacts
Now you can upload its content where you want

Here it is the repository file how will look like 
(if you plan to upload it to a webserver, modify the URI accordingly)

[testing.kantoo.org]
desc = Funtoo on RPI3!
repo=file:///home/jeff/Workspace/kantoo-devkit.git/sab_workspace/entropy_artifacts#bz2
enabled = true
pkg = file:///home/jeff/Workspace/kantoo-devkit.git/sab_workspace/entropy_artifacts

```

If everything worked, you have a directory containing the Entropy artifacts: everything needed to run a repository of Entropy packaged binaries that will install on Funtoo-1.3.
