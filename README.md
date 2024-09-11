# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/dscc-admin-ch/lomas/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                                           |    Stmts |     Miss |   Cover |   Missing |
|----------------------------------------------- | -------: | -------: | ------: | --------: |
| \_\_init\_\_.py                                |        0 |        0 |    100% |           |
| admin\_database/\_\_init\_\_.py                |        0 |        0 |    100% |           |
| admin\_database/admin\_database.py             |       87 |        0 |    100% |           |
| admin\_database/factory.py                     |       17 |        0 |    100% |           |
| admin\_database/mongodb\_database.py           |       57 |        1 |     98% |       281 |
| admin\_database/utils.py                       |       27 |        0 |    100% |           |
| admin\_database/yaml\_database.py              |       91 |        1 |     99% |       176 |
| administration/\_\_init\_\_.py                 |        0 |        0 |    100% |           |
| app.py                                         |       70 |        8 |     89% |79-83, 121-127 |
| constants.py                                   |       98 |        3 |     97% |   7-8, 13 |
| data\_connector/\_\_init\_\_.py                |        0 |        0 |    100% |           |
| data\_connector/data\_connector.py             |       32 |        0 |    100% |           |
| data\_connector/factory.py                     |       28 |        0 |    100% |           |
| data\_connector/in\_memory\_connector.py       |        9 |        0 |    100% |           |
| data\_connector/path\_connector.py             |       19 |        1 |     95% |        55 |
| data\_connector/s3\_connector.py               |       22 |        0 |    100% |           |
| dataset\_store/\_\_init\_\_.py                 |        0 |        0 |    100% |           |
| dataset\_store/basic\_dataset\_store.py        |       24 |        0 |    100% |           |
| dataset\_store/data\_connector\_observer.py    |        4 |        0 |    100% |           |
| dataset\_store/dataset\_store.py               |       14 |        0 |    100% |           |
| dataset\_store/factory.py                      |       15 |        0 |    100% |           |
| dataset\_store/lru\_dataset\_store.py          |       43 |        3 |     93% |     93-97 |
| dp\_queries/\_\_init\_\_.py                    |        0 |        0 |    100% |           |
| dp\_queries/dp\_libraries/\_\_init\_\_.py      |        0 |        0 |    100% |           |
| dp\_queries/dp\_libraries/diffprivlib.py       |       53 |        0 |    100% |           |
| dp\_queries/dp\_libraries/factory.py           |       19 |        0 |    100% |           |
| dp\_queries/dp\_libraries/opendp.py            |       81 |        8 |     90% |67, 146-152, 156-161, 213 |
| dp\_queries/dp\_libraries/smartnoise\_sql.py   |       52 |        5 |     90% |104, 115-119 |
| dp\_queries/dp\_libraries/smartnoise\_synth.py |      121 |        0 |    100% |           |
| dp\_queries/dp\_libraries/utils.py             |       33 |        0 |    100% |           |
| dp\_queries/dp\_logic.py                       |       43 |        1 |     98% |       145 |
| dp\_queries/dp\_querier.py                     |       10 |        0 |    100% |           |
| dp\_queries/dummy\_dataset.py                  |       50 |        0 |    100% |           |
| mongodb\_admin.py                              |      271 |        0 |    100% |           |
| routes/\_\_init\_\_.py                         |        0 |        0 |    100% |           |
| routes/routes\_admin.py                        |       66 |        0 |    100% |           |
| routes/routes\_dp.py                           |       44 |        0 |    100% |           |
| routes/utils.py                                |       36 |        0 |    100% |           |
| tests/\_\_init\_\_.py                          |        0 |        0 |    100% |           |
| tests/constants.py                             |        6 |        0 |    100% |           |
| tests/test\_api.py                             |      428 |        1 |     99% |       103 |
| tests/test\_api\_diffprivlib.py                |      140 |        3 |     98% |     29-32 |
| tests/test\_api\_smartnoise\_synth.py          |      248 |        0 |    100% |           |
| tests/test\_dummy\_generation.py               |       63 |        0 |    100% |           |
| tests/test\_mongodb\_admin.py                  |      414 |        0 |    100% |           |
| tests/test\_mongodb\_admin\_cli.py             |      242 |        0 |    100% |           |
| utils/\_\_init\_\_.py                          |        0 |        0 |    100% |           |
| utils/anti\_timing\_att.py                     |       18 |        0 |    100% |           |
| utils/collection\_models.py                    |       46 |        0 |    100% |           |
| utils/config.py                                |       83 |        2 |     98% |  211, 221 |
| utils/error\_handler.py                        |       36 |        2 |     94% |   120-121 |
| utils/logger.py                                |        5 |        0 |    100% |           |
| utils/query\_examples.py                       |       37 |        0 |    100% |           |
| utils/query\_models.py                         |       75 |        0 |    100% |           |
|                                      **TOTAL** | **3377** |   **39** | **99%** |           |


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