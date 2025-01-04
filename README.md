# Edbov Data
A project that gathers information about Edbovägen and stores it in a SQLite
database.
For information on how to run and use the project see the project documentation.

## Configuration
The project is configured in a INI configuration file that shall be pointed to
by the environment variable "ED_CONFIG".

## Usage

### Run the script
The script can be run from the root folder with either of:

``` shell
python -m edbov_data
```

or:

``` shell
python -m edbov_data.<module>
```

or:

``` shell
./edbov_data-runner.py
```

## Debug
Use the DAP debugger. Emacs is set up in the file .dir-locals.el.
Start the script with:

``` shell
python -Xfrozen_modules=off -m debugpy --listen 5678 --wait-for-client -m edbov_data.<module>
```

In Emacs:

``` emacs-lisp
M x dap-breakpoint-add
M x dap-debug
M x dap-hydra
```

## Documentation
To build the documentation:

``` shell
cd docs
make html
```

The html documentation can then be viewed by browsing to:
edbov_data/docs/_build/html/index.html

## Tests
To run tests:

``` shell
pytest
```

## Install the script locally
Use pipx to install the script in a virtual environment:

``` shell
sudo pacman -S python-pipx
```

Then:

``` shell
cd edbov_data
pipx install .
```

To upgrade to a new version:

``` shell
cd edbov_data
pipx upgrade edbov_data
```

When installed the entry points to the scripts, i.e. the way to run
the scripts, are defined by the entry_points in setup.py. In the
example the script "script_2.py" would be run with "name-for-script-2".

## Install on another machine
Build a wheel package:

``` shell
python -m build
```

Copy the file: dist/edbov_data-<x.y.z>-py3-none-any.whl to the machine and install it with:

``` shell
pipx install ./edbov_data-<x.y.z>-py3-none-any.whl --force
```
