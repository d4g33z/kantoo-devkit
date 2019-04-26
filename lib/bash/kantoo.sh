#!/usr/bin/env sh
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
    rm root/funtoo.sh
}

install_distcc() {
    emerge distcc
    cd usr/lib/distcc/bin
    rm c++ g++ gcc cc
    cat > ${CHOST}-wrapper << EOF
#!/bin/bash
exec /usr/lib/distcc/bin/${CHOST}-g\${0:$[-2]} "\$@"
EOF
    ln -s ${CHOST}-wrapper cc
    ln -s ${CHOST}-wrapper gcc
    ln -s ${CHOST}-wrapper g++
    ln -s ${CHOST}-wrapper c++

    distcc-config --set-hosts "${DISTCCD_HOSTS}"
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

removeimages() {
    docker rmi $(docker images --filter "dangling=true" -q --no-trunc)
}


patch_eit() {
    wget https://patch-diff.githubusercontent.com/raw/Sabayon/entropy/pull/70.patch -O /tmp/sabayon-patch
    cd /usr/lib/entropy
    git apply /tmp/sabayon-patch
    cd -

    sed -e 's:python2.7:python3:g' -i /usr/bin/eit
    eselect python set python3.6
}


rebuild_entropy_database() {
    if [ ! -e /var/lib/entropy/client/database/${ENTROPY_ARCH}/equo.db ]; then
        echo "=== rebuilding the entropy database ==="
        equo rescue generate <<EOF
Yes
Yes
Yes
EOF
    fi

    echo "=== registering all portage installed packages ==="
    equo rescue spmsync
}

sync_or_create_local_repo() {
    if [ -d "/entropy/artifacts/standard" ]; then
      echo "=== Repository already exists, syncronizing ==="
      eit unlock ${REPOSITORY_NAME} || true
      eit pull --quick ${REPOSITORY_NAME} || true
    else
      echo "=== Repository is empty, intializing ==="
      echo "Yes" | eit init --quick ${REPOSITORY_NAME}
    fi
}

inject_portage_packages() {
    mkdir -p ${TMP_PKGDIR}
    rsync -a ${PKGDIR} ${TMP_PKGDIR}

    built_pkgs=$(find ${TMP_PKGDIR} -name "*.tbz2" | xargs)

    echo "=== Injecting packages ==="
    #if [ ! -z ${built_pkgs} ]; then
        eit unlock ${REPOSITORY_NAME}
        eit inject --quick ${built_pkgs} || { echo "ouch unable to inject"; }
    #fi
}

push_to_local_repo() {
    echo "=== Pushing built packages locally ==="
    eit push --quick --force
}


install_equo() {
    #REMOVE the ._cfg_client.conf files as we supply one
    find /etc -iname '._cfg_*' -exec rm {} \;

    emerge --usepkg equo
    #edit /etc/entropy/client.conf
    #create /etc/entropy/repositories.conf.d/entropy_kantoo.org

    #use these command to regenerate the list of all packages installed by portage
    #see https://www.funtoo.org/Entropy
    equo rescue generate <<EOF
Yes
Yes
Yes
EOF
    equo rescue spmsync
    equo update
}

equo_upgrade() {
    equo update --force
    equo upgrade
}

set_up_container_ssh() {
    echo "PermitRootLogin yes" >> /etc/ssh/sshd_config
    /usr/bin/ssh-keygen -A
    /usr/sbin/sshd -f /etc/ssh/sshd_config
}


configure_stage4() {
    ################################################################################
    #Set Up Mount Points
    sed -i "s/\/dev\/sda1.*/\/dev\/mmcblk0p1 \/boot vfat defaults 0 2/" ${SYSROOT}/etc/fstab
    sed -i "s/\/dev\/sda2.*//" ${SYSROOT}/etc/fstab
    sed -i "s/\/dev\/sda3.*/\/dev\/mmcblk0p2 \/ ext4  defaults 0 1/" ${SYSROOT}/etc/fstab
    sed -i "s/\#\/dev\/cdrom.*//" ${SYSROOT}/etc/fstab

    ################################################################################
    # Set Up Root Password
    sed -i "s|root\:\*|root\:$(openssl passwd -1 "${ROOT_PASSWD}")|" $SYSROOT/etc/shadow

    ################################################################################
    # Set Up SSH root Access
    echo "PermitRootLogin yes" >> ${SYSROOT}/etc/ssh/sshd_config

    ################################################################################
    # Set Up Software Clock
    mkdir -p ${SYSROOT}/lib/rc/cache
    touch ${SYSROOT}/lib/rc/cache/shutdowntime

    ################################################################################
    # Enable Serial Console Access
    sed -i "s/s0:.*/s0:12345:respawn:\/sbin\/agetty -L 115200 ttyAMA0 vt100/" ${SYSROOT}/etc/inittab

    ################################################################################
    # Link to Accelerated Video Libraries
    if [ ${ENTROPY_ARCH} = armv7l ]; then
        echo "LDPATH=\"/opt/vc/lib\"" > ${SYSROOT}/etc/env.d/99vc
    fi

    ################################################################################
    # Set hostname
    sed -i "s/hostname=\"localhost\"/hostname=\"${HOST_NAME}\"/" ${SYSROOT}/etc/conf.d/hostname
}

install_firmware() {
    if [ ! -d ${RPI_FIRMWARE}/firmware ]; then
        git clone --depth=1 git://github.com/raspberrypi/firmware/ ${RPI_FIRMWARE}/firmware
    fi

    #sysroot_update_firmware_repos

    cp ${RPI_FIRMWARE}/firmware/boot/{bootcode.bin,fixup*.dat,start*.elf} ${SYSROOT}/boot
    cp -r ${RPI_FIRMWARE}/firmware/hardfp/opt ${SYSROOT}/

    if [ ! -d ${RPI_FIRMWARE}/firmware-nonfree ]; then
        git clone --depth=1 https://github.com/RPi-Distro/firmware-nonfree ${RPI_FIRMWARE}/firmware-nonfree
    fi
    git --git-dir=${RPI_FIRMWARE}/firmware-nonfree/.git --work-tree=${RPI_FIRMWARE}/firmware-nonfree pull origin
    mkdir -p ${SYSROOT}/lib/firmware/brcm
    cp -r ${RPI_FIRMWARE}/firmware-nonfree/brcm/brcmfmac43430-sdio.{bin,txt} ${SYSROOT}/lib/firmware/brcm
    cp -r ${RPI_FIRMWARE}/firmware-nonfree/brcm/brcmfmac43455-sdio.{bin,txt,clm_blob} ${SYSROOT}/lib/firmware/brcm
}

install_kernel() {
    mkdir -p ${SYSROOT}/boot/overlays
    cp -r ${RPI_FIRMWARE}/firmware/boot ${SYSROOT}/
    cp ${RPI_FIRMWARE}/firmware/boot/overlays/*.dtb* ${SYSROOT}/boot/overlays
    cp ${RPI_FIRMWARE}/firmware/boot/overlays/README ${SYSROOT}/boot/overlays
    cp ${RPI_FIRMWARE}/firmware/boot/kernel7.img  ${SYSROOT}/boot
    mkdir -p ${SYSROOT}/lib/modules
    cp -r ${RPI_FIRMWARE}/firmware/modules/* ${SYSROOT}/lib/modules

    #what is this?
    rm ${SYSROOT}/boot/kernel.img

    cat > ${SYSROOT}/boot/config.txt << EOF
#serial console raspi3
#never use this!
#enable_uart=1
#instead disable the bluetooth modem and remap gpio pins
dtoverlay=pi3-disable-bt
EOF

    cat > ${SYSROOT}/boot/cmdline.txt << EOF
dwc_otg.lpm_enable=0 console=tty1 console=ttyAMA0,115200 root=/dev/mmcblk0p2 rootfstype=ext4 elevator=deadline fsck.repair=yes rootwait
EOF
}

export_fs(){

    rm /.dockerenv
    sed -i -e 's/rc_sys="docker"/#rc_sys=""/g' etc/rc.conf
    find /etc -iname '._cfg*' -exec rm {} \;
    tar chf /entropy/stage4s/stage4.tar --anchored --exclude=/portage --exclude=/entropy --exclude=/dev/* --exclude=/sys/* --exclude=/proc/* --exclude=/boot/* --exclude=/var/lib/entropy/client/packages --exclude /var/git/meta-repo --exclude /root/.ssh /

    tar chf /entropy/stage4s/boot.tar /boot/
}
