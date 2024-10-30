import pathlib

from setuptools import find_packages, setup

here = pathlib.Path(__file__).parent.resolve()

this_directory = pathlib.Path(__file__).parent
long_description = (this_directory / "README.md").read_text()


setup(
    name="lomas-core",
    packages=find_packages(),
    version="0.3.5",
    description="Lomas core.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/dscc-admin-ch/lomas/",
    author="Data Science Competence Center, Swiss Federal Statistical Office",
    author_email="dscc@bfs.admin.ch",
    license="MIT",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Natural Language :: English",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Scientific/Engineering",
        "Topic :: Security",
    ],
    python_requires=">=3.11, <3.13",
    install_requires=[
        "diffprivlib==0.6.5",
        "diffprivlib_logger>=0.0.3",
        "fastapi>=0.111.1",
        "numpy>=1.26.4",
        "opendp==0.10.0",
        "opendp_logger>=0.3.0",
        "pandas>=2.2.2",
        "pymongo>=4.6.3",
        "scikit-learn>=1.4.2",
        "smartnoise-synth>=1.0.4",
        "smartnoise_synth_logger>=0.0.3"
    ]
)
