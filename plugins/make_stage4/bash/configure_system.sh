#!/usr/bin/env sh
################################################################################
#Set Up Mount Points
sed -i "s/\/dev\/sda1.*/\/dev\/mmcblk0p1 \/boot vfat defaults 0 2/" ${SYSROOT}/etc/fstab
sed -i "s/\/dev\/sda2.*//" ${SYSROOT}/etc/fstab
sed -i "s/\/dev\/sda3.*/\/dev\/mmcblk0p2 \/ ext4  defaults 0 1/" ${SYSROOT}/etc/fstab
sed -i "s/\#\/dev\/cdrom.*//" ${SYSROOT}/etc/fstab

################################################################################
# Set Up Root Password
#sed -i "s|root\:\*|root\:${ROOT_PASSWD}|" $SYSROOT/etc/shadow
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
echo "LDPATH=\"/opt/vc/lib\"" > ${SYSROOT}/etc/env.d/99vc

