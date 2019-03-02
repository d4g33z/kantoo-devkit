#!/usr/bin/env bash
XX='\e[0m'
BO='\e[1m'
UL='\e[4m'

RED='\e[31m'
GRE='\e[32m'
MAG='\e[35m'
YEL='\e[33m'

alpine_install() {
    apk --no-cache add gnupg tar xz
}

stage3_install() {
    ################################################################################
    echo -e $UL$MAG"Install the Stage 3 Tarball"
    echo -e $XX

    STAGE3_URL="${DIST}/${ARCH}/${SUBARCH}/${FILENAME}"
    STAGE3_ARCHIVE="$(basename $STAGE3_URL)"
    STAGE3_GPG=${STAGE3_ARCHIVE}.gpg

    if [ ! -f ${STAGE3_ARCHIVE}  ]; then
        wget ${STAGE3_URL} -O ${STAGE3_ARCHIVE}
    fi
    wget ${STAGE3_URL}.gpg -O ${STAGE3_GPG}
    #check for drobbins trust
    if [ "$(gpg --list-public-keys | grep D3B948F82EE8B4020A0410789A658306E986E8EE -)" = "" ]; then
        gpg --recv-key E986E8EE
    fi
    #check for arm32 trust
    if [ "$(gpg --list-public-keys | grep 38E84AD53B01590BA6785E882A7B0B2EEEE54A43 -)" = "" ]; then
        gpg --recv-key EEE54A43
    fi
    if [ "$(gpg --trust-model always --verify ${STAGE3_GPG} ${STAGE3_ARCHIVE} 2>&1 | grep BAD)" != "" ]; then
        echo "gpg verification failed. Download a new stage 3 archive"
        return 1
    fi

    tar xpf ${STAGE3_ARCHIVE} --xattrs --numeric-owner #for docker containers

}

configure_system() {

sed -i -e 's/#rc_sys=""/rc_sys="docker"/g' etc/rc.conf
echo 'UTC' > etc/timezone

}

cleanup() {
rm stage3-latest.tar.xz*
rm -rf usr/src/linux-debian-sources-*
rm -rf lib/modules/*
rm -rf boot/*
}

install_distcc() {
    emerge distcc
    cd usr/lib/distcc/bin
    rm c++ g++ gcc cc
    cat > ${CHOST}-wrapper << EOF2
#!/bin/bash
exec /usr/lib/distcc/bin/${CHOST}-g\${0:$[-2]} "\$@"
EOF2
    ln -s ${CHOST}-wrapper cc
    ln -s ${CHOST}-wrapper gcc
    ln -s ${CHOST}-wrapper g++
    ln -s ${CHOST}-wrapper c++
}

# see https://stackoverflow.com/questions/34658836/docker-is-in-volume-in-use-but-there-arent-any-docker-containers
removecontainers() {
    docker stop $(docker ps -aq)
    docker rm $(docker ps -aq)
}

armaggedon() {
    removecontainers
    docker network prune -f
    docker rmi -f $(docker images --filter dangling=true -qa)
    docker volume rm $(docker volume ls --filter dangling=true -q)
    docker rmi -f $(docker images -qa)
}