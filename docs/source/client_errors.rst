Errors
============

They are 4 custom errors describing the reasons why the queries fail and what to do:
    1. InvalidQueryException
    2. ExternalLibraryException
    3. UnauthorizedAccessException
    4. InternalServerException

Additionally, when utilizing a MongoDB administration database, a WriteConcernError (from pymongo.errors) may be triggered if a write operation is not acknowledged. In such instances, the error should be escalated to the server administrator as an InternalServerException.

=======================

.. _InvalidQueryException:

InvalidQueryException
---------------------
- Happens when: error is due to an an invalid query from the user
- Example: an "opendp" pipeline which is not a measurement, not enough budget for query
- What to do: Based on the specific error message, the user should check and fix their relevant query parameters.


.. _ExternalLibraryException:

ExternalLibraryException
------------------------
- Happens when: error comes from an external differential privacy library ("smartnoise-sql" or "opendp").
- Example: invalid values in Smartnoise-SQL `mechanisms` parameter.
- What to do: Based on the specific error message, the user should check and fix their "smartnoise-sql" `query` parameter or "opendp" `pipeline` parameter.


.. _UnauthorizedAccessException:

UnauthorizedAccessException
---------------------------
- Happens when: user tries to query a dataset without sufficient authorisation:
    - when the user does not exist,
    - when the user does not have access to the dataset,
    - when the user may not query.
- Example: user tries to query a dataframe to which they do not have access
- What to do: The user should decrease the budget parameters and check their access rights.

.. _InternalServerException:

InternalServerException
---------------------------
- Happens when: there are internal issues within the server.
- Example: failed startup of the server
- What to do: contact the administrative team for help. Users are not responsible for the failure of their request.

This error should never occur while the server is deployed.
