"""
This file is largely inspired from this blog post
https://www.codingwiththomas.com/blog/my-sphinx-best-practice-for-a-multiversion-documentation-in-different-languages

The general idea is to use a versions.yaml file which indicates
from which branches to build the documentation pages.

Arguments (version, language, etc.) are passed to sphinx's conf.py
as environment variables.

The Sphinx templates are configured such that they render the correct
hmtl to create links between versions.
"""
import os
import subprocess
import yaml
import re

def git_ref_exists(git_ref: str) -> bool:
  """
  Checks whether a git ref exists on the "origin" remote.

  Args:
      git_ref (str): The git ref to check.

  Returns:
      bool: True if the reference is found, False otherwise.
  """
  #check if reference is a tag
  tag_pattern = r"^v\d+\.\d+\.\d+$"
  if re.match(tag_pattern, git_ref):
    refs = "tags"
  else:
    refs = "heads"
  try:
    result = subprocess.run(f"git ls-remote --{refs} origin {git_ref}",
                            shell=True, text=True,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE
    )

    if len(result.stdout.strip()) > 0:
      return True
    else:
      return False
  except subprocess.CalledProcessError as e:
    print(f"Error checking ref.")
    return False


def build_doc(version: str, 
              language: str, 
              tag: str,
              ):
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
  """
  start_branch_cmd = subprocess.run("git branch --show-current", stdout=subprocess.PIPE, shell=True, text=True)
  start_branch = start_branch_cmd.stdout.strip()

  # Set parameters for conf.py
  os.environ["current_version"] = version
  os.environ["current_language"] = language

  if not git_ref_exists(tag):
    # Replace index if tag does not exist
    subprocess.run("mv source/index.rst source/index.rst.old", shell=True)
    subprocess.run("mv source/index_under_construction.rst source/index.rst", shell=True)

  else:
    # Fetch and checkout branch to document
    subprocess.run(f"git fetch origin {tag}:{tag}", shell=True)
    subprocess.run(f"git checkout {tag}", shell=True)
    
    # Versions and conf.py always from calling branch
    subprocess.run(f"git checkout {start_branch} -- source/conf.py", shell=True)
    subprocess.run(f"git checkout {start_branch} -- versions.yaml", shell=True)
    
    # Copy relevant sources and generate code docs rsts.
    subprocess.run("mkdir -p ./source/_static", shell=True)
    subprocess.run("cp ../images/lomas_logo_txt.png ./source/_static/logo.png", shell=True)
    subprocess.run("cp ../images/poster.pdf ./source/_static/poster.pdf", shell=True)
    subprocess.run("cp ../CONTRIBUTING.md ./source/CONTRIBUTING.md", shell=True)
    subprocess.run("cp ../client/CONTRIBUTING.md ./source/CONTRIBUTING_CLIENT.md", shell=True)
    subprocess.run("cp ../server/CONTRIBUTING.md ./source/CONTRIBUTING_SERVER.md", shell=True)
    subprocess.run("sphinx-apidoc -o ./source ../client/lomas_client/ --tocfile client_modules", shell=True)
    subprocess.run("sphinx-apidoc -o ./source ../server/lomas_server/ --tocfile server_modules", shell=True)
    subprocess.run("mkdir -p ./source/notebooks", shell=True)
    subprocess.run("cp -r ../client/notebooks/Demo_Client_Notebook.ipynb ./source/notebooks/Demo_Client_Notebook.ipynb", shell=True)
    subprocess.run("cp -r ../client/notebooks/Demo_Client_Notebook_Smartnoise-SQL.ipynb ./source/notebooks/Demo_Client_Notebook_Smartnoise-SQL.ipynb", shell=True)
    subprocess.run("cp -r ../client/notebooks/Demo_Client_Notebook_DiffPrivLib.ipynb ./source/notebooks/Demo_Client_Notebook_DiffPrivLib.ipynb", shell=True)
    subprocess.run("cp -r ../client/notebooks/Demo_Client_Notebook_Smartnoise-Synth.ipynb ./source/notebooks/Demo_Client_Notebook_Smartnoise-Synth.ipynb", shell=True)
    subprocess.run("cp -r ../client/notebooks/s3_example_notebook.ipynb ./source/notebooks/s3_example_notebook.ipynb", shell=True)
    subprocess.run("cp -r ../server/notebooks/local_admin_notebook.ipynb ./source/notebooks/local_admin_notebook.ipynb", shell=True)
  

  # Build the html doc
  os.environ['SPHINXOPTS'] = "-D language='{}'".format(language)
  subprocess.run("make html", shell=True)

  # Make things as they were before
  if not git_ref_exists(tag):
    subprocess.run("git reset --hard && git clean -f -d", shell=True)
  else:
    # Go back to calling branch
    subprocess.run(f"git checkout {start_branch}", shell=True)

  return
    

# a move dir method because we run multiple builds and bring the html folders to a 
# location which we then push to github pages
def move_dir(src: str, dst: str) -> None:
  """
  Moves the src directory and its contents to dst.

  Args:
      src (str): source directory
      dst (str): destination directory
  """
  subprocess.run(["mkdir", "-p", dst])
  subprocess.run("mv "+src+'* ' + dst, shell=True)


if __name__ == "__main__":

  # Set arguments to conf.py
  # to separate a single local build from all builds we have a flag, see conf.py
  os.environ["build_all_docs"] = str(True)
  os.environ["pages_root"] = "https://dscc-admin-ch.github.io/lomas-docs"

  # manually build the master branch
  build_doc("stable", "en", "master")
  move_dir("./build/html/", "../pages/")
  r = subprocess.run(["ls", "-al", "../pages"], text=True, stdout=subprocess.PIPE)
  print(r.stdout)

  # reading the yaml file
  with open("versions.yaml", "r") as yaml_file:
    docs = yaml.safe_load(yaml_file)

  # and looping over all values to call our build with version, language and its tag
  for version, details in docs.items():
    if version == "stable":
      continue
    tag = details.get('tag', '')
    for language in details.get('languages', []): 
        build_doc(version, language, tag)
        move_dir("./build/html/", "../pages/"+version+'/'+language+'/')
        r = subprocess.run(["ls", "-al", "../pages"], text=True, stdout=subprocess.PIPE)
        print(r.stdout)