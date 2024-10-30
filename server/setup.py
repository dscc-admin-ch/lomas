import pathlib
from setuptools import find_packages, setup

here = pathlib.Path(__file__).parent.resolve()

this_directory = pathlib.Path(__file__).parent
long_description = (this_directory / "README.md").read_text()


setup(
    name="lomas-server",
    packages=find_packages(),
    version="0.3.5",
    description="Lomas server.",
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
        "boto3==1.34.115",
        "httpx==0.27.0",
        "jax==0.4.31",
        "jaxlib==0.4.31",
        "lomas-core==0.3.5",
        "packaging==24.1",
        "pyaml==23.9.5",
        "pydantic==2.8.2",
        "smartnoise-sql==1.0.4",
        "uvicorn==0.29.0"
    ]
)
