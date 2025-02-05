# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import sys

import yaml

sys.path.insert(0, os.path.abspath("../../server"))
sys.path.insert(0, os.path.abspath("../../client"))
scripts_client = "../../client/lomas_client"
scripts_server = "../../server/lomas_server"
if scripts_client not in sys.path:
    sys.path.append(os.path.abspath(scripts_client))
if scripts_server not in sys.path:
    sys.path.append(os.path.abspath(scripts_server))


# -- Project information -----------------------------------------------------

project = "Lomas"
copyright = "2024, DSCC"
author = "DSCC"

# The full version, including alpha/beta/rc tags
release = "0.0.1"


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.viewcode",
    "sphinx.ext.napoleon",
    "nbsphinx",
    "myst_parser",
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = []


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "sphinx_rtd_theme"

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]

# The name of an image file (relative to this directory)
# to place at the top of the sidebar.
html_logo = "_static/logo.png"

# get the environment variable build_all_docs and pages_root
build_all_docs = os.environ.get("build_all_docs")
pages_root = os.environ.get("pages_root", "")

# if not there, we dont call this
if build_all_docs is not None:
    # we get the current language and version
    current_language = os.environ.get("current_language")
    current_version = os.environ.get("current_version")

    # we set the html_context wit current language and version
    # and empty languages and versions for now
    html_context = {
        "current_language": current_language,
        "languages": [],
        "current_version": current_version,
        "versions": [],
    }

    # and we append all versions and languages accordingly
    # we treat the master branch as stable
    if current_version == "stable":
        html_context["languages"].append(["en", pages_root])

    if current_language == "en":
        html_context["versions"].append(["stable", pages_root])

    # and loop over all other versions from our yaml file
    # to set versions and languages
    with open("../versions.yaml", "r") as yaml_file:
        docs = yaml.safe_load(yaml_file)

    if current_version != "stable":
        for language in docs[current_version].get("languages", []):
            html_context["languages"].append([language, pages_root + "/" + current_version + "/" + language])

    for version, details in docs.items():
        if version != "stable":
            html_context["versions"].append([version, pages_root + "/" + version + "/" + current_language])
