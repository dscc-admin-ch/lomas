"""
This file is largely inspired from this blog post.

https://www.codingwiththomas.com/blog/my-sphinx-best-practice-for-a-multiversion-documentation-in-different-languages

The general idea is to use a versions.yaml file which indicates
from which branches to build the documentation pages.

Arguments (version, language, etc.) are passed to sphinx's conf.py
as environment variables.

The Sphinx templates are configured such that they render the correct
hmtl to create links between versions.
"""

import argparse
import os
import re
import shutil
import subprocess
from pathlib import Path

import yaml


def git_ref_exists(git_ref: str) -> bool:
    """
    Checks whether a git ref exists on the "origin" remote.

    Args:
        git_ref (str): The git ref to check.

    Returns:
        bool: True if the reference is found, False otherwise.
    """
    # check if reference is a tag
    tag_pattern = r"^v\d+\.\d+\.\d+$"
    if re.match(tag_pattern, git_ref):
        refs = "tags"
    else:
        refs = "heads"
    try:
        result = subprocess.run(
            f"git ls-remote --{refs} origin {git_ref}",
            shell=True,
            text=True,
            capture_output=True,
            check=False,
        )
        return len(result.stdout.strip()) > 0
    except subprocess.CalledProcessError as e:
        print(f"Error checking ref: {e}")
        return False


def copy_notebook_to_source(path: str) -> None:
    """
    Copy notebook from '../client/' or '../server/' to './source/'.

    Args:
      notebook_path (str): Path to notebook to copy
    """
    notebook_path = Path(path)
    destination_path = path.replace("../client/", "./source/").replace("../server/", "./source/")

    if not notebook_path.exists():
        print(f"Notebook not found at {notebook_path}, skipping copy.")
        return

    destination = Path(destination_path)
    shutil.copy2(notebook_path, destination)


def get_current_branch() -> str:
    """
    Get the name of the current git branch.

    Returns:
        str: The name of the branch currently checked out.
    """
    result = subprocess.run(
        "git branch --show-current", stdout=subprocess.PIPE, shell=True, text=True, check=False
    )
    return result.stdout.strip()


def set_env_vars(version: str, language: str) -> None:
    """
    Set environment variables used by Sphinx/conf.py for the documentation build.

    Args:
        version (str): The version of the documentation.
        language (str): The language code for the documentation.
    """
    os.environ["current_version"] = version
    os.environ["current_language"] = language
    os.environ["SPHINXOPTS"] = f"-D language='{language}'"


def replace_index_with_under_construction() -> None:
    """
    Replace the main index.rst with an "under construction" version.

    The original index.rst is renamed to index.rst.old.
    """
    index = Path("source/index.rst")
    under_construction = Path("source/index_under_construction.rst")
    old_index = Path("source/index.rst.old")

    if index.exists():
        index.rename(old_index)
    if under_construction.exists():
        under_construction.rename(index)


def checkout_tag(tag: str) -> None:
    """
    Fetch and checkout a specific git tag or branch.

    Args:
        tag (str): The git tag or branch to checkout.
    """
    subprocess.run(f"git fetch origin {tag}:{tag}", shell=True, check=False)
    subprocess.run(f"git checkout {tag}", shell=True, check=False)


def restore_conf_from_branch(branch: str) -> None:
    """
    Restore `conf.py` and `versions.yaml` from a specific branch.

    Args:
        branch (str): The branch to restore configuration files from.
    """
    subprocess.run(f"git checkout {branch} -- source/conf.py", shell=True, check=False)
    subprocess.run(f"git checkout {branch} -- versions.yaml", shell=True, check=False)


def copy_sources() -> None:
    """Copy static files, notebooks, and other documentation sources into the Sphinx source folder."""
    subprocess.run("mkdir -p ./source/_static", shell=True, check=False)
    subprocess.run("cp ../images/lomas_logo_txt.png ./source/_static/logo.png", shell=True, check=False)
    subprocess.run("cp ../images/poster.pdf ./source/_static/poster.pdf", shell=True, check=False)
    subprocess.run("cp ../CONTRIBUTING.md ./source/CONTRIBUTING.md", shell=True, check=False)
    subprocess.run("cp ../server/CONTRIBUTING.md ./source/CONTRIBUTING_SERVER.md", shell=True, check=False)

    subprocess.run("mkdir -p ./source/notebooks", shell=True, check=False)
    notebook_paths = [
        "../client/notebooks/Demo_Client_Notebook.ipynb",
        "../client/notebooks/Demo_Client_Notebook_Smartnoise-SQL.ipynb",
        "../client/notebooks/Demo_Client_Notebook_DiffPrivLib.ipynb",
        # "../client/notebooks/Demo_Client_Notebook_Smartnoise-Synth.ipynb",
        "../client/notebooks/Demo_Client_Notebook_OpenDP_Polars.ipynb",
    ]
    for nb_path in notebook_paths:
        copy_notebook_to_source(nb_path)


def generate_sphinx_api_doc() -> None:
    """Generate Sphinx API documentation using `sphinx-apidoc` for core, client, and server modules."""
    subprocess.run(
        "sphinx-apidoc -o ./source ../core/lomas_core/ --tocfile core_modules", shell=True, check=False
    )
    subprocess.run(
        "sphinx-apidoc -o ./source ../client/lomas_client/ --tocfile client_modules",
        shell=True,
        check=False,
    )
    subprocess.run(
        "sphinx-apidoc -o ./source ../server/lomas_server/ --tocfile server_modules",
        shell=True,
        check=False,
    )


def build_doc(version: str, language: str, tag: str, local: bool = False) -> None:
    """
    Builds the documention for the given tag (git ref).

    The versions.yaml and conf.py are always taken
    from the "calling" branch (ie. the one that is
    checked out at the time of calling this function)

    The build is skipped if the version does not exist.

    Args:
        version (str): Version to display
        language (str): Language (for formatting)
        tag (str): git ref
        local (bool): whether to build on the local branch only
    """
    start_branch = get_current_branch()
    set_env_vars(version, language)

    if not local and not git_ref_exists(tag):
        replace_index_with_under_construction()
    else:
        if not local:
            checkout_tag(tag)
            restore_conf_from_branch(start_branch)

        copy_sources()
        generate_sphinx_api_doc()

    # Build HTML files
    subprocess.run("sphinx-build -M html source build", shell=True, check=False)

    # Make things as they were before
    if not local:
        checkout_tag(tag)
        restore_conf_from_branch(start_branch)
        copy_sources()
        generate_sphinx_api_doc()


# a move dir method because we run multiple builds and bring the html folders to a
# location which we then push to github pages
def move_dir(src: str, dst: str) -> None:
    """
    Moves the src directory and its contents to dst.

    Args:
        src (str): source directory
        dst (str): destination directory
    """
    subprocess.run(["mkdir", "-p", dst], check=False)
    subprocess.run("mv " + src + "* " + dst, shell=True, check=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-l", "--local", action="store_true", help="local build on current branch")

    args = parser.parse_args()

    if args.local:
        # Set arguments to conf.py
        # to separate a single local build from all builds we have a flag, see conf.py
        os.environ["build_all_docs"] = str(False)
        os.environ["pages_root"] = "./build/html"
        build_doc("stable", "en", "", True)

    else:
        # Set arguments to conf.py
        # to separate a single local build from all builds we have a flag, see conf.py
        os.environ["build_all_docs"] = str(True)
        os.environ["pages_root"] = "https://dscc-admin-ch.github.io/lomas-docs"

        # manually build the master branch
        build_doc("stable", "en", "master")
        move_dir("./build/html/", "../pages/")

        # reading the yaml file
        with open("versions.yaml", encoding="utf-8") as yaml_file:
            docs = yaml.safe_load(yaml_file)

        # and looping over all values to call our build with version, language and its tag
        for version, details in docs.items():
            if version == "stable":
                continue
            tag = details.get("tag", "")
            for language in ["en"]:
                build_doc(version, language, tag)
                move_dir("./build/html/", "../pages/" + version + "/" + language + "/")
