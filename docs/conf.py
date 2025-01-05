import os
import sys

# -- Path setup --------------------------------------------------------------

# Add the parent directory of 'edbo_data' to sys.path
sys.path.insert(0, os.path.abspath("../.."))

# -- Project information -----------------------------------------------------

project = "Edbo Data"
author = "Mats Gustafsson"
release = "0.0.1"

# -- General configuration ---------------------------------------------------

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.napoleon",
    "sphinx_autodoc_typehints",
]

autosummary_generate = True

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# -- Options for HTML output -------------------------------------------------

html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]
