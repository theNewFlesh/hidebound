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

1. Install `docker-desktop <https://docs.docker.com/desktop/>`__
2. ``docker pull thenewflesh/hidebound:latest``

Docker For Developers
~~~~~~~~~~~~~~~~~~~~~

1. Install `docker-desktop <https://docs.docker.com/desktop/>`__
2. Ensure docker-desktop has at least 4 GB of memory allocated to it.
3. ``git clone git@github.com:theNewFlesh/hidebound.git``
4. ``cd hidebound``
5. ``chmod +x bin/hidebound``
6. ``bin/hidebound start``

The service should take a few minutes to start up.

Run ``bin/hidebound --help`` for more help on the command line tool.

Overview
========

Hidebound is an ephemeral database and asset framework used for
generating, validating and exporting assets to various data stores.
Hidebound enables developers to ingest arbitrary sets of files and
output them as content and generated metadata, which has validated
according to specifications they define.

Assets are placed into an ingress directory, typically reserved for
Hidebound projects, and then processed by Hidebound. Hidebound extracts
metadata from the files and directories that make each asset according
to their name, location and file properties. This data comprises the
entirety of Hidebound’s database at any one time.

Dataflow
========

|image0|

Data begins as files on disk. Hidebound creates a JSON-compatible dict
from their name traits and file traits and then constructs an internal
database table from them, one dict per row. All the rows are then
aggregated by asset, and converted into JSON blobs. Those blobs are then
validated according to their respective specifications. Files from valid
assets are then copied or moved into Hidebound’s content directory,
according to their same directory structure and naming. Metadata is
written to JSON files inside Hidebound’s metadata directory. Each file’s
metadata is written as a JSON file in /hidebound/metadata/file, and each
asset’s metadata (the aggregate of its file metadata) is written to
/hidebound/metadata/asset. From their exporters, can export the valid
asset data and its accompanying metadata to various locations, like an
AWS S3 bucket.

Workflow
========

The acronynm to remember for workflows is **CRUDES**: create, read,
update, delete, export and search. Those operations constitue the main
functionality that Hidebound supports.

*Create Asset*
~~~~~~~~~~~~~~

For example, an asset could be an image sequence, such as a directory
full of PNG files, all of which have a frame number, have 3 (RGB)
channels, and are 1024 pixels wide by 1024 pixels tall. Let’s call the
specification for this type of asset “spec001”. We create an image
sequence of a cat running, and we move it into the Hidebound projects
directory.

*Update*
~~~~~~~~

|image1|

We call the update function via Hidebound’s web app. Hidebound creates a
new database based upon the recursive listing of all the files within
said directory. This database is displayed to us as a table, with one
file per row. If we choose to group by asset in the app, the table will
display one asset per row. Hidebound extracts metadata from each
filename (not any directory name) as well as from the file itself. That
metadata is called file_traits. Using only information derived from
filename and file traits, Hidebound determines which files are grouped
together as a single asset and the specification of that asset. Asset
traits are then derived from this set of files (one or more). Finally,
Hidebound validates each asset according to its determined
specification. All of this data is displayed as a table within the web
app. Importantly, all of the errors in filenames, file traits and asset
traits are included.

*Review Graph*
~~~~~~~~~~~~~~

|image2| If we click on the graph tab, we are greeted by a hierarchical
graph of all our assets in our project directory. Our asset is red,
meaning it’s invalid. Valid asset’s are green, and all other files and
directories, including parent directories, are cyan.

*Diagnose and Repair*
~~~~~~~~~~~~~~~~~~~~~

We flip back to the data tab. Using table within it, we search (via SQL)
for our asset within Hidebound’s freshly created database. We see an
error in one of the filenames, conveniently displayed in red text. The
descriptor in one orf our filenames has capital letters in it. This
violates Hidebound’s naming convention, and so we get an error. We go
and rename the file appropriately and call update again. Our asset is
now valid. The filenames are correct and we can see in the height and
width columns, that it’s 1024 by 1024 and the channels column says it
has three.

*Create*
~~~~~~~~

Next we click the create button. For each valid asset, Hidebound
generates file and asset metadata as JSON files within the
hidebound/metadata directory. Hidebound also copies or moves, depending
on the config write mode, valid files and directories into the
hidebound/content directory. Hidebound/content and hidebound/metadata
are both staging directories used for generating a valid ephemeral
database. We now have a hidebound directory that looks like this
(unmentioned assets are collapsed behind the ellipses):

.. code:: shell

   /tmp/hidebound
   ├── hidebound_config.yaml
   │
   ├── specifications
   │   └── specifications.py
   │
   ├── data
   │   ...
   │   └── p-cat001
   │       └── spec001
   │           └── p-cat001_s-spec001_d-running-cat_v001
   │               ├── p-cat001_s-spec001_d-running-cat_v001_c0000-0005_f0001.png
   │               ├── p-cat001_s-spec001_d-running-cat_v001_c0000-0005_f0002.png
   │               └── p-cat001_s-spec001_d-running-cat_v001_c0000-0005_f0003.png
   │
   ├── metadata
       ├── asset
       │   ...
       │   └── a9f3727c-cb9b-4eb1-bc84-a6bc3b756cc5.json
       │
       └── file
           ...
           ├── 279873a2-bfd0-4757-abf2-7dc4f771f992.json
           ├── e50160ae-8678-40b3-b766-ee8311b1f0c9.json
           └── ea95bd79-cb8f-4262-8489-efe734c5f65c.json

*Export*
~~~~~~~~

The hidebound directories contain only valid assets. Thus, we are now
free to export this data to various data stores, such as AWS S3,
MongoDB, and Girder. Exporters are are defined within the exporters
subpackage. They expect a populated hidebound directory and use the
files and metadata therein to export hidebound data. Exporter
configurations are stored in the hidebound config, under the “exporters”
key. Currently supported exporters include, disk, s3 and girder. Below
we can see the results of an export to Girder in the Girder web app.

|image3|

*Delete*
~~~~~~~~

Once this export process is complete, we may click the delete button.
Hidebound deletes the hidebound/content and hidebound/metdata
directories and all their contents. If write_mode in the Hidebound
configuration is set to “copy”, then this step will merely delete data
created by Hidebound. If it is set to “move”, then Hidebound will
presumably delete, the only existing copy of out asset data on the host
machine. The delete stage in combination with the removal of assets from
the ingress directory is what makes Hidebound’s database ephemeral.

.. _workflow-1:

*Workflow*
~~~~~~~~~~

``/api/workflow`` is a API endpoint that initializes a database a with a
given config, and then calls each method from a given list. For
instance, if you send this data to ``/api/workflow``:

``{config={...}, workflow=['update', 'create', 'export', 'delete']}``

A database instance will be created with the given config, and then that
instance will call its update, create, export and delete methods, in
that order.

Naming Convention
=================

Hidebound is a highly opinionated framework that relies upon a strict
but composable naming convention in order to extract metadata from
filenames. All files and directories that are part of assets must
conform to a naming convention defined within that asset’s
specification.

In an over-simplified sense; sentences are constructions of words.
Syntax concerns how each word is formed, grammar concerns how to form
words into a sentence, and semantics concerns what each word means.
Similarly, filenames can be thought of as crude sentences. They are made
of several words (ie fields). These words have distinct semantics (as
determines by field indicators). Each word is constructed according to a
syntax (ie indicator + token). All words are joined together by spaces
(ie underscores) in a particular order as determined by grammar (as
defined in each specification).

*Syntax*
~~~~~~~~

-  Names consist of a series of fields, each separated by a single
   underscore “_”, also called a field separator.
-  Periods, “.”, are the exception to this, as it indicates file
   extension.
-  Legal characters include and only include:

================ ========== =========================
Name             Characters Use
================ ========== =========================
Underscore       \_         only for field separation
Period           .          only for file extensions
Lowercase letter a to z     everything
Number           0 to 9     everything
Hyphen           -          token separator
================ ========== =========================

Fields are comprised of two main parts:

=============== ===================================================
Name            Use
=============== ===================================================
Field indicator determines metadata key
Field token     a set of 1+ characters that define the field’s data
=============== ===================================================

Environment Variables
~~~~~~~~~~~~~~~~~~~~~

If ``HIDEBOUND_CONFIG_FILEPATH`` is set, Hidebound will ignore all other
environment variables and read the given filepath in as a yaml or json
config file.

+---------------------------+---+--------------------------------------+
| Variable                  | F | Portion                              |
|                           | o |                                      |
|                           | r |                                      |
|                           | m |                                      |
|                           | a |                                      |
|                           | t |                                      |
+===========================+===+======================================+
| HIDEBOUND_CONFIG_FILEPATH | s | Entire Hidebound config file         |
|                           | t |                                      |
|                           | r |                                      |
+---------------------------+---+--------------------------------------+
| HI                        | s | ingress_directory parameter of       |
| DEBOUND_INGRESS_DIRECTORY | t | config                               |
|                           | r |                                      |
+---------------------------+---+--------------------------------------+
| HI                        | s | staging_directory parameter of       |
| DEBOUND_STAGING_DIRECTORY | t | config                               |
|                           | r |                                      |
+---------------------------+---+--------------------------------------+
| HIDEBOUND_INCLUDE_REGEX   | s | include_regex parameter of config    |
|                           | t |                                      |
|                           | r |                                      |
+---------------------------+---+--------------------------------------+
| HIDEBOUND_EXCLUDE_REGEX   | s | exclude_regex parameter of config    |
|                           | t |                                      |
|                           | r |                                      |
+---------------------------+---+--------------------------------------+
| HIDEBOUND_WRITE_MODE      | s | write_mode parameter of config       |
|                           | t |                                      |
|                           | r |                                      |
+---------------------------+---+--------------------------------------+
| HIDEBOUND_REDACT_REGEX    | s | redact_regex parameter of config     |
|                           | t |                                      |
|                           | r |                                      |
+---------------------------+---+--------------------------------------+
| HIDEBOUND_REDACT_HASH     | s | redact_hash parameter of config      |
|                           | t |                                      |
|                           | r |                                      |
+---------------------------+---+--------------------------------------+
| HIDEBOUND_WORKFLOW        | y | workflow paramater of config         |
|                           | a |                                      |
|                           | m |                                      |
|                           | l |                                      |
+---------------------------+---+--------------------------------------+
| HIDE                      | y | specification_files section of       |
| BOUND_SPECIFICATION_FILES | a | config                               |
|                           | m |                                      |
|                           | l |                                      |
+---------------------------+---+--------------------------------------+
| HI                        | s | dask cluster type                    |
| DEBOUND_DASK_CLUSTER_TYPE | t |                                      |
|                           | r |                                      |
+---------------------------+---+--------------------------------------+
| HIDE                      | i | number of partions for each          |
| BOUND_DASK_NUM_PARTITIONS | n | dataframe                            |
|                           | t |                                      |
+---------------------------+---+--------------------------------------+
| HIDEBOU                   | i | number of workers on local cluster   |
| ND_DASK_LOCAL_NUM_WORKERS | n |                                      |
|                           | t |                                      |
+---------------------------+---+--------------------------------------+
| HIDEBOUND_DASK            | i | number of threads per worker on      |
| _LOCAL_THREADS_PER_WORKER | n | local cluster                        |
|                           | t |                                      |
+---------------------------+---+--------------------------------------+
| HIDEBOUND_D               | s | use multiprocessing for local        |
| ASK_LOCAL_MULTIPROCESSING | t | cluster                              |
|                           | r |                                      |
+---------------------------+---+--------------------------------------+
| HIDEB                     | s | gateway server address               |
| OUND_DASK_GATEWAY_ADDRESS | t |                                      |
|                           | r |                                      |
+---------------------------+---+--------------------------------------+
| HIDEBOUND_D               | s | scheduler proxy server address       |
| ASK_GATEWAY_PROXY_ADDRESS | t |                                      |
|                           | r |                                      |
+---------------------------+---+--------------------------------------+
| HIDEBOUND_DA              | s | gateway server address, as           |
| SK_GATEWAY_PUBLIC_ADDRESS | t | accessible from a web browser        |
|                           | r |                                      |
+---------------------------+---+--------------------------------------+
| HIDEBOU                   | s | authentication type                  |
| ND_DASK_GATEWAY_AUTH_TYPE | t |                                      |
|                           | r |                                      |
+---------------------------+---+--------------------------------------+
| HIDEBOU                   | s | api token                            |
| ND_DASK_GATEWAY_API_TOKEN | t |                                      |
|                           | r |                                      |
+---------------------------+---+--------------------------------------+
| HIDEBOUND_DAS             | y | list of dask gateway cluster options |
| K_GATEWAY_CLUSTER_OPTIONS | a |                                      |
|                           | m |                                      |
|                           | l |                                      |
+---------------------------+---+--------------------------------------+
| HIDEBOUND_DASK_           | s | whether to shudown cluster upon      |
| GATEWAY_SHUTDOWN_ON_CLOSE | t | close                                |
|                           | r |                                      |
+---------------------------+---+--------------------------------------+
| HIDEBOUND_EXPORTERS       | y | exporters section of config          |
|                           | a |                                      |
|                           | m |                                      |
|                           | l |                                      |
+---------------------------+---+--------------------------------------+
| HIDEBOUND_WEBHOOKS        | y | webhooks section of config           |
|                           | a |                                      |
|                           | m |                                      |
|                           | l |                                      |
+---------------------------+---+--------------------------------------+

--------------

Here is a full example config with comments:

.. code:: yaml

   ingress_directory: /mnt/storage/projects                                 # where hb looks for assets
   staging_directory: /mnt/storage/hidebound                                # hb staging directory
   include_regex: ""                                                        # include files that match
   exclude_regex: "\\.DS_Store"                                             # exclude files that match
   write_mode: copy                                                         # copy files from root to staging
                                                                            # options: copy, move
   redact_regex: "(_key|_id|_token|url)$"                                   # regex matched config keys to redact
   redact_hash: true                                                        # hash redacted values
   workflow:                                                                # workflow steps
     - delete                                                               # clear staging directory
     - update                                                               # create database from ingress files
     - create                                                               # stage valid assets
     - export                                                               # export assets in staging
   specification_files:                                                     # list of spec files
     - /mnt/storage/specs/image_specs.py
     - /mnt/storage/specs/video_specs.py
   dask:
     cluster_type: local                                                    # Dask cluster type
                                                                            # options: local, gateway
     num_partitions: 16                                                     # number of partions for each dataframe
     local_num_workers: 16                                                  # number of workers on local cluster
     local_threads_per_worker: 1                                            # number of threads per worker on local cluster
     local_multiprocessing: true                                            # use multiprocessing for local cluster
     gateway_address: http://proxy-public/services/dask-gateway             # gateway server address
     gateway_proxy_address: gateway://traefik-daskhub-dask-gateway.core:80  # scheduler proxy server address
     gateway_public_address: https://dask-gateway/services/dask-gateway/    # gateway server address, as accessible from a web browser
     gateway_auth_type: jupyterhub                                          # authentication type
     gateway_api_token: token123                                            # api token
     gateway_cluster_options:                                               # list of dask gateway options
       - field: image                                                       # option field
         label: image                                                       # option label
         option_type: select                                                # options: bool, float, int, mapping, select, string
         default: "some-image:latest"                                       # option default value
         options:                                                           # list of choices if option_type is select
           - "some-image:latest"                                            # choice 1
           - "some-image:0.1.2"                                             # choice 2
     gateway_shutdown_on_close: true                                        # whether to shudown cluster upon close
   exporters:                                                               # dict of exporter configs
     - name: disk                                                           # export to disk
       target_directory: /mnt/storage/archive                               # target location
       metadata_types:                                                      # options: asset, file, asset-chunk, file-chunk
         - asset                                                            # only asset and file metadata
         - file
       dask:                                                                # dask settings override
         num_workers: 8
         local_threads_per_worker: 2
     - name: s3                                                             # export to s3
       access_key: ABCDEFGHIJKLMNOPQRST                                     # aws access key
       secret_key: abcdefghijklmnopqrstuvwxyz1234567890abcd                 # aws secret key
       bucket: prod-data                                                    # s3 bucket
       region: us-west-2                                                    # bucket region
       metadata_types:                                                      # options: asset, file, asset-chunk, file-chunk
         - asset                                                            # drop file metadata
         - asset-chunk
         - file-chunk
       dask:                                                                # dask settings override
         cluster_type: gateway
         num_workers: 64
     - name: girder                                                         # export to girder
       api_key: eyS0nj9qPC5E7yK5l7nhGVPqDOBKPdA3EC60Rs9h                    # girder api key
       root_id: 5ed735c8d8dd6242642406e5                                    # root resource id
       root_type: collection                                                # root resource type
       host: http://prod.girder.com                                         # girder server url
       port: 8180                                                           # girder server port
       metadata_types:                                                      # options: asset, file
         - asset                                                            # only asset metadata
       dask:                                                                # dask settings override
         num_workers: 10
       dask:                                                                # dask settings override
         num_workers: 10
   webhooks:                                                                # call these after export
     - url: https://hooks.slack.com/services/ABCDEFGHI/JKLMNO               # slack URL
       method: post                                                         # post this to slack
       timeout: 60                                                          # timeout after 60 seconds
       # params: {}                                                         # params to post (NA here)
       # json: {}                                                           # json to post (NA here)
       data:                                                                # data to post
         channel: "#hidebound"                                              # slack data
         text: export complete                                              # slack data
         username: hidebound                                                # slack data
       headers:                                                             # request headers
         Content-type: application/json

Specification
=============

Asset specifications are defined in python using the base classes found
in specification_base.py. The base classes are defined using the
schematics framework. Hidebound generates a single JSON blob of metadata
for each file of an asset, and then combines blob into a single blob
with a list values per key. Thus every class member defined with
schematics is encapsulated with ListType.

Example asset
~~~~~~~~~~~~~

Suppose we have an image sequence asset that we wish to define a
specificqtion for. Our image sequences consist of a directory containing
1 or 3 channel png with frame numbers in the filename.

.. code:: shell

   projects
       └── cat001
           └── raw001
               └── p-cat001_s-raw001_d-calico-jumping_v001
                   ├── p-cat001_s-raw001_d-calico-jumping_v001_f0001.png
                   ├── p-cat001_s-raw001_d-calico-jumping_v001_f0002.png
                   └── p-cat001_s-raw001_d-calico-jumping_v001_f0003.png

Example specification
~~~~~~~~~~~~~~~~~~~~~

We would write the following specification for such an asset.

.. code:: python

   from schematics.types import IntType, ListType, StringType
   import hidebound.core.validators as vd  # validates traits
   import hidebound.core.traits as tr      # gets properties of files and file names
   from hidebound.core.specification_base import SequenceSpecificationBase

   class Raw001(SequenceSpecificationBase):
       asset_name_fields = [  # naming convention for asset directory
           'project', 'specification', 'descriptor', 'version'
       ]
       filename_fields = [    # naming convention for asset files
           'project', 'specification', 'descriptor', 'version', 'frame',
           'extension'
       ]
       height = ListType(IntType(), required=True)  # heights of png images
       width = ListType(IntType(), required=True)   # widths of png images
       frame = ListType(
           IntType(),
           required=True,
           validators=[vd.is_frame]  # validates that frame is between 0 and 9999
       )
       channels = ListType(
           IntType(),
           required=True,
           validators=[lambda x: vd.is_in(x, [1, 3])]  # validates that png is 1 or 3 channel
       )
       extension = ListType(
           StringType(),
           required=True,
           validators=[
               vd.is_extension,
               lambda x: vd.is_eq(x, 'png')  # validates that image is png
           ]
       )
       file_traits = dict(
           width=tr.get_image_width,            # retrieves image width from file
           height=tr.get_image_height,          # retrieves image height from file
           channels=tr.get_num_image_channels,  # retrieves image channel number from file
       )

.. |image0| image:: resources/screenshots/data_flow.png
.. |image1| image:: resources/screenshots/update.png
.. |image2| image:: resources/screenshots/graph.png
.. |image3| image:: resources/screenshots/girder.png
