from debile import __appname__, __version__
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
    "setup.py": ([
        'debile', 'debile.utils'
    ], {}),  # Default config
    "setup.slave.py": ([
        'debile.slave'
    ], {}),  # Slave config
    "setup.master.py": (['debile.master'], {
        'console_scripts': [
            'debile-server-init = debile.master.cli:init',
            'debile-incoming = debile.master.cli:process_incoming',
            'debile-import = debile.master.cli:import_db',
        ],
    }),  # Master config
}

packages, scripts = flavors[__file__]

long_description = ""

setup(
    name=__appname__,
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
