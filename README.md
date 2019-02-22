# Kantoo Devkit #

This is a collection of tools modeled on the [Sabayon Devkit](https://github.com/Sabayon/devkit).

The idea is to fascilitate the creation of 'Kantoo stage4s:' Funtoo stage3s that have been augmented to allow
installation of binary packages via the Entropy package manager.

Docker containers are used to create images of each choosen subarch, profile and mixins, with a predefined list of 
packages to build with portage and package with entropy. 


