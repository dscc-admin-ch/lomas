# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/dscc-admin-ch/lomas/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                                         |    Stmts |     Miss |   Cover |   Missing |
|--------------------------------------------- | -------: | -------: | ------: | --------: |
| \_\_init\_\_.py                              |        0 |        0 |    100% |           |
| admin\_database/\_\_init\_\_.py              |        0 |        0 |    100% |           |
| admin\_database/admin\_database.py           |       92 |        1 |     99% |       457 |
| admin\_database/mongodb\_database.py         |       54 |        1 |     98% |       275 |
| admin\_database/utils.py                     |       32 |        1 |     97% |        40 |
| admin\_database/yaml\_database.py            |       89 |        1 |     99% |       171 |
| administration/\_\_init\_\_.py               |        0 |        0 |    100% |           |
| app.py                                       |      157 |       21 |     87% |106-110, 144-150, 223, 265, 312, 377, 443, 494, 552, 616, 661, 712, 768, 821, 875 |
| constants.py                                 |       62 |        3 |     95% |   7-8, 13 |
| dataset\_store/\_\_init\_\_.py               |        0 |        0 |    100% |           |
| dataset\_store/basic\_dataset\_store.py      |       24 |        0 |    100% |           |
| dataset\_store/dataset\_store.py             |       11 |        0 |    100% |           |
| dataset\_store/lru\_dataset\_store.py        |       45 |        6 |     87% |75-79, 96-100 |
| dataset\_store/private\_dataset\_observer.py |        4 |        0 |    100% |           |
| dataset\_store/utils.py                      |       15 |        1 |     93% |        34 |
| dp\_queries/\_\_init\_\_.py                  |        0 |        0 |    100% |           |
| dp\_queries/dp\_libraries/\_\_init\_\_.py    |        0 |        0 |    100% |           |
| dp\_queries/dp\_libraries/opendp.py          |       71 |       26 |     63% |49-50, 55-66, 75, 78-85, 114-116, 183, 186-191 |
| dp\_queries/dp\_libraries/smartnoise\_sql.py |       50 |        7 |     86% |98-99, 110, 121-125 |
| dp\_queries/dp\_libraries/utils.py           |       14 |        1 |     93% |        30 |
| dp\_queries/dp\_logic.py                     |       48 |        3 |     94% |76, 145, 179 |
| dp\_queries/dp\_querier.py                   |       10 |        0 |    100% |           |
| dp\_queries/dummy\_dataset.py                |       50 |        5 |     90% |58-64, 106-109 |
| mongodb\_admin.py                            |      280 |       35 |     88% |133, 142, 147, 572, 582-589, 600-624, 718-734, 745-749 |
| mongodb\_admin\_cli.py                       |      107 |      107 |      0% |     1-461 |
| private\_dataset/\_\_init\_\_.py             |        0 |        0 |    100% |           |
| private\_dataset/in\_memory\_dataset.py      |        9 |        0 |    100% |           |
| private\_dataset/path\_dataset.py            |       19 |        2 |     89% |     45-51 |
| private\_dataset/private\_dataset.py         |       25 |        0 |    100% |           |
| private\_dataset/s3\_dataset.py              |       21 |       13 |     38% |26-36, 47-63 |
| private\_dataset/utils.py                    |       23 |        9 |     61% |     38-60 |
| tests/\_\_init\_\_.py                        |        0 |        0 |    100% |           |
| tests/constants.py                           |        1 |        0 |    100% |           |
| tests/test\_api.py                           |      243 |        0 |    100% |           |
| tests/test\_dummy\_generation.py             |       52 |        0 |    100% |           |
| tests/test\_mongodb\_admin.py                |      346 |        0 |    100% |           |
| tests/test\_mongodb\_admin\_cli.py           |      242 |        0 |    100% |           |
| utils/\_\_init\_\_.py                        |        0 |        0 |    100% |           |
| utils/anti\_timing\_att.py                   |       19 |        1 |     95% |        47 |
| utils/collections\_models.py                 |       43 |        0 |    100% |           |
| utils/config.py                              |       81 |        3 |     96% |165, 245, 255 |
| utils/error\_handler.py                      |       35 |        3 |     91% |62, 118-119 |
| utils/example\_inputs.py                     |       15 |        0 |    100% |           |
| utils/input\_models.py                       |       41 |        0 |    100% |           |
| utils/loggr.py                               |        5 |        0 |    100% |           |
| utils/utils.py                               |       28 |        8 |     71% |     71-92 |
| uvicorn\_serve.py                            |       10 |       10 |      0% |      1-20 |
|                                    **TOTAL** | **2473** |  **268** | **89%** |           |


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