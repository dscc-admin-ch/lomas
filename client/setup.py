import pathlib

from setuptools import find_packages, setup

here = pathlib.Path(__file__).parent.resolve()

this_directory = pathlib.Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

setup(
    name="lomas_client",
    packages=find_packages(),
    version="0.0.1",
    description="A client to interact with the Lomas server.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/dscc-admin/dscc_sdd/",
    author="Data Science Competence Center, Swiss Federal Statistical Office",
    author_email="dscc@bfs.admin.ch",
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
        "numpy == 1.23.2",
        "requests == 2.31.0",
        "pandas==2.0.1",
        "pyyaml",
    ],
)
