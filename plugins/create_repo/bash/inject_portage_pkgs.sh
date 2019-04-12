#!/usr/bin/env sh

wget https://patch-diff.githubusercontent.com/raw/Sabayon/entropy/pull/70.patch -O /tmp/sayabyon-patch
cd /usr/lib/entropy
git apply /tmp/sabayon-patch
cd -

mkdir -p ${TMP_PKGDIR}
rsync -a ${PKGDIR} ${TMP_PKGDIR}

built_pkgs=$(find ${TMP_PKGDIR} -name "*.tbz2" | xargs)

echo "=== Injecting packages ==="
#if [ ! -z ${built_pkgs} ]; then
eit unlock ${REPOSITORY_NAME}
eit inject --quick ${built_pkgs} || { echo "ouch unable to inject"; }

#else
#    echo "no built portage packages found"
#fi

# we just want to inject a handful of packages, not everything on system
#echo "=== commiting all installed packages locally ==="
#eit commit --quick
#echo "=== Pushing built packages locally ==="
#eit push --quick --force