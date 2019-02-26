# Kantoo Devkit #

This is a collection of tools modeled on the [Sabayon Devkit](https://github.com/Sabayon/devkit).

The idea is to fascilitate the creation of 'Kantoo stage4s:' Funtoo stage3s that have been augmented to allow
installation of binary packages via the Entropy package manager.

Docker containers are used to create images of each choosen subarch, profile and mixins, with a predefined list of 
packages to build with portage and package with entropy.

The `dockerdriver.py` is used to operate on a container, attaching volumes and environment variables as needed, and 
executing a series of bash or python scripts to modify it. The steps can be atomized by commit intermediate containers 
to images.

## How To Use it ##

Clone this repo. Run the script to get some uninformative output. Use `virtualenv` to isolate everything nicely. 

```commandline
# cd kantoo-devkit
# virtualenv -p /usr/bin/python3.6 env3.6
# source env3.6/bin/activate
# pip install -r requirements.txt
# vim configs/create_repo.hjson
# python dockerdriver.py
# cat last_logs.txt
```

Hello, world!

