#!/usr/bin/env sh
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

distcc-config --set-hosts "${DISTCCD_HOSTS}"
