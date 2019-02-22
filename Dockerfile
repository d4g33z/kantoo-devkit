# This Dockerfile creates a funtoo stage3 container image. By default it
# creates a stage3 generic 64bit image. It utilizes a multi-stage build and requires
# docker-17.05.0 or later. It fetches a daily snapshot from the official
# sources and verifies its checksum as well as its gpg signature.

# As gpg keyservers sometimes are unreliable, we use multiple gpg server pools
# to fetch the signing key.

# we are going to use alpine as our bootstrap container
ARG BOOTSTRAP
FROM ${BOOTSTRAP:-alpine:3.7} as builder

WORKDIR /funtoo

# here are all the arguments about arch/subarch ... defined
ARG ARCH=x86-64bit
ARG SUBARCH=amd64-k10
ARG DIST="https://build.funtoo.org/1.3-release-std"
ARG FILENAME="stage3-latest.tar.xz"
ARG BDFL_KEY="E986E8EE"
ARG BDFL_FP="E8EE"
ARG SIGNING_KEYS="11FD00FD 683A2F8A BEA87CD2 EEE54A43 62DD6D47 6B365A89"

RUN echo "Building Funtoo Container image for ${ARCH} ${SUBARCH} fetching from ${DIST}" \
 && sleep 3 \
 && apk --no-cache add gnupg tar wget xz \
 && STAGE3="${DIST}/${ARCH}/${SUBARCH}/${FILENAME}" \
 && wget -nv "${STAGE3}" "${STAGE3}.gpg" "${STAGE3}.hash.txt" \
 && gpg --list-keys \
 && echo "standard-resolver" >> ~/.gnupg/dirmngr.conf \
 && echo "honor-http-proxy" >> ~/.gnupg/dirmngr.conf \
 && echo "disable-ipv6" >> ~/.gnupg/dirmngr.conf \
 && gpg --keyserver hkp://pool.sks-keyservers.net --recv-keys ${BDFL_KEY} ${SIGNING_KEYS} \
 && gpg --list-keys --fingerprint | grep ${BDFL_FP} | tr -d '[:space:]' | awk 'BEGIN { FS = "=" } ; { print $1 ":6:" }' | gpg --import-ownertrust \
 && gpg --verify ${FILENAME}.gpg ${FILENAME} \
 && echo "Hash value from hash file:" \
 && cat ${FILENAME}.hash.txt \
 && echo "Hash value computed:" \
 && sha256sum ${FILENAME} \
 && awk '{print $2 "  stage3-latest.tar.xz"}' ${FILENAME}.hash.txt | sha256sum -c - \
 && tar xpf ${FILENAME} --xattrs --numeric-owner \
 && sed -i -e 's/#rc_sys=""/rc_sys="docker"/g' etc/rc.conf \
 && echo 'UTC' > etc/timezone \
 && rm stage3-latest.tar.xz* \
 && rm -rf usr/src/linux-debian-sources-* \
 && rm -rf lib/modules/* \
 && rm -rf boot/*

FROM scratch

WORKDIR /
COPY --from=builder /funtoo/ /
CMD ["/bin/bash"]
