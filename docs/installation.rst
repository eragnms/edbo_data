Installation
============

Setup
-----

Add an environmental variable::

  ED_CONFIG: pointing to a configuration file

Setup authentication for Netatmo. Create an app by logging in at
`Netatmo <https://dev.netatmo.com/apidocumentation>`_. When
clicking at your user name you can choose the option "My Apps". Fill in the fields:
app name, description, data protection officer name, data protection offices email.
Under Token Generator pick scopes and then generate new tokens.
Create a file: ~/.netatmo.credentials and add to it the information from the Netatmo
app::

  {
  "CLIENT_ID": "",
  "CLIENT_SECRET": "",
  "REFRESH_TOKEN": ""
  }

Then set the permissions on the file::

  chmod u=rw,g=r,o=r .netatmo.credentials

Add the token for Tibber in an environment variable::

  TIBBER_TOKEN: <token>

For development
---------------

Clone the repository and do::

  cd edbo_data
  python -m venv venv
  source venv/bin/activate.fish
  pip install -r requirements.txt

Then test with::

  python -m edbo_data.edbo_data -h

For production
--------------

Requires the package python-pipx::

  sudo pacman -S python-pipx

With access to the Git repository
+++++++++++++++++++++++++++++

Clone the repository and do::

  cd edbo_data
  pipx install .

To upgrade to a new version::

  cd edbov_data
  pipx upgrade edbov_data

Without the Git repository
++++++++++++++++++++++++++

Build a wheel package::

  python -m build

Copy the file: dist/edbov_data-<x.y.z>-py3-none-any.whl to the machine and install it with::

  pipx install ./edbov_data-<x.y.z>-py3-none-any.whl --force
