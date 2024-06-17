import os
import subprocess
import yaml

# https://www.codingwiththomas.com/blog/my-sphinx-best-practice-for-a-multiversion-documentation-in-different-languages
# a single build step, which keeps conf.py and versions.yaml at the develop branch
# in generall we use environment variables to pass values to conf.py, see below
# and runs the build as we did locally
def build_doc(version, 
              language, 
              tag,
              ):
    os.environ["current_version"] = version
    os.environ["current_language"] = language
    subprocess.run("git checkout " + tag, shell=True)
    subprocess.run("git checkout develop -- conf.py", shell=True)
    subprocess.run("git checkout develop -- versions.yaml", shell=True)
    subprocess.run("cp ../images/lomas_logo_txt.png ./source/_static/logo.png", shell=True)
    subprocess.run("cp ../server/CONTRIBUTING.md ./source/CONTRIBUTING.md", shell=True)
    subprocess.run("sphinx-apidoc -o ./source ../client/lomas_client/ --tocfile client_modules", shell=True)
    subprocess.run("sphinx-apidoc -o ./source ../server/lomas_server/ --tocfile server_modules", shell=True)
    subprocess.run("mkdir ./source/notebooks", shell=True)
    subprocess.run("cp -r ../client/notebooks/Demo_Client_Notebook.ipynb ./source/notebooks/Demo_Client_Notebook.ipynb", shell=True)
    subprocess.run("cp -r ../client/notebooks/s3_example_notebook.ipynb ./source/notebooks/s3_example_notebook.ipynb", shell=True)
    subprocess.run("cp -r ../server/notebooks/local_admin_notebook.ipynb ./source/notebooks/local_admin_notebook.ipynb", shell=True)
    # os.environ['SPHINXOPTS'] = "-D language='{}'".format(language)
    subprocess.run("make html", shell=True)    

# a move dir method because we run multiple builds and bring the html folders to a 
# location which we then push to github pages
def move_dir(src, dst):
  subprocess.run(["mkdir", "-p", dst])
  subprocess.run("mv "+src+'* ' + dst, shell=True)

# to separate a single local build from all builds we have a flag, see conf.py
os.environ["build_all_docs"] = str(True)
os.environ["pages_root"] = "https://dscc-admin-ch.github.io/lomas-docs"

# manually the master branch build in the current supported languages
build_doc("stable", "en", "master")
move_dir("./build/html/", "../pages/")

# reading the yaml file
with open("versions.yaml", "r") as yaml_file:
  docs = yaml.safe_load(yaml_file)

# and looping over all values to call our build with version, language and its tag
for version, details in docs.items():
  tag = details.get('tag', '')
  for language in details.get('languages', []): 
    build_doc(version, language, tag)
    move_dir("./build/html/", "../pages/"+version+'/'+language+'/')