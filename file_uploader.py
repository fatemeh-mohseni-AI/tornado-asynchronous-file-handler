#!/usr/bin/env python

"""Usage: python file_uploader.py [--put] file1.txt file2.png ...

Demonstrates uploading files to a server, without concurrency. It can either
POST a multipart-form-encoded request containing one or more files, or PUT a
single file without encoding.

See also file_receiver.py in this directory, a server that receives uploads.
"""

import asyncio
import mimetypes
import os
import sys
from functools import partial
from urllib.parse import quote
from uuid import uuid4

from tornado import httpclient
from tornado.options import define, options

import yaml

# Using HTTP POST, upload one or more files in a single multipart-form-encoded


async def multipart_producer(boundary, filenames, write):
    boundary_bytes = boundary.encode()

    for filename in filenames:
        filename_bytes = filename.encode()
        mtype = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        buf = (
            (b"--%s\r\n" % boundary_bytes)
            + (
                b'Content-Disposition: form-data; name="%s"; filename="%s"\r\n'
                % (filename_bytes, filename_bytes)
            )
            + (b"Content-Type: %s\r\n" % mtype.encode())
            + b"\r\n"
        )
        await write(buf)
        with open(filename, "rb") as f:
            while True:
                # 16k at a time.
                chunk = f.read(16 * 1024)
                if not chunk:
                    break
                await write(chunk)

        await write(b"\r\n")

    await write(b"--%s--\r\n" % (boundary_bytes,))


# Using HTTP PUT, upload one raw file. This is preferred for large files since
# the server can stream the data instead of buffering it entirely in memory.

async def post(filenames):
    client = httpclient.AsyncHTTPClient(max_body_size=1024*1024*1024*1)
    boundary = uuid4().hex
    headers = {"Content-Type": "multipart/form-data; boundary=%s" % boundary}
    producer = partial(multipart_producer, boundary, filenames)
    response = await client.fetch(
        f"http://{conf['SERVER_IP_ADDRESS']}:{conf['SERVER_PORT']}/post",
        method="POST",
        headers=headers,
        body_producer=producer,
        request_timeout=3600,
    )

    print(response)


async def raw_producer(filename, write):
    with open(filename, "rb") as f:
        while True:
            # 16K at a time.
            chunk = f.read(16 * 1024)
            if not chunk:
                # Complete.
                break

            await write(chunk)


async def put(filenames):
    client = httpclient.AsyncHTTPClient()
    for filename in filenames:
        mtype = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        headers = {"Content-Type": mtype}
        producer = partial(raw_producer, filename)
        url_path = quote(os.path.basename(filename))
        response = await client.fetch(
            f"http://{conf['SERVER_IP_ADDRESS']}:{conf['SERVER_PORT']}/%s" % url_path,
            method="PUT",
            headers=headers,
            body_producer=producer,
        )
        print(response)


def config_loader():
    """
    loads every file inside config folder
    """
    config_ = {}

    logger_config_path = os.path.abspath(
        os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'production.yaml')
    )

    with open(logger_config_path) as f:
        config = yaml.safe_load(f)
        value = config["CONFIG"]

    return value


if __name__ == "__main__":
    # load config
    conf = config_loader()

    define("put", type=bool, help="Use PUT instead of POST", group="file uploader")

    # Tornado configures logging from command line opts and returns remaining args.
    filenames = options.parse_command_line()
    if not filenames:
        print("Provide a list of filenames to upload.", file=sys.stderr)
        sys.exit(1)

    method = put if options.put else post
    asyncio.run(method(filenames))

