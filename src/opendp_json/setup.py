import pathlib

from setuptools import find_packages, setup

here = pathlib.Path(__file__).parent.resolve()

setup(
    name="OpenDP Logger",
    version="0.1.0",
    description="A logger wrapper for OpenDP to keep track of, import, export the AST",
    url="https://github.com/ObliviousAI/opendp_json",
    author='Oblivious',
    author_email='hello@oblivious.ai',
    license='MIT',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
    ], 
    keywords='opendp logger ast',
    packages=find_packages(),
    python_requires=">=3.7, <4",
    install_requires=[
        "opendp >= 0.5.0",
        "PyYAML >= 6.0"
    ],
    package_data={"oblv": ["py.typed"]},
)