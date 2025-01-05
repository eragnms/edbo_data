edbo_data Package Documentation
===============================

Overview
--------

The `edbo_data` package provides tools to fetch different types of data that
are relevant for my house at Edbovägen.

Netatmo authentication
----------------------

Create an app by logging in at  `Netatmo <https://dev.netatmo.com/apidocumentation>`_. When
clicking at your user name you can choose the option "My Apps". Fill in the fields: app name,
description, data protection officer name, data protection offices email. Under Token Generator
pick scopes and then generate new tokens.
Create a file: ~/.netatmo.credentials and add to it the information from the Netatmo app::

  {
  "CLIENT_ID": "",
  "CLIENT_SECRET": "",
  "REFRESH_TOKEN": ""
  }

Then set the permissions on the file::

  chmod u=rw,g=r,o=r .netatmo.credentials

Modules
-------

.. automodule:: edbo_data.fetching.fetch_smhi
    :members:
    :undoc-members:
    :show-inheritance:

.. automodule:: edbo_data.fetching.fetch_netatmo
    :members:
    :undoc-members:
    :show-inheritance:
