# This Dockerfile creates a funtoo stage3 container image. It fetches a daily snapshot from the official
# sources and verifies its checksum as well as its gpg signature.

ARG BOOTSTRAP
FROM ${BOOTSTRAP:-alpine:3.7} as builder

WORKDIR /kantoo

ARG ARCH
ARG SUBARCH
ARG DIST
ARG STAGE3_ARCHIVE

#see https://stackoverflow.com/questions/27931668/encoding-problems-when-running-an-app-in-docker-python-java-ruby-with-u
#RUN locale-gen en_US.UTF-8
ENV LANG en_US.UTF-8
ENV LANGUAGE en_US:en
ENV LC_ALL en_US.UTF-8

#downloaded and verified stage3 archive guaranteed to be present by Stalker
COPY stage3s/${ARCH}/${SUBARCH}/${STAGE3_ARCHIVE} .

COPY lib/bash/kantoo.sh root/kantoo.sh

RUN /bin/sh -c "source root/kantoo.sh && alpine_install"; \
    /bin/sh -c "source root/kantoo.sh && stage3_install"; \
    /bin/sh -c "source root/kantoo.sh && configure_system"; \
    /bin/sh -c "source root/kantoo.sh && cleanup";

FROM scratch

WORKDIR /
COPY --from=builder /kantoo/ /
CMD ["/bin/bash"]
