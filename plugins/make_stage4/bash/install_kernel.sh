#!/usr/bin/env sh

mkdir -p ${SYSROOT}/boot/overlays
cp -r ${RPI_FIRMWARE}/firmware/boot ${SYSROOT}/
cp ${RPI_FIRMWARE}/firmware/boot/overlays/*.dtb* ${SYSROOT}/boot/overlays
cp ${RPI_FIRMWARE}/firmware/boot/overlays/README ${SYSROOT}/boot/overlays
cp ${RPI_FIRMWARE}/firmware/boot/kernel7.img  ${SYSROOT}/boot
mkdir -p ${SYSROOT}/lib/modules
cp -r ${RPI_FIRMWARE}/firmware/modules/* ${SYSROOT}/lib/modules

#what is this?
rm ${SYSROOT}/boot/kernel.img
