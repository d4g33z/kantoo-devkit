#!/usr/bin/env sh

wget https://patch-diff.githubusercontent.com/raw/Sabayon/entropy/pull/70.patch -O /tmp/sabayon-patch
cd /usr/lib/entropy
git apply /tmp/sabayon-patch
cd -

sed -e 's:python2.7:python:g' -i /usr/bin/eit
eselect python set python3.6
