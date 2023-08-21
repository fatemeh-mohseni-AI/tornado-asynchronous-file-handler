#!/usr/bin/env python

"""Usage: python file_receiver.py

Demonstrates a server that receives a multipart-form-encoded set of files in an
HTTP POST, or streams in the raw data of a single file in an HTTP PUT.

See file_uploader.py in this directory for code that uploads files in this format.
"""

import asyncio
import logging
import os.path
from urllib.parse import unquote

import tornado
from tornado import options

import io
import os
import PIL.Image as Image

save_path = "/home/fatemeh/Desktop/test/"


class POSTHandler(tornado.web.RequestHandler):
    def post(self):
        for field_name, files in self.request.files.items():
            for info in files:
                filename, content_type = info["filename"], info["content_type"]
                body = info["body"]
                logging.info(
                    'POST "%s" "%s" %d bytes', filename, content_type, len(body)
                )
                self.save(body, content_type, filename)
        self.write("OK")

    def save(self, body, content_type, filename):
        ls = [True for types in ["video", "mp4", "MP4"] if types in content_type]
        if True in ls:
            self.save_video(body, filename)

        ls_ = [True for types in ["image", "png", "jpeg", "jpg", "PNG", "JPG", "JPEG"] if types in content_type]
        if True in ls_:
            self.save_image(body, filename)

    def save_image(self, body, filename):
        image = Image.open(io.BytesIO(body))
        path = os.path.join(save_path, filename)
        image.save(path)

    def save_video(self, body, filename):
        path = os.path.join(save_path, filename)
        with open(path, "wb") as out_file:  # open for [w]riting as [b]inary
            out_file.write(body)


@tornado.web.stream_request_body
class PUTHandler(tornado.web.RequestHandler):
    def initialize(self):
        self.bytes_read = 0

    def data_received(self, chunk):
        self.bytes_read += len(chunk)

    def put(self, filename):
        filename = unquote(filename)
        mtype = self.request.headers.get("Content-Type")
        logging.info('PUT "%s" "%s" %d bytes', filename, mtype, self.bytes_read)
        self.write("OK")


def make_app():
    return tornado.web.Application([(r"/post", POSTHandler), (r"/(.*)", PUTHandler)])


async def main():
    options.parse_command_line()
    app = make_app()
    app.listen(8760, reuse_port=True)
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())

