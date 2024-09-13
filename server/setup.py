from setuptools import find_packages, setup


setup(
    name="lomas-server",
    packages=find_packages(),
    version="0.3.2",
    description="Lomas server.",
    # long_description=long_description,
    # long_description_content_type="text/markdown",
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
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Scientific/Engineering",
        "Topic :: Security",
    ],
    # install_requires=..
)
