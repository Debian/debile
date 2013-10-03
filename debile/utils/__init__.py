import sys
import shlex
import subprocess

def run_command(command):
    if not isinstance(command, list):
        command = shlex.split(command)
    try:
        pipe = subprocess.Popen(command,
                                shell=False,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
    except OSError:
        return (None, None, -1)
    (output, stderr) = pipe.communicate()
    return (output, stderr, pipe.returncode)
