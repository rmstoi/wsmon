# SPDX-FileCopyrightText: 2025 Ruslan Mstoi <ruslan.mstoi@gmail.com>
#
# SPDX-License-Identifier: MIT

from wsmon import WSData

# WSData default test arguments
url = "http://testsite.io"
check_interval = 111
pattern = r'(.*) example'


def test_wsdata_init():
    site = WSData(url, check_interval, pattern)
    assert site.url == url
    assert site.check_interval == check_interval
    assert site.pattern == pattern


def test_wsdata_init_default():
    """Test default arguments"""
    site = WSData(url)
    assert site.url == url
    assert site.check_interval == 5
    assert site.pattern is None


def test_wsdata_str():
    site = WSData(url, check_interval, pattern)
    expect_str = ("url=%s check_interval=%s pattern=%r" %
                  (url, check_interval, pattern))
    assert str(site) == expect_str
