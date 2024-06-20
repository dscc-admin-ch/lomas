# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/dscc-admin-ch/lomas/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                                         |    Stmts |     Miss |   Cover |   Missing |
|--------------------------------------------- | -------: | -------: | ------: | --------: |
| \_\_init\_\_.py                              |        0 |        0 |    100% |           |
| admin\_database/\_\_init\_\_.py              |        0 |        0 |    100% |           |
| admin\_database/admin\_database.py           |       91 |        0 |    100% |           |
| admin\_database/mongodb\_database.py         |       54 |        1 |     98% |       275 |
| admin\_database/utils.py                     |       31 |        0 |    100% |           |
| admin\_database/yaml\_database.py            |       89 |        1 |     99% |       171 |
| administration/\_\_init\_\_.py               |        0 |        0 |    100% |           |
| app.py                                       |      150 |        8 |     95% |107-111, 145-151 |
| constants.py                                 |       69 |        3 |     96% |   7-8, 13 |
| dataset\_store/\_\_init\_\_.py               |        0 |        0 |    100% |           |
| dataset\_store/basic\_dataset\_store.py      |       24 |        0 |    100% |           |
| dataset\_store/dataset\_store.py             |       11 |        0 |    100% |           |
| dataset\_store/lru\_dataset\_store.py        |       42 |        3 |     93% |     87-91 |
| dataset\_store/private\_dataset\_observer.py |        4 |        0 |    100% |           |
| dataset\_store/utils.py                      |       14 |        0 |    100% |           |
| dp\_queries/\_\_init\_\_.py                  |        0 |        0 |    100% |           |
| dp\_queries/dp\_libraries/\_\_init\_\_.py    |        0 |        0 |    100% |           |
| dp\_queries/dp\_libraries/opendp.py          |       81 |        6 |     93% |146-152, 156-161 |
| dp\_queries/dp\_libraries/smartnoise\_sql.py |       46 |        5 |     89% |110, 121-125 |
| dp\_queries/dp\_libraries/utils.py           |       13 |        0 |    100% |           |
| dp\_queries/dp\_logic.py                     |       43 |        1 |     98% |       145 |
| dp\_queries/dp\_querier.py                   |       10 |        0 |    100% |           |
| dp\_queries/dummy\_dataset.py                |       49 |        0 |    100% |           |
| mongodb\_admin.py                            |      273 |        0 |    100% |           |
| private\_dataset/\_\_init\_\_.py             |        0 |        0 |    100% |           |
| private\_dataset/in\_memory\_dataset.py      |        9 |        0 |    100% |           |
| private\_dataset/path\_dataset.py            |       18 |        1 |     94% |        51 |
| private\_dataset/private\_dataset.py         |       25 |        0 |    100% |           |
| private\_dataset/s3\_dataset.py              |       20 |        0 |    100% |           |
| private\_dataset/utils.py                    |       22 |        0 |    100% |           |
| tests/\_\_init\_\_.py                        |        0 |        0 |    100% |           |
| tests/constants.py                           |        4 |        0 |    100% |           |
| tests/test\_api.py                           |      341 |        1 |     99% |       101 |
| tests/test\_dummy\_generation.py             |       63 |        0 |    100% |           |
| tests/test\_mongodb\_admin.py                |      414 |        0 |    100% |           |
| tests/test\_mongodb\_admin\_cli.py           |      242 |        0 |    100% |           |
| utils/\_\_init\_\_.py                        |        0 |        0 |    100% |           |
| utils/anti\_timing\_att.py                   |       18 |        0 |    100% |           |
| utils/collections\_models.py                 |       43 |        0 |    100% |           |
| utils/config.py                              |       88 |        2 |     98% |  267, 277 |
| utils/error\_handler.py                      |       36 |        2 |     94% |   120-121 |
| utils/example\_inputs.py                     |       15 |        0 |    100% |           |
| utils/input\_models.py                       |       41 |        0 |    100% |           |
| utils/loggr.py                               |        5 |        0 |    100% |           |
| utils/utils.py                               |       28 |        0 |    100% |           |
|                                    **TOTAL** | **2526** |   **34** | **99%** |           |


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