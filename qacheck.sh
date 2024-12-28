#!/usr/bin/env bash

# SPDX-FileCopyrightText: 2025 Ruslan Mstoi <ruslan.mstoi@gmail.com>
#
# SPDX-License-Identifier: MIT

set -x

files="wsmon.py test_wsmon.py"

isort $files
flake8 $files
reuse lint
