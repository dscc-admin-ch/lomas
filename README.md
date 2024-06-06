# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/dscc-admin-ch/lomas/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                                         |    Stmts |     Miss |   Cover |   Missing |
|--------------------------------------------- | -------: | -------: | ------: | --------: |
| \_\_init\_\_.py                              |        0 |        0 |    100% |           |
| admin\_database/\_\_init\_\_.py              |        0 |        0 |    100% |           |
| admin\_database/admin\_database.py           |       96 |        3 |     97% |38, 473-474 |
| admin\_database/mongodb\_database.py         |       58 |        3 |     95% |90-91, 291 |
| admin\_database/utils.py                     |       33 |        5 |     85% |     36-41 |
| admin\_database/yaml\_database.py            |       96 |       69 |     28% |26-28, 39-43, 54-58, 72-79, 94-98, 112-116, 136-147, 164-169, 185-190, 208-214, 231-234, 255-262, 275-278, 285-289 |
| administration/\_\_init\_\_.py               |        0 |        0 |    100% |           |
| app.py                                       |      204 |       64 |     69% |92-99, 103-107, 115-122, 141-147, 163, 220, 262-263, 309-310, 374-375, 438-441, 489-492, 549-550, 611-614, 656-659, 707-710, 763-766, 816-819, 870-873 |
| constants.py                                 |       62 |        3 |     95% |   7-8, 13 |
| dataset\_store/\_\_init\_\_.py               |        0 |        0 |    100% |           |
| dataset\_store/basic\_dataset\_store.py      |       24 |       12 |     50% |28-30, 39-54, 68-71 |
| dataset\_store/dataset\_store.py             |       11 |        0 |    100% |           |
| dataset\_store/lru\_dataset\_store.py        |       46 |        7 |     85% |66, 75-79, 96-100 |
| dataset\_store/private\_dataset\_observer.py |        4 |        0 |    100% |           |
| dataset\_store/utils.py                      |       16 |        3 |     81% | 31, 34-35 |
| dp\_queries/\_\_init\_\_.py                  |        0 |        0 |    100% |           |
| dp\_queries/dp\_libraries/\_\_init\_\_.py    |        0 |        0 |    100% |           |
| dp\_queries/dp\_libraries/opendp.py          |       73 |       28 |     62% |49-50, 55-66, 75, 78-86, 114-116, 183, 186-193 |
| dp\_queries/dp\_libraries/smartnoise\_sql.py |       50 |        7 |     86% |98-99, 110, 121-125 |
| dp\_queries/dp\_libraries/utils.py           |       15 |        2 |     87% |     30-31 |
| dp\_queries/dp\_logic.py                     |       53 |        8 |     85% |65, 76-77, 145, 177-180 |
| dp\_queries/dp\_querier.py                   |       10 |        0 |    100% |           |
| dp\_queries/dummy\_dataset.py                |       51 |        6 |     88% |58-64, 106-110 |
| mongodb\_admin.py                            |      282 |       78 |     72% |133, 142, 147, 393-396, 479-483, 495-499, 514-523, 576, 586-593, 604-628, 722-739, 749-753, 793-796, 810-818, 830-834, 862-871 |
| mongodb\_admin\_cli.py                       |      107 |      107 |      0% |     1-461 |
| private\_dataset/\_\_init\_\_.py             |        0 |        0 |    100% |           |
| private\_dataset/in\_memory\_dataset.py      |        9 |        0 |    100% |           |
| private\_dataset/path\_dataset.py            |       20 |        3 |     85% |     45-51 |
| private\_dataset/private\_dataset.py         |       25 |        0 |    100% |           |
| private\_dataset/s3\_dataset.py              |       22 |       14 |     36% |26-36, 47-63 |
| private\_dataset/utils.py                    |       24 |       10 |     58% |     38-61 |
| tests/\_\_init\_\_.py                        |        0 |        0 |    100% |           |
| tests/constants.py                           |        1 |        0 |    100% |           |
| tests/test\_api.py                           |      238 |        1 |     99% |        58 |
| tests/test\_dummy\_generation.py             |       52 |        0 |    100% |           |
| tests/test\_mongodb\_admin.py                |      240 |        0 |    100% |           |
| utils/\_\_init\_\_.py                        |        0 |        0 |    100% |           |
| utils/anti\_timing\_att.py                   |       20 |        4 |     80% |37-38, 47-48 |
| utils/collections\_models.py                 |       43 |        0 |    100% |           |
| utils/config.py                              |       84 |        9 |     89% |165-166, 206-209, 230, 234, 245, 255 |
| utils/error\_handler.py                      |       35 |        3 |     91% |62, 118-119 |
| utils/example\_inputs.py                     |       15 |        0 |    100% |           |
| utils/input\_models.py                       |       41 |        0 |    100% |           |
| utils/loggr.py                               |        5 |        0 |    100% |           |
| utils/utils.py                               |       29 |        9 |     69% | 33, 71-92 |
| uvicorn\_serve.py                            |       10 |       10 |      0% |      1-20 |
|                                    **TOTAL** | **2204** |  **468** | **79%** |           |


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