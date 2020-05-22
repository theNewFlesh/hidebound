Introduction
============

A local database service for converting directories of arbitrary files
into validated assets and derived metadata for export to databases like
AWS S3 and MongoDB.

See `documentation <https://thenewflesh.github.io/hidebound/>`__ for
details.

Installation
============

Python
~~~~~~

``pip install hidebound``

Docker
~~~~~~

1. Install
   `docker <https://docs.docker.com/v17.09/engine/installation>`__
2. Install
   `docker-machine <https://docs.docker.com/machine/install-machine>`__
   (if running on macOS or Windows)
3. ``docker pull thenewflesh/hidebound:latest``

Docker For Developers
~~~~~~~~~~~~~~~~~~~~~

1. Install
   `docker <https://docs.docker.com/v17.09/engine/installation>`__
2. Install
   `docker-machine <https://docs.docker.com/machine/install-machine>`__
   (if running on macOS or Windows)
3. Ensure docker-machine has at least 4 GB of memory allocated to it.
4. ``git clone git@github.com:theNewFlesh/hidebound.git``
5. ``cd hidebound``
6. ``chmod +x bin/hidebound``
7. ``bin/hidebound start``

The service should take a few minutes to start up.

Run ``bin/hidebound --help`` for more help on the command line tool.

Overview
========

Hidebound is a local, dockerized ; database, asset framework, asset
validation and display service. Hidebound is not a competitor to
databases like MongoDB, Amazon Web Service's (AWS) S3, PostGres, etc.
Hidebound enables developers to ingest arbitrary sets of files and
output them as validated assets and metadata for consumption by
databases like AWS S3 and MongoDB.

Hidebound is framework for validating, and extracting metadata data from
files and directories according, to user defined specifications. Assets
are placed into a root directory (typically one reserved for Hidebound
projects) and then discovered, validated, extracted, and copied or moved
by Hidebound.

Workflow
========

Create *Asset*
~~~~~~~~~~~~~~

For example, an asset could be an image sequence, such as a directory
full of PNG files, all of which have a frame number, have 3 (RGB)
channels, and are 1024 pixels wide and 1024 pixels tall. Let's call the
specification for this type of asset "raw001". We create an image
sequence, and we move it into the Hidebound projects directory.

*Update*
~~~~~~~~

We call the update function via Hidebound's web client. Hidebound
creates a new database based upon the recursive listing of all the files
within said directory. This database is displayed to us as a table, with
one file per row. If we choose to group by asset in the client, it will
be, oneasset per row. Hidebound extracts metadata from each filename
(not any directory name) as well as from the file itself. That metadata
is called file\_traits. Using only information derived from filename and
file traits, Hidebound determines which files are grouped together as a
single asset and the specification of that asset. Asset traits are then
derived from this set (1 or more) of files. Finally, Hidebound validates
each asset according to its determined specification. All of this data
is displayed as a table within the web client. Importantly, all of the
errors in filenames, file traits and asset traits are included.

Review *Graph*
~~~~~~~~~~~~~~

If we click on the graph tab, we are greeted by a hierarchical graph of
all our assets in our project directory. Our asset is red, meaning it's
invalid. Valid asset's are green, and all other files and directories,
including parent directories, are cyan.

Diagnose and *Repair*
~~~~~~~~~~~~~~~~~~~~~

We flip back to the data tab. Using table within it, we search (via SQL)
for our asset within Hidebound's freshly created database. We see an
error in one of the filenames. Our descriptor has capital letters in it.
This violates Hidebound's naming convention, and so we get an error. We
go and rename the file appropriately and call update again. Our asset is
not valid. We can say in the height and width columns, its 1024 by 1024
and the channels column says it has three.

*Create*
~~~~~~~~

Next we click the create button. For each valid asset, Hidebound
generates file and asset metadata as JSON files within the
hidebound/metadata directory. Hidebound also copies or moves (depending
on config) valid files and directories into the hidebound/data
directory. Thus we now have a hidebound directory that looks like this:

::

        /hidebound
            |-- data
            |   |-- p-proj001_s-raw001_d-running-cat_v001
            |       |-- p-proj001_s-raw001_d-running-cat_v001_c000-0005_f0001.png
            |       |-- p-proj001_s-raw001_d-running-cat_v001_c000-0005_f0002.png
            |       |-- p-proj001_s-raw001_d-running-cat_v001_c000-0005_f0003.png
            |
            |-- metadata
                |-- file
                |   |-- fab4219b-b4a2-4910-976f-e06ab7e64bd9.json
                |   |-- asgdhjhg-b4a2-8765-7896-jaskldj78211.json
                |   |-- akjsd879-jahs-1862-871h-891723hdsasd.json
                |
                |-- asset
                    |-- kajsaks3-askl-1233-mnas-alskhdu12632.json

*Upload*
~~~~~~~~

This directory contains only valid assets and their assosciated
metadata. We are now free to upload this data to various databases, such
as AWS S3 and MongoDB. I recommend a service that continually parses
this directory and uploads whatever it finds. Currently, such a process
is considered to be beyond the scope of Hidebound's intent.

*Delete*
~~~~~~~~

Once this upload process is complete, we may click the delete button.
Hidebound deletes the hidebound/data and hidebound/metdata directories
and all their contents. If write\_mode in the Hidebound configuration is
set to "copy", then this step will merely delete data created by
Hidebound. If it is set to "move", then it Hidebound will presumably
delete, the only existing copy of out asset data on the host machine.

Naming Convention
=================

Hidebound is a highly opionated framework that relies on a strict but
composable naming convention in order to extract metadata from
filenames. All files and directories that are part of assets must
conform to a naming convention defined within that asset's
sepcification.

In an over-simplified sense; sentences are constructions of words.
Syntax concerns how each word is formed, grammar concerns how to
construct words into a sentence, and semantics concerns what each word
means. Similarly, filenames can be thought of as crude sentences. They
are made of several words (ie fields). These words have distinct
semantics (as determines by field indicators). Each word is constructed
according to a syntax (ie indicator + token). All words are joined
together by spaces (ie underscores) in a particular order as detrmined
by grammar (as defined in specifications).

*Syntax*
--------

-  Names consist of a series of field, each separated by a single
   underscore “\_”, also called a field separator.
-  Period, ".", is the exception to this, as it indicates file
   extension.
-  Legal characters include and only include:

   -  Underscores --> only for field separation
   -  Periods --> only for file extensions
   -  Lowercase letters --> a to z
   -  Numbers --> 0 to 9
   -  Hyphens --> -

Fields are comprised of two main parts: - The field indicator -->
determines metadata key - The field token --> a set of characters, 1 or
more in length, that define the field's data

--------------

**Example Diagrams**
~~~~~~~~~~~~~~~~~~~~

In our example filename:
``p-proj001_s-raw001_d-running-cat_v001_c000-005_f0003.png`` the
metadata will be:

::

    {
        'project': 'proj001',
        'specification': 'spec001',
        'descriptor': 'running-cat',
        'version': 1,
        'coordinate': [0, 5],
        'frame': 3,
        'extension': 'png',
    }

The raw001 specification is derived from the second field of this
filename:

::

           field   field
       indicator   token
               | __|_
              | |    |
    p-proj001_s-raw001_d-running-cat_v001_c000-005_f0003.png
              |______|
                  |
                field

+--------------------+---------------------------+
| Part               | Value                     |
+====================+===========================+
| Field              | s-raw001                  |
+--------------------+---------------------------+
| Field indicator    | s-                        |
+--------------------+---------------------------+
| Field token        | raw001                    |
+--------------------+---------------------------+
| Derived metadata   | {specification: raw001}   |
+--------------------+---------------------------+

*Special Field Syntax*
~~~~~~~~~~~~~~~~~~~~~~

-  Projects begin with 3 or 4 letters followed by 1 or 3 numbers
-  Specifications begin with 3 or 4 letters followed by 3 numbers
-  Descriptors begin with a letter or number and may also contain
   hyphens
-  Descriptors may not begin with the words master, final or last
-  Versions are triple-padded with zeros and must be greater than 0
-  Coordinates may contain up to 3 triple-padded numbers, separated by
   hyphens
-  Coordinates are always evaluated in XYZ order
-  For example: ``c001-002-003`` produces ``{x: 1, y: 2, z: 3}``
-  Each element of a coordinate may be equal to or greater than zero
-  Frames are quadruple-padded and are greater than or equal to 0
-  Extensions may only contain upper and lower case letters a to z and
   numbers 0 to 9

*Semantics*
-----------

Hidebound is highly opionated, especially with regards to its semantics.
It contains exactly seven field types, as indicated by their field
indicators. They are:

+-----------------+-------------+
| Field           | Indicator   |
+=================+=============+
| project         | p-          |
+-----------------+-------------+
| specification   | s-          |
+-----------------+-------------+
| descriptor      | d-          |
+-----------------+-------------+
| version         | v           |
+-----------------+-------------+
| coordinate      | c           |
+-----------------+-------------+
| frame           | f           |
+-----------------+-------------+
| extension       | .           |
+-----------------+-------------+

*Grammar*
---------

The grammar is fairly simple: - All names must contain a specification
field - All specification must define a field order - All fields of a
name under that specification must occcur in its defined field order

Its is highly encouraged that fields be defined in the following order:

``project, specification, descriptor, version, coordinate, frame, extension``

The grammatical concept of field order here is one of rough
encapsulation: - Projects contain assets - Assets are grouped by
specification - A meaningful set of assets is grouped by a descriptor -
That set of assets consists of multiple version of the same content - A
single asset may broken into chunks, identified by 1, 2 or 3 coordinates
- Each chunk may consist of a series of files seperated by frame number
- An single file has an extension

*Encouraged Lexical Conventions*
--------------------------------

-  Specifications end with a triple padded number so that they may be
   explicitely version. You redefine an asset specification to something
   slightly different, by copying its specification class, adding one to
   its name and change the class attributes in some way. That way you
   always maintain backwards compatibility with legacy assets.
-  Descriptors are not a dumping ground for useless terms like wtf,
   junk, stuff, wip and test.
-  Descriptors should not specify information known at the asset
   specification level, such as the project name, the generic content of
   the asset (ie image, mask, png, etc).
-  Descriptors should not include information that can be known from the
   preceding tokens, such as version, frame or extension.
-  A descriptor should be applicable to every version of the asset it
   designates.
-  Use of hyphens in descriptors is encouraged.
-  When in doubt, hyphenate and put into the descriptor.

Project Structure
=================

Hidebound does not formally define a project structure. It merely
stipulates that asset must exist under some particular root directory.
Each asset specification does define a directory structure for the files
that make up that asset. Assets are divided into 3 types: file, sequence
and complex. File defines an asset that consists of a single file.
Sequence is defined to be a single directory containing one or more
files. Complex is for assets that consist of an arbitrarily complex
layout of directories and files.

However, the following project structure is recommended:

::

    project
        |-- asset-specification
            |-- descriptor
                |-- asset      # either a file or directory of files and directories
                    |- file

For Example
^^^^^^^^^^^

::

    p-cat001
        |-- s-raw001
            |-- d-tabby-playing
            |   |-- p-cat001_s-raw001_d-tabby-playing_v001
            |       |-- p-cat001_s-raw001_d-tabby-playing_v001_f0001.png
            |       |-- p-cat001_s-raw001_d-tabby-playing_v001_f0002.png
            |       |-- p-cat001_s-raw001_d-tabby-playing_v001_f0003.png
            |-- d-calico-jumping
                |-- p-cat001_s-raw001_d-calico-jumping_v001
                    |-- p-cat001_s-raw001_d-calico-jumping_v001_f0001.png
                    |-- p-cat001_s-raw001_d-calico-jumping_v001_f0002.png
                    |-- p-cat001_s-raw001_d-calico-jumping_v001_f0003.png
