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

if [ ${CONFIG_SERIAL} =  1 ]; then
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
else
    touch ${SYSROOT}/boot/config.txt
    cat > ${SYSROOT}/boot/cmdline.txt << EOF
dwc_otg.lpm_enable=0 console=tty1 root=/dev/mmcblk0p2 rootfstype=ext4 elevator=deadline fsck.repair=yes rootwait
EOF
fi