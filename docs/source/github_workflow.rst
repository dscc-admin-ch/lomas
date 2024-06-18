Release Workflow
==================

When preparing a new release, developers need to be aware of the existence of multiple processes.

Branches
--------------

* develop
* master
* release

.. Add schema + explanation ?


Docker build
--------------
TODO

Helm
--------------
TODO
.. * 


Documentation
--------------

.. * when working on release, the file versions.yaml must be MANUALLY edited in order to add the new tag associated to the new release
.. * github action will build all documentation (develop + all tags) when push is made on master or develop

Client (PyPi)
--------------

.. * when working on release, MANUALLY change version number in setup.py (idea to put the same one as the tag/version of the release)
.. * when release published, github action will automatically publish the lomas-client package to pypi (push_pypi.yml)
.. * no workflows are triggered when pushed are made on develop
