Debile
======

Debile is a Debian build system. It's reduced, minimal and
purely implemented in modern Python. This allows folks to use debile
as a platform to aid with building debs, or running custom tooling
against debs or debian source packages.

Debile isn't useful for many "normal" situations, other tools, such as
sbuild, or pbuilder will do much better when used directly by simple shell
scripts. It's also not great as a buildd, check out wanna-build if you're
interested in a big professional setup.


Fedmsg Topics
=============

All topics are under:

    org.anized.{dev,sage,prod}.debile
    `-- source
    |   |-- accept
    |   |-- reject
    |
    `-- binary
    |   |-- accept
    |   |-- reject
    |
    `-- job
    |   |-- start
    |   |-- complete
    |   |-- abort
    |
    `-- result
        |-- receive

Run tests
=========

$ apt-get install python-nose
$ nosetests
