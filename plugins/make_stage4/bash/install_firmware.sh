#!/usr/bin/env sh
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
