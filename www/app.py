# -*- coding: utf-8 -*-

"""
用aiohttp写一个基本的app.py
Web App将在9000端口监听HTTP请求，并且对首页/进行响应
"""

import asyncio
import json
import logging
import os
import time
from datetime import datetime

from aiohttp import web
from jinja2 import Environment, FileSystemLoader
import orm
from config import configs
from coroweb import add_routes, add_static
#
# from handlers import cookie2user, COOKIE_NAME
#
# logging.basicConfig(level=logging.INFO)


def init_jinja2(app, **kwargs):
    """
    初始化jinja2模板
    我们使用jinja2作为模板引擎，在新框架中对jinja2模板进行初始化设置。
    参考资料：jinja2
    初始化jinja2需要以下几步：
    1、对Environment类的参数options进行配置。
    2、使用jinja提供的模板加载器加载模板文件，程序中选用FileSystemLoader加载器直接从模板文件夹加载模板。
    3、有了加载器和options参数，传递给Environment类，添加过滤器，完成初始化。
    :param app:
    :param kwargs:
    :return:
    """
    logging.info('init jinja2...')
    options = dict(
        autoescape=kwargs.get('autoescape', True),
        block_start_string=kwargs.get('block_start_string', '{%'),
        block_end_string=kwargs.get('block_end_string', '%}'),
        variable_start_string=kwargs.get('variable_start_string', '{{'),
        variable_end_string=kwargs.get('variable_end_string', '}}'),
        auto_reload=kwargs.get('auto_reload', True)
    )
    path = kwargs.get('path', None)
    if path is None:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
    logging.info('set jinja2 template path: %s' % path)
    env = Environment(loader=FileSystemLoader(path), **options)
    """The core component of Jinja is the `Environment`.  It contains
    important shared variables like configuration, filters, tests,
    globals and others.  Instances of this class may be modified if
    they are not shared and if no template was loaded so far.
    Modifications on environments after the first template was loaded
    will lead to surprising effects and undefined behavior.
    """
    filters = kwargs.get('filters', None)
    if filters is not None:
        for name, f in filters.items():
            env.filters[name] = f
    app['__template__'] = env


# 时间过滤器，显示登录时间
def datetime_filter(t):
    delta = int(time.time() - t)
    logging.debug('%s' % delta)
    if delta < 60:
        return u'1分钟前'
    if delta < 3600:
        return u'%s分钟前' % (delta // 60)
    if delta < 86400:
        return u'%s小时前' % (delta // 3600)
    if delta < 604800:
        return u'%s天前' % (delta // 86400)
    dt = datetime.fromtimestamp(t)
    return u'%s年%s月%s日' % (dt.year, dt.month, dt.day)


# middleware
# middleware是符合WSGI定义的中间件。位于服务端和客户端之间对数据进行拦截处理的一个桥梁。
# 可以看做服务器端的数据，经middleware一层层封装，最终传递给客户端。
# middleware是一种拦截器，一个URL在被某个函数处理前，可以经过一系列的middleware的处理。
# 一个middleware可以改变URL的输入、输出，甚至可以决定不继续处理而直接返回。
# middleware的用处就在于把通用的功能从每个URL处理函数中拿出来，集中放到一个地方。例如，一个记录URL日志的logger可以简单定义如下：
async def logger_factory(app, handler):
    """
    middleware,记录URL日志
    :param app:
    :param handler:
    :return:
    """

    async def logger(request):
        # 记录日志:
        logging.info('Request: %s %s' % (request.method, request.path))
        # 继续处理请求:
        return await handler(request)

    return logger


async def auth_factory(app, handler):
    """
    对于每个URL处理函数，如果我们都去写解析cookie的代码，那会导致代码重复很多次。
    利用middle在处理URL之前，把cookie解析出来，并将登录用户绑定到request对象上，这样，后续的URL处理函数就可以直接拿到登录用户。
    :param app:
    :param handler:
    :return:
    """
    from handlers import cookie2user, COOKIE_NAME
    async def auth(request):
        logging.info('check user: %s %s' % (request.method, request.path))
        request.__user__ = None
        cookie_str = request.cookies.get(COOKIE_NAME)
        if cookie_str:
            user = await cookie2user(cookie_str)
            if user:
                logging.info('set current user: %s' % user.email)
                request.__user__ = user
        if request.path.startswith('/manage/') and (request.__user__ is None or (not request.__user__.admin)):
            return web.HTTPFound('/signin')
        return await handler(request)

    return auth


async def data_factory(app, handler):

    async def parse_data(request):
        if request.method == 'POST':
            if request.content_type.startswith('application/json'):
                request.__data__ = await request.json()
                logging.info('request json: %s' % str(request.__data__))
            elif request.content_type.startswith('application/x-www-form-urlencoded'):
                request.__data__ = await request.post()
                logging.info('request form: %s' % str(request.__data__))
        return await handler(request)

    return parse_data


async def response_factory(app, handler):
    """
    middleware,把返回值转换为web.Response对象再返回，以保证满足aiohttp的要求
    :param app:
    :param handler:
    :return:
    """
    async def response(request):
        logging.info('Response handler...')
        # 结果:
        result = await handler(request)
        # 是web.Response对象，直接返回
        if isinstance(request, web.StreamResponse):
            return result
        # bytes，为二进制流
        if isinstance(result, bytes):
            resp = web.Response(body=result)
            resp.content_type = 'application/octet-stream'
            return resp
        # str，页面或redirect
        if isinstance(result, str):
            # redirect
            if result.startswith('redirect:'):
                return web.HTTPFound(result[9:])
            resp = web.Response(body=result.encode('utf-8'))
            resp.content_type = 'text/html;charset=utf-8'
            return resp
        # dict
        if isinstance(result, dict):
            # 在后续构造视图url函数返回值时，会加入__template__值，用以选择渲染的模板
            template = result.get('__template__')  # D.get(k[,d]) -> D[k] if k in D, else d.  d defaults to None.
            # 没有模板
            if template is None:
                resp = web.Response(
                    body=json.dumps(
                        result,
                        ensure_ascii=False,
                        default=lambda o: o.__dict__).encode('utf-8'))
                resp.content_type = 'application/json;charset=utf-8'
                return resp
            else:  # 有模板
                # 读取用户模板
                result['__user__'] = getattr(request, '__user__', None)
                # jinja2.environment,读取用户模板并返回相应页面
                resp = web.Response(
                    body=app['__template__'].get_template(template).render(**result).encode('utf-8'))
                resp.content_type = 'text/html;charset=utf-8'
                return resp

        # int，HTTP Response Status Code
        if isinstance(result, int) and 100 <= result < 600:
            return web.Response(status=result)
        # tuple,状态码和状态信息,如：(200, 'OK')
        if isinstance(result, tuple) and len(result) == 2:
            status_code, msg = result
            if isinstance(status_code, int) and 100 <= status_code < 600:
                return web.Response(status=status_code, text=str(msg))
        # default:
        resp = web.Response(body=str(result).encode('utf-8'))  # 均以上条件不满足，默认返回
        resp.content_type = 'text/plain;charset=utf-8'  # utf-8纯文本
        return resp

    return response


def timestamp2time(ts):
    local_time = time.localtime(ts)
    dt = time.strftime("%Y-%m-%d %H:%M:%S", local_time)
    return dt


async def init(loop, host='127.0.0.1', port=9000):
    """
    init web app
    :param loop:
    :param host:
    :param port:
    :return:
    """
    await orm.create_pool(loop=loop, **configs.db)
    app = web.Application(
        loop=loop,
        middlewares=[logger_factory, auth_factory, response_factory])
    init_jinja2(app, filters=dict(datetime=datetime_filter))
    add_routes(app, 'handlers')
    # add_static(app)
    srv = await loop.create_server(app.make_handler(), host, port)
    logging.info('server started at http://%s:%s...' % (host, port))
    return srv


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    event_loop = asyncio.get_event_loop()
    event_loop.run_until_complete(init(event_loop))
    event_loop.run_forever()
