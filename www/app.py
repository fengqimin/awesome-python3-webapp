# -*- coding: utf-8 -*-

"""
用aiohttp写一个基本的app.py
Web App将在9000端口监听HTTP请求，并且对首页/进行响应
"""
import logging
import asyncio, os, json, time
from datetime import datetime
from aiohttp import web


logging.basicConfig(level=logging.INFO)


def index(request):
    logging.info('request: {0}'.format(request))
    return web.Response(body=b'<h1>Awesome</h1>')


async def init(loop):
    app = web.Application(loop=loop)
    app.router.add_route('GET', '/', index)
    srv = await loop.create_server(app.make_handler(), '127.0.0.1', 9000)
    logging.info('server started at http://127.0.0.1:9000...')
    return srv


event_loop = asyncio.get_event_loop()
event_loop.run_until_complete(init(event_loop))
event_loop.run_forever()
