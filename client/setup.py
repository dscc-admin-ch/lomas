import pathlib

from setuptools import find_packages, setup

here = pathlib.Path(__file__).parent.resolve()

this_directory = pathlib.Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

setup(
    name="fso_sdd_demo",
    packages=find_packages(),
    version="0.0.7",
    description="A serializer of popular differential privacy frameworks \
        (OpenDP, Smartnoise-SQL) for remote execution.",
    url="https://https://gitlab.renkulab.io/dscc/sdd-poc-client",
    download_url="https://gitlab.renkulab.io/dscc/sdd-poc-client/-/releases/V_0.0.7/evidences/38.json",
    author="FSO DSCC",
    author_email="pauline.maury-laribiere@bfs.admin.ch",
    license="MIT",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
    ],
    keywords=["opendp", "smartnoise-sql", "logger", "ast"],
    python_requires=">=3.8, <4",
    install_requires=[
        "opendp == 0.8.0",
        "numpy == 1.22.3",
        "requests == 2.31.0",
        "pandas==2.0.1",
        "pyyaml",
    ],
)
