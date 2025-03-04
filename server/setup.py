from pathlib import Path

from setuptools import find_packages, setup

setup(
    name="lomas-server",
    packages=find_packages(),
    version="0.4.1",
    description="Lomas server.",
    long_description=Path("README.md").read_text("utf-8"),
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
    install_requires=Path("requirements_server.txt").read_text("utf-8").splitlines(),
    extras_require={
        "admin": [
            "mantelo==2.2.0",
            "mongomock==4.3.0",
            "oauthlib==3.2.2",
            "pytest==8.3.3",
            "requests==2.32.0",
            "requests-oauthlib==2.0.0",
            "streamlit==1.39.0",
            "st-pages==0.5.0",
        ]
    },
)
