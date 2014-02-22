# Create a local-use Debile slave.
#
# VERSION   0.1
FROM        debile-slave-base
MAINTAINER  Paul R. Tagliamonte <paultag@debian.org>

ADD ursae.json /usr/share/dput-ng/profiles/
ADD slave.yaml /etc/debile/

RUN chown -R Debian-debile-unpriv:Debian-debile-unpriv /etc/debile/*
ADD config.tar.gz /tmp/config.tar.gz
RUN /usr/share/debile-slave/debile-slave-import /tmp/config.tar.gz
RUN rm /tmp/config.tar.gz

USER Debian-debile-unpriv
CMD ["debile-slave"]
