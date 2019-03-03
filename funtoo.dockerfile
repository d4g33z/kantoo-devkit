# This Dockerfile creates a funtoo stage3 container image. It fetches a daily snapshot from the official
# sources and verifies its checksum as well as its gpg signature.

# We are going to use alpine as our bootstrap container
ARG BOOTSTRAP
FROM ${BOOTSTRAP:-alpine:3.7} as builder

WORKDIR /funtoo

# here are all the arguments about arch/subarch ... defined
# set from createrepo.py
ARG ARCH
ARG SUBARCH
ARG DIST="https://build.funtoo.org/1.3-release-std"
ARG FILENAME="stage3-latest.tar.xz"

#see https://stackoverflow.com/questions/27931668/encoding-problems-when-running-an-app-in-docker-python-java-ruby-with-u
#RUN locale-gen en_US.UTF-8
ENV LANG en_US.UTF-8
ENV LANGUAGE en_US:en
ENV LC_ALL en_US.UTF-8

#copy if exists
#https://forums.docker.com/t/copy-only-if-file-exist/3781/2
COPY stage3s/${ARCH}/${SUBARCH}/stage3-*.tar.xz stage3-latest.tar.xz

COPY funtoo.sh root/funtoo.sh

RUN echo -e $UL$MAG"Building a Funtoo container image for ${ARCH} ${SUBARCH} fetching from ${DIST}"

RUN /bin/sh -c "source root/funtoo.sh && alpine_install"; \
    /bin/sh -c "source root/funtoo.sh && stage3_install"; \
    /bin/sh -c "source root/funtoo.sh && configure_system"; \
    /bin/sh -c "source root/funtoo.sh && cleanup";

FROM scratch

WORKDIR /
COPY --from=builder /funtoo/ /
CMD ["/bin/bash"]
