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
| app.py                                       |      145 |        9 |     94% |106-110, 144-150, 223 |
| constants.py                                 |       62 |        3 |     95% |   7-8, 13 |
| dataset\_store/\_\_init\_\_.py               |        0 |        0 |    100% |           |
| dataset\_store/basic\_dataset\_store.py      |       24 |        0 |    100% |           |
| dataset\_store/dataset\_store.py             |       11 |        0 |    100% |           |
| dataset\_store/lru\_dataset\_store.py        |       45 |        6 |     87% |75-79, 96-100 |
| dataset\_store/private\_dataset\_observer.py |        4 |        0 |    100% |           |
| dataset\_store/utils.py                      |       14 |        0 |    100% |           |
| dp\_queries/\_\_init\_\_.py                  |        0 |        0 |    100% |           |
| dp\_queries/dp\_libraries/\_\_init\_\_.py    |        0 |        0 |    100% |           |
| dp\_queries/dp\_libraries/opendp.py          |       61 |       16 |     74% |49-50, 55-57, 75, 78-84, 183, 186-191 |
| dp\_queries/dp\_libraries/smartnoise\_sql.py |       46 |        5 |     89% |110, 121-125 |
| dp\_queries/dp\_libraries/utils.py           |       13 |        0 |    100% |           |
| dp\_queries/dp\_logic.py                     |       43 |        1 |     98% |       145 |
| dp\_queries/dp\_querier.py                   |       10 |        0 |    100% |           |
| dp\_queries/dummy\_dataset.py                |       49 |        4 |     92% |58-64, 106-108 |
| mongodb\_admin.py                            |      279 |       34 |     88% |133, 142, 147, 572, 582-589, 600-624, 718-732, 745-749 |
| private\_dataset/\_\_init\_\_.py             |        0 |        0 |    100% |           |
| private\_dataset/in\_memory\_dataset.py      |        9 |        0 |    100% |           |
| private\_dataset/path\_dataset.py            |       18 |        1 |     94% |        51 |
| private\_dataset/private\_dataset.py         |       25 |        0 |    100% |           |
| private\_dataset/s3\_dataset.py              |       20 |       12 |     40% |26-36, 47-63 |
| private\_dataset/utils.py                    |       22 |        8 |     64% |     38-59 |
| tests/\_\_init\_\_.py                        |        0 |        0 |    100% |           |
| tests/constants.py                           |        1 |        0 |    100% |           |
| tests/test\_api.py                           |      243 |        0 |    100% |           |
| tests/test\_dummy\_generation.py             |       52 |        0 |    100% |           |
| tests/test\_mongodb\_admin.py                |      346 |        0 |    100% |           |
| tests/test\_mongodb\_admin\_cli.py           |      242 |        0 |    100% |           |
| utils/\_\_init\_\_.py                        |        0 |        0 |    100% |           |
| utils/anti\_timing\_att.py                   |       18 |        0 |    100% |           |
| utils/collections\_models.py                 |       43 |        0 |    100% |           |
| utils/config.py                              |       80 |        2 |     98% |  245, 255 |
| utils/error\_handler.py                      |       35 |        3 |     91% |62, 118-119 |
| utils/example\_inputs.py                     |       15 |        0 |    100% |           |
| utils/input\_models.py                       |       41 |        0 |    100% |           |
| utils/loggr.py                               |        5 |        0 |    100% |           |
| utils/utils.py                               |       28 |        8 |     71% |     71-92 |
| uvicorn\_serve.py                            |       10 |       10 |      0% |      1-20 |
|                                    **TOTAL** | **2324** |  **124** | **95%** |           |


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