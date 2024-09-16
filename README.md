# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/dscc-admin-ch/lomas/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                                           |    Stmts |     Miss |   Cover |   Missing |
|----------------------------------------------- | -------: | -------: | ------: | --------: |
| \_\_init\_\_.py                                |        0 |        0 |    100% |           |
| admin\_database/\_\_init\_\_.py                |        0 |        0 |    100% |           |
| admin\_database/admin\_database.py             |       87 |        0 |    100% |           |
| admin\_database/factory.py                     |       15 |        0 |    100% |           |
| admin\_database/mongodb\_database.py           |       59 |        1 |     98% |       283 |
| admin\_database/utils.py                       |       28 |        0 |    100% |           |
| admin\_database/yaml\_database.py              |       93 |        1 |     99% |       181 |
| administration/\_\_init\_\_.py                 |        0 |        0 |    100% |           |
| app.py                                         |       55 |        3 |     95% |     80-84 |
| constants.py                                   |       87 |        3 |     97% |  9-10, 15 |
| data\_connector/\_\_init\_\_.py                |        0 |        0 |    100% |           |
| data\_connector/data\_connector.py             |       24 |        0 |    100% |           |
| data\_connector/factory.py                     |       28 |        0 |    100% |           |
| data\_connector/in\_memory\_connector.py       |        9 |        0 |    100% |           |
| data\_connector/path\_connector.py             |       17 |        1 |     94% |        58 |
| data\_connector/s3\_connector.py               |       20 |        0 |    100% |           |
| dp\_queries/\_\_init\_\_.py                    |        0 |        0 |    100% |           |
| dp\_queries/dp\_libraries/\_\_init\_\_.py      |        0 |        0 |    100% |           |
| dp\_queries/dp\_libraries/diffprivlib.py       |       54 |        0 |    100% |           |
| dp\_queries/dp\_libraries/factory.py           |       20 |        0 |    100% |           |
| dp\_queries/dp\_libraries/opendp.py            |       81 |        8 |     90% |74, 153-159, 163-168, 220 |
| dp\_queries/dp\_libraries/smartnoise\_sql.py   |       55 |        5 |     91% |129, 140-144 |
| dp\_queries/dp\_libraries/smartnoise\_synth.py |      117 |        0 |    100% |           |
| dp\_queries/dp\_libraries/utils.py             |       33 |        0 |    100% |           |
| dp\_queries/dp\_querier.py                     |       34 |        1 |     97% |       108 |
| dp\_queries/dummy\_dataset.py                  |       40 |        1 |     98% |        54 |
| mongodb\_admin.py                              |      273 |        2 |     99% |  439, 676 |
| routes/\_\_init\_\_.py                         |        0 |        0 |    100% |           |
| routes/routes\_admin.py                        |       62 |        0 |    100% |           |
| routes/routes\_dp.py                           |       44 |        0 |    100% |           |
| routes/utils.py                                |       41 |        0 |    100% |           |
| tests/\_\_init\_\_.py                          |        0 |        0 |    100% |           |
| tests/constants.py                             |        6 |        0 |    100% |           |
| tests/test\_api.py                             |      396 |        1 |     99% |       102 |
| tests/test\_api\_diffprivlib.py                |      135 |        0 |    100% |           |
| tests/test\_api\_smartnoise\_synth.py          |      248 |        0 |    100% |           |
| tests/test\_collection\_models.py              |       85 |        0 |    100% |           |
| tests/test\_dummy\_generation.py               |       63 |        0 |    100% |           |
| tests/test\_mongodb\_admin.py                  |      416 |        1 |     99% |        75 |
| tests/test\_mongodb\_admin\_cli.py             |      243 |        1 |     99% |        45 |
| utils/\_\_init\_\_.py                          |        0 |        0 |    100% |           |
| utils/anti\_timing\_att.py                     |       18 |        0 |    100% |           |
| utils/collection\_models.py                    |      106 |        3 |     97% |116, 209, 218 |
| utils/config.py                                |       77 |        2 |     97% |  189, 199 |
| utils/error\_handler.py                        |       37 |        2 |     95% |   122-123 |
| utils/logger.py                                |        5 |        0 |    100% |           |
| utils/query\_examples.py                       |       37 |        0 |    100% |           |
| utils/query\_models.py                         |       64 |        0 |    100% |           |
|                                      **TOTAL** | **3312** |   **36** | **99%** |           |


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