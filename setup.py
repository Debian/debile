from debile import __version__
from setuptools import setup


"""
Dear world:

     I'd like to say I'm sorry to anyone reading this. The amount of
     scotch I had on hand wasn't enough to let me finish the debian
     packaging hack I was working through (was working fine until I hit
     some nonsense). As a result, this file will suffer.

     Trust me, this is much better than what I had before.
               -- PRT
"""

flavors = {
    "setup.py": ("debile", [
        'debile', 'debile.utils'
    ], {
        'console_scripts': [
            'debile-remote = debile.utils.cli:main',
        ],
    }),  # Default config
    "setup.slave.py": ("debile.slave", [
        'debile.slave',
        'debile.slave.commands',
        'debile.slave.runners',
        'debile.slave.wrappers',
    ], {
        'console_scripts': [
            'debile-slave = debile.slave.cli:daemon',
        ],
    }),  # Slave config
    "setup.master.py": ("debile.master", [
        'debile.master'
    ], {
        'console_scripts': [
            'debile-master = debile.master.cli:server',
            'debile-master-init = debile.master.cli:init',
            'debile-incoming = debile.master.cli:process_incoming',
        ],
    }),  # Master config
}

appname, packages, scripts = flavors[__file__]

long_description = ""

setup(
    name=appname,
    version=__version__,
    scripts=[],
    packages=packages,
    author="Paul Tagliamonte",
    author_email="tag@pault.ag",
    long_description=long_description,
    description='FOO BAR BAZ BAR FOO',
    license="Expat",
    url="http://debile.debian.net/",
    platforms=['any'],
    entry_points=scripts,
)
