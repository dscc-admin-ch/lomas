# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/dscc-admin-ch/lomas/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                                           |    Stmts |     Miss |   Cover |   Missing |
|----------------------------------------------- | -------: | -------: | ------: | --------: |
| \_\_init\_\_.py                                |        0 |        0 |    100% |           |
| admin\_database/\_\_init\_\_.py                |        0 |        0 |    100% |           |
| admin\_database/admin\_database.py             |       89 |        0 |    100% |           |
| admin\_database/constants.py                   |        7 |        0 |    100% |           |
| admin\_database/factory.py                     |       15 |        0 |    100% |           |
| admin\_database/mongodb\_database.py           |       74 |        2 |     97% |   294-295 |
| admin\_database/utils.py                       |       32 |        0 |    100% |           |
| admin\_database/yaml\_database.py              |       96 |        1 |     99% |       173 |
| administration/\_\_init\_\_.py                 |        0 |        0 |    100% |           |
| administration/dashboard/config.py             |       32 |       11 |     66% |10-11, 55-59, 73, 82-84, 97 |
| administration/tests/\_\_init\_\_.py           |        0 |        0 |    100% |           |
| app.py                                         |       60 |        3 |     95% |     81-83 |
| constants.py                                   |       45 |        3 |     93% | 10-11, 16 |
| data\_connector/\_\_init\_\_.py                |        0 |        0 |    100% |           |
| data\_connector/data\_connector.py             |       24 |        0 |    100% |           |
| data\_connector/factory.py                     |       27 |        0 |    100% |           |
| data\_connector/in\_memory\_connector.py       |        9 |        0 |    100% |           |
| data\_connector/path\_connector.py             |       17 |        1 |     94% |        54 |
| data\_connector/s3\_connector.py               |       19 |        0 |    100% |           |
| dp\_queries/\_\_init\_\_.py                    |        0 |        0 |    100% |           |
| dp\_queries/dp\_libraries/\_\_init\_\_.py      |        0 |        0 |    100% |           |
| dp\_queries/dp\_libraries/diffprivlib.py       |       54 |        0 |    100% |           |
| dp\_queries/dp\_libraries/factory.py           |       20 |        0 |    100% |           |
| dp\_queries/dp\_libraries/opendp.py            |       82 |        8 |     90% |65, 137-143, 147-152, 201 |
| dp\_queries/dp\_libraries/smartnoise\_sql.py   |       57 |        5 |     91% |124, 135-139 |
| dp\_queries/dp\_libraries/smartnoise\_synth.py |      118 |        0 |    100% |           |
| dp\_queries/dp\_libraries/utils.py             |       27 |        0 |    100% |           |
| dp\_queries/dp\_querier.py                     |       36 |        1 |     97% |       110 |
| dp\_queries/dummy\_dataset.py                  |       41 |        1 |     98% |        53 |
| mongodb\_admin.py                              |      290 |        2 |     99% |  411, 652 |
| routes/\_\_init\_\_.py                         |        0 |        0 |    100% |           |
| routes/middlewares.py                          |       61 |        0 |    100% |           |
| routes/routes\_admin.py                        |       64 |        0 |    100% |           |
| routes/routes\_dp.py                           |       44 |        0 |    100% |           |
| routes/utils.py                                |       63 |        0 |    100% |           |
| tests/\_\_init\_\_.py                          |        0 |        0 |    100% |           |
| tests/constants.py                             |        6 |        0 |    100% |           |
| tests/test\_api.py                             |      419 |        1 |     99% |       117 |
| tests/test\_api\_diffprivlib.py                |      138 |        0 |    100% |           |
| tests/test\_api\_smartnoise\_synth.py          |      265 |        0 |    100% |           |
| tests/test\_collection\_models.py              |       85 |        0 |    100% |           |
| tests/test\_dummy\_generation.py               |       63 |        0 |    100% |           |
| tests/test\_mongodb\_admin.py                  |      426 |        1 |     99% |        76 |
| tests/test\_mongodb\_admin\_cli.py             |      247 |        1 |     99% |        47 |
| utils/\_\_init\_\_.py                          |        0 |        0 |    100% |           |
| utils/config.py                                |       37 |        2 |     95% |    85, 95 |
| utils/metrics.py                               |       11 |        0 |    100% |           |
|                                      **TOTAL** | **3200** |   **43** | **99%** |           |


## Setup coverage badge

Below are examples of the badges you can use in your main branch `README` file.

### Direct image

[![Coverage badge](https://raw.githubusercontent.com/dscc-admin-ch/lomas/python-coverage-comment-action-data/badge.svg)](https://htmlpreview.github.io/?https://github.com/dscc-admin-ch/lomas/blob/python-coverage-comment-action-data/htmlcov/index.html)

This is the one to use if your repository is private or if you don't want to customize anything.

### [Shields.io](https://shields.io) Json Endpoint

[![Coverage badge](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/dscc-admin-ch/lomas/python-coverage-comment-action-data/endpoint.json)](https://htmlpreview.github.io/?https://github.com/dscc-admin-ch/lomas/blob/python-coverage-comment-action-data/htmlcov/index.html)

Using this one will allow you to [customize](https://shields.io/endpoint) the look of your badge.
It won't work with private repositories. It won't be refreshed more than once per five minutes.

### [Shields.io](https://shields.io) Dynamic Badge

[![Coverage badge](https://img.shields.io/badge/dynamic/json?color=brightgreen&label=coverage&query=%24.message&url=https%3A%2F%2Fraw.githubusercontent.com%2Fdscc-admin-ch%2Flomas%2Fpython-coverage-comment-action-data%2Fendpoint.json)](https://htmlpreview.github.io/?https://github.com/dscc-admin-ch/lomas/blob/python-coverage-comment-action-data/htmlcov/index.html)

This one will always be the same color. It won't work for private repos. I'm not even sure why we included it.

## What is that?

This branch is part of the
[python-coverage-comment-action](https://github.com/marketplace/actions/python-coverage-comment)
GitHub Action. All the files in this branch are automatically generated and may be
overwritten at any moment.