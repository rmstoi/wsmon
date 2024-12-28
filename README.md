<!--
SPDX-FileCopyrightText: 2025 Ruslan Mstoi <ruslan.mstoi@gmail.com>

SPDX-License-Identifier: MIT
-->

# Website monitor

A program that monitors the availability of many websites over the
network, produces metrics about these and stores the metrics into a
PostgreSQL database or YAML file.

## Install dependencies

To install needed Python packages

`python3 -m pip install -r requirements.txt`

## Usage

All of the default configuration settings are in `config.yaml` file. To
use different configuration settings yaml file pass it as an arument of
-c option.

To change PostgreSQL database settings modify db.conninfo and
db.table\_name attributes.

To add new sites to monitor add them to the `sites` list. Set as needed
check interval and regular expression pattern to check in the returned
page.

To start site monitor

`./wsmon.py`

Press Ctrl-C to stop `wsmon.py`

## Site check failure

If website check fails the error info will be saved to the database.
Failing site will be checked again max\_retry times.

## Unit tests

Use `pytest` to run unit tests:

`pytest .`
