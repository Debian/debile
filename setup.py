from debile import __appname__, __version__
from setuptools import setup


long_description = ""

setup(
    name=__appname__,
    version=__version__,
    scripts=[],
    packages=[
        'debile',
        'debile.slave',
        'debile.master',
        'debile.utils.dud',
    ],
    author="Paul Tagliamonte",
    author_email="tag@pault.ag",
    long_description=long_description,
    description='FOO BAR BAZ BAR FOO',
    license="Expat",
    url="http://debile.debian.net/",
    platforms=['any'],
    entry_points={
        'console_scripts': [
            'debile-server-init = debile.master.cli:init',
            'debile-incoming = debile.master.cli:process_incoming',
        ],
    }
)
