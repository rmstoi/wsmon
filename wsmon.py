#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ruslan Mstoi <ruslan.mstoi@gmail.com>
#
# SPDX-License-Identifier: MIT

"""Website monitor

A program that monitors the availability of many websites over the network,
produces metrics about these and stores the metrics into a PostgreSQL database.

"""

import argparse
import asyncio
import re
import sys
from datetime import datetime

import aiohttp
import psycopg
import yaml

datastore = None


class WSData(object):
    """Monitor website data attributes"""

    # max time to retry a failing website monitor
    max_retry = 2

    def __init__(self, url, check_interval=5, pattern=None):
        """url -- the website url to monitor
        check_interval -- Each URL should be checked periodically, with the
                          ability to configure the interval (between 5 and 300
                          seconds)
        pattern -- Optional for checking the returned page contents for a regex
                   pattern that is expected to be found on the page.

        """
        interval_min = 5
        interval_max = 300
        assert check_interval >= interval_min and \
            check_interval <= interval_max, \
            f"interval set to {check_interval} but should be in range of " \
            " {interval_min} and {interval_max} seconds)"

        self.url = url
        self.check_interval = check_interval
        self.pattern = pattern

    def __str__(self):
        return ("url=%s check_interval=%s pattern=%r" %
                (self.url, self.check_interval, self.pattern))


class Database(object):
    """Database related functions and variables"""

    def __init__(self, conninfo, table_name):
        """
        conninfo -- connection info, parameter to
                    psycopg.AsyncConnection.connect
        table_name -- name of table used for site monitor results
        """
        self.conninfo = conninfo
        self.table_name = table_name

    async def create_table(self):
        """Create a database table to store website monitor results."""
        async with await psycopg.AsyncConnection.connect(**self.conninfo) \
                   as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    f"""CREATE TABLE IF NOT EXISTS {self.table_name} (
                            id SERIAL PRIMARY KEY,
                            url TEXT NOT NULL,
                            status_code INTEGER NOT NULL,
                            request_time TIMESTAMP NOT NULL,
                            response_time TIMESTAMP NOT NULL,
                            time_diff FLOAT NOT NULL,
                            regex_check TEXT NOT NULL
                            );
                    """)
                await conn.commit()

    async def insert(self, url, status_code, request_time, response_time,
                     time_diff, regex_check):
        """Insert row into a table"""
        async with await psycopg.AsyncConnection.connect(**self.conninfo) \
                   as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    f"""INSERT INTO {self.table_name} (
                            url, status_code, request_time, response_time,
                            time_diff, regex_check)
                            VALUES (%s, %s, %s, %s, %s, %s);""",
                    (url, status_code, request_time, response_time, time_diff,
                     regex_check))
                await conn.commit()


class YAMLFile(object):
    """Results YAML file"""

    filename = 'results.yaml'

    def __init__(self, conninfo=None, table_name=None):
        """
        conninfo -- connection info, parameter to
                    psycopg.AsyncConnection.connect
        table_name -- name of table used for site monitor results
        """
        self.conninfo = conninfo
        self.table_name = table_name
        self.results = []

    async def create_table(self):
        pass

    async def insert(self, url, status_code, request_time, response_time,
                     time_diff, regex_check):
        """Insert row into a table"""
        self.results.append(
            {f'{request_time} {url}': dict(url=url, status_code=status_code,
                                           request_time=request_time,
                                           response_time=response_time,
                                           time_diff=time_diff,
                                           regex_check=regex_check)})

    def save(self):
        """Write results to yaml file"""
        with open(self.filename, 'w') as fo:
            yaml.dump(self.results, fo)


def msg(text):
    now = datetime.now().time().replace(microsecond=0).isoformat()
    print(now + 4 * " " + text)


async def monitor_website(session, site):
    """Monitor the availability of website

    Also produce metrics and and store the metrics into a PostgreSQL database.

    """
    msg(f"SYN {site}")

    request_time = datetime.now()
    async with session.get(site.url) as resp:
        text = await resp.text()
        status = resp.status
        response_time = datetime.now()
        time_diff = (response_time - request_time).total_seconds()

        regexp_check = "not unused"
        if site.pattern:
            pattern = re.compile(site.pattern)
            m = pattern.search(text)
            if m:
                regexp_check = f"{pattern.pattern} found"
            else:
                regexp_check = "no match found"
        else:
            regexp_check = "not used"

        await datastore.insert(site.url, status, request_time, response_time,
                               time_diff, regexp_check)

        msg(f"FIN site={site} status={status} request_time={request_time} "
            f"response_time={response_time} time_diff={time_diff} "
            f"regex_check={regexp_check}")


async def wrapper(session, site):
    """Wrapper that handles retries and adds interval sleep after website
    monitor

    """
    retry = 0
    while True:
        try:
            await monitor_website(session, site)
        except Exception:
            msg(f"ERR url={site}")
            await datastore.insert(site.url, 444, datetime.now(),
                                   datetime.now(), 0, "ERROR")
            if retry == WSData.max_retry:
                msg(f"ERROR too many retries {retry}, stop monitor url={site}")
                break
            retry += 1
        await asyncio.sleep(site.check_interval)


def parse_args():
    """Parse command line arguments and options"""

    arg_parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])

    default_conf_file = "config.yaml"
    arg_parser.add_argument("-c", "--conf-file",
                            help="YAML config file. Default "
                            f"{default_conf_file}",
                            default=default_conf_file)
    arg_parser.add_argument("-r", "--results2file",
                            help="Write results to YAML file"
                            f" {YAMLFile.filename} instead of database",
                            action='store_true')
    args = arg_parser.parse_args()

    try:
        with open(args.conf_file, 'r') as conf_file:
            config = yaml.safe_load(conf_file)
    except Exception as err:
        print("Error reading config file:", err)
        raise
    return (config, args.results2file)


async def main():
    (config, results2file) = parse_args()
    WSData.max_retry = config['max_retry']

    global datastore
    if results2file:
        datastore = YAMLFile()
    else:
        datastore = Database(config["db"]["conninfo"],
                             config["db"]["table_name"])
        try:
            await datastore.create_table()
        except psycopg.OperationalError as err:
            sys.exit("Error creating database table: %r" % err)

    sites = [WSData(**site) for site in config['sites']]
    async with aiohttp.ClientSession() as session:
        await asyncio.gather(*(wrapper(session, site) for site in sites))


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        datastore.save()
        sys.exit("Bye!")
