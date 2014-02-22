# Create a Debile slave.
#
# VERSION   0.1
FROM        debian:experimental
MAINTAINER  Paul R. Tagliamonte <paultag@debian.org>
# OK. Enough about that. Let's take our pristine Debian image and
# add our key.

RUN apt-get update
RUN apt-get install -y curl
RUN curl http://debile.anized.org/key.asc | apt-key add -
# Right, now that we have our key,

RUN echo "deb http://debile.anized.org/archive/ rc-buggy main" > /etc/apt/sources.list.d/debile.list
# and our loving repo,

# Let's update
RUN apt-get update
# and install debile-slave
RUN apt-get install -y debile-slave

ADD slave.yaml /etc/debile/slave.yaml

USER Debian-debile-unpriv
CMD ["/usr/share/debile-slave/debile-slave-docker"]
