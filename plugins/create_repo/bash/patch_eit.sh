#!/usr/bin/env sh

sed -e 's:python2.7:python:g' -i /usr/bin/eit
eselect python set python3.6
