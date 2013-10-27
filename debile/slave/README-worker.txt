How to plug a new static analyzer ?

= Files =

Create:
commands/yourstaticanalyzer.py
runners/yourstaticanalyzer.py
wrappers/yourstaticanalyzer.py

Do not hesitate to start from another program.
Example:
* cppcheck works on sources.
* lintian works on deb files.
* findbugs works on unpacked deb files.

= Hack on files =

== runners/yourstaticanalyzer.py ==

The work to run your analyzer is done in this file.

Call your program with the right arguments and retrieve out, err and ret
arguments.

Once the results are parsed, they are processed by the runners to check if the
job should be marked as failed or not.


== wrappers/yourstaticanalyzer.py ==

The function takes as argument the output produced by the static analyzer.
It can be a standard output, XML file, etc

The goal of this function is to extract the relevant information from the input
to generate a Issue object.
This object is created from the following information:
* ID
* location
* severity
* message
* notes (optionnal)
* trace (optionnal)


== commands/yourstaticanalyzer.py ==

Provide the run() method to be called by the debile slave engine.
(usually trivial)


= Write tests =

Tests should be provided for any worker.
tests/test_findbugs.py is a good example.

They can be started with the command:
$ nosetests


= Plug the analyzer to the debile slave =

Add your analyzer in commands/__init__.py
