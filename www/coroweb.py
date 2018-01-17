# -*- coding: utf-8 -*-

"""
在正式开始Web开发前，我们需要编写一个Web框架。
"""
import functools, inspect, os
from aiohttp import web
from urllib import parse
# import urllib.request
import logging
import asyncio


from apis import APIError


# 建立视图url函数装饰器，用来附带URL信息
# @get
def get(path):
    """
    定义一个装饰器@get('/path')，把一个函数映射为一个URL处理函数
    :param:path ``str`` the path of url
    :return:一个函数通过@get()的装饰就附带了URL信息。
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        wrapper.__method__ = 'GET'  # 附带的请求方式
        wrapper.__route__ = path  # 附带的URL信息
        return wrapper

    return decorator


# @post
def post(path):
    """
    定义一个装饰器@post('/path')，把一个函数映射为一个URL处理函数
    :param:path ``str`` the path of url
    :return:
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        wrapper.__method__ = 'POST'
        wrapper.__route__ = path
        return wrapper

    return decorator


"""
定义RequestHandler

我们已经完成了MVC视图url函数装饰器的编写，但这远远不够。视图url函数仍无法从request中获取参数。
所以我们还要从request对象中提取相应视图url函数所需的参数，并且视图url函数并非都是coroutine。
因此，需要定义一个能处理request请求的类来对视图url函数进行封装，RequestHandler。
RequestHandler是一个类，分析视图url函数所需的参数，再从request对象中将参数提取，调用视图url函数（URL处理函数），并返回web.Response对象。
由于其定义了__call__()方法，其实例对象可以看作函数。
用这样一个RequestHandler类，就能处理各类request向对应视图url函数发起的请求了。
RequestHandler目的就是从URL函数中分析其需要接收的参数，从request中获取必要的参数，调用URL函数，
然后把结果转换为web.Response对象，这样，就完全符合aiohttp框架的要求：
"""


# 解析视图url函数
# 使用python自带库的inspect模块，解析视图url函数的参数。
# 在 Python 中定义函数，可以用必选参数、默认参数、可变参数、关键字参数和命名关键字参数5种参数形式。
#  inspect.Parameter.kind 类型：
# POSITIONAL_ONLY       位置参数，属于python的历史产物，你无法在高版本的python中创建一个POSITIONAL_ONLY类型的参数
# KEYWORD_ONLY          命名关键词参数 fn( a, request, *args, c=1, d, **kwargs)中的c, d，其中c为可选命名关键字，d为必选命名关键字
# VAR_POSITIONAL        可变位置参数 fn( a, request, *args, c=1, d, **kwargs)中的*args
# VAR_KEYWORD           可变关键字参数 fn( a, request, *args, c=1, d, **kwargs)中的**kwargs
# POSITIONAL_OR_KEYWORD 位置或关键字参数fn( a, request, *args, c=1, d, **kwargs)中的a, request
# 这 5 种参数都可以组合起来使用，但是注意，参数定义的顺序必须是：必选参数、默认参数、可变参数/命名关键字参数和关键字参数。
# 接收参数的优先级
#   1. 先接收POSITIONAL_OR_KEYWORD
# 	2. 再接收KEYWORD_ONLY
#   3. 再接收VAR_POSITIONAL和VAR_KEYWORD，这两者没有交集
def get_required_kw_args(fn):
    """
    # 获取无默认值的命名关键词参数名称
    :param fn:the name of func
    :return:the list of required kwargs
    """
    args = []
    ''' 
    def foo(a, b = 10, *c, d,**kw): 
        pass 
    sig = inspect.signature(foo) ==> <Signature (a, b=10, *c, d, **kw)> 
    sig.parameters ==>  mappingproxy(OrderedDict([('a', <Parameter "a">), ...])) 
    * parameters : OrderedDict
        An ordered mapping of parameters' names to the corresponding
        Parameter objects (keyword-only arguments are in the same order
        as listed in `code.co_varnames`).
        class Parameter:
    """Represents a parameter in a function signature.

    Has the following public attributes:

    * name : str
        The name of the parameter as a string.
    * default : object
        The default value for the parameter if specified.  If the
        parameter has no default value, this attribute is set to
        `Parameter.empty`.
    * annotation
        The annotation for the parameter if specified.  If the
        parameter has no annotation, this attribute is set to
        `Parameter.empty`.
    * kind : str
        Describes how argument values are bound to the parameter.
        Possible values: `Parameter.POSITIONAL_ONLY`,
        `Parameter.POSITIONAL_OR_KEYWORD`, `Parameter.VAR_POSITIONAL`,
        `Parameter.KEYWORD_ONLY`, `Parameter.VAR_KEYWORD`.
    """
    sig.parameters.items() ==> odict_items([('a', <Parameter "a">), ...)]) 
    sig.parameters.values() ==>  odict_values([<Parameter "a">, ...]) 
    sig.parameters.keys() ==>  odict_keys(['a', 'b', 'c', 'd', 'kw']) 
    '''
    params = inspect.signature(fn).parameters  # OrderedDict object
    for name, param in params.items():
        # 如果视图url函数存在命名关键字参数，且默认值为空，获取它的key（参数名）
        if param.kind == inspect.Parameter.KEYWORD_ONLY and param.default == inspect.Parameter.empty:
            args.append(name)
    return tuple(args)


def get_named_kw_args(fn):
    """
    # 获取命名关键词参数名称
    :param fn:the name of func
    :return:the list of named kwargs
    """
    args = []
    params = inspect.signature(fn).parameters  # OrderedDict object
    for name, param in params.items():
        # 如果视图url函数存在命名关键字参数，获取它的key（参数名）
        if param.kind == inspect.Parameter.KEYWORD_ONLY:
            args.append(name)
    return tuple(args)


def has_named_kw_args(fn):
    """
    判断是否有命名关键词参数
    :param fn:the name of func
    :return:
    """
    params = inspect.signature(fn).parameters  # OrderedDict object
    for name, param in params.items():
        if param.kind == inspect.Parameter.KEYWORD_ONLY:
            return True


def has_var_kw_arg(fn):
    """
    判断是否有可变关键词参数
    :param fn:the name of func
    :return:
    """
    params = inspect.signature(fn).parameters  # OrderedDict object
    params = inspect.signature(fn).parameters  # OrderedDict object
    for name, param in params.items():
        if param.kind == inspect.Parameter.VAR_KEYWORD:
            return True


def has_request_arg(fn):
    """
    判断是否有名字为"request"的参数，且在最后，否则报错
    :param fn:the name of func
    :return:
    """
    sig = inspect.signature(fn)  # OrderedDict object
    params = sig.parameters
    found = False
    for name, param in params.items():
        if name == 'request':
            found = True
            continue
        if found and (
            param.kind != inspect.Parameter.VAR_KEYWORD and
            param.kind != inspect.Parameter.KEYWORD_ONLY and
            param.kind != inspect.Parameter.VAR_POSITIONAL

        ):
            raise ValueError('request parameter must be the last named parameter in function:%s%s'
                             % (fn.__name__, str(sig)))

    return found


class RequestHandler(object):
    """
    从request中获取必要的参数，调用URL函数，然后把结果转换为web.Response对象
    request是经aiohttp包装后的对象,其本质是一个HTTP请求,由三部分组成：request line, request headers and request payload。
    HTTP请求的格式如下所示：
    <method> <request-url> <version>，request line,用来说明请求类型、要访问的资源以及使用的HTTP版本
    <headers> ，request headers用来说明服务器要使用的附加信息
    <blank line>
    <entity-body></entity-body>,request payload,协议规定 POST 提交的数据必须放在消息主体（entity-body）中
    </headers></version></request-url></method>

    我们需要的参数包含在请求体以及请求行URI中。 request对象封装了HTTP请求，可以通过request的属性调取值。
    参考资料：aiohttp.web.Request

    """

    def __init__(self, app, fn):
        """
        init class
        :param app: the name of app
        :param fn:the name of func
        """
        self._app = app
        self._func = fn
        self._has_request_arg = has_request_arg(fn)
        self._has_var_kw_arg = has_var_kw_arg(fn)
        self._has_named_kw_args = has_named_kw_args(fn)
        self._named_kw_args = get_named_kw_args(fn)
        self._required_kw_args = get_required_kw_args(fn)

    async def __call__(self, request):
        """
        把实例对象看作函数一样进行调用
        RequestHandler需要处理以下问题：
        1.确定HTTP请求的方法（’POST’or’GET’）（用request.method获取）
        2.如果为POST方法，根据HTTP请求的content_type字段，选用不同解析方法获取参数。（用request.content_type获取）
        POST常用提交数据方式：application/json、application/x-www-form-urlencoded、multipart/form-data等
        3.如果为GET方法，根据HTTP请求的query_string字段（用request.query_string获取）
        4.将获取的参数经处理，使其完全符合视图url函数接收的参数形式
        5.调用视图url函数，返回执行结果

        # 3.如果kw为空（说明request无请求内容），则将match_info列表里的资源映射给kw；若不为空，把命名关键词参数内容给kw
        # 4.完善_has_request_arg和_required_kw_args属性
        :param request:
        :return:
        """
        # 1.定义kw，用于保存参数
        kwargs = None
        # 2.判断url函数是否存在关键词参数，如果存在根据POST或者GET方法将request请求内容保存到kwargs
        if self._has_named_kw_args or self._has_var_kw_arg or self._required_kw_args:
            if request.method == 'POST':
                logging.debug('POST')
                content_type = request.content_type.lower()  # 小写，便于检查
                if not content_type:  # 如果content_type不存在，返回400错误以及'Missing Content-Type.'
                    # def __init__(self, *, headers=None, reason=None, body=None, text=None, content_type=None):
                    return web.HTTPBadRequest(text='Missing Content-Type.')
                # content-type is application/json
                if content_type.startswith('application/json'):
                    # json格式数据
                    params = await request.json()  # 解析body字段的json数据
                    if not isinstance(params, dict):  # 如果request.json()返回的不是dict对象，返回400错误以及提示语
                        return web.HTTPBadRequest(text='JSON body must be  dict object.')
                    kwargs = params
                elif content_type.startswith('application/x-www-form-urlencoded') \
                        or content_type.startswith('multipart/form-data'):  # form表单请求的编码形式
                    params = await request.post()  # 返回post的内容中解析后的数据。dict-like对象。
                    kwargs = dict(**params)  # 组成dict，统一kw格式
                else:
                    # 对于其他格式数据不予支持，报400错误
                    return web.HTTPBadRequest(text='Unsupported Content-Type: %s' % request.content_type)

            if request.method == 'GET':
                logging.debug('GET')

                # 返回URL的查询字符串，?后的键值。形如mod=forumdisplay& &fid=30&page=1&filter=author&orderby=dateline
                query_string = request.query_string
                # 如果查询字符串不为空，转换为字典类型
                if query_string:
                    kwargs = dict()
                    # parse_qs()解析的字典中value为列表，需要处理
                    for k, v in parse.parse_qs(query_string, True).items():  # keep_blank_values=True
                        kwargs[k] = v[0]

        # 如果kwargs为空，表示request中没有参数
        if kwargs is None:
            # request.match_info返回dict对象,封装了与 request 的 path 和 method 完全匹配的 PlainResource 对象
            # 可变路由中的可变字段{variable}为参数名，传入request请求的path为值
            # 若存在可变路由：/a/{name}/c，可匹配path为：/a/jack/c的request,则request.match_info返回{name = jack}
            kwargs = dict(**request.match_info)
        else:  # request中有参数，按照函数的参数要求，对kwargs中的参数进行处理
            logging.debug('kwargs is %s' % request)
            if not self._has_var_kw_arg and self._has_named_kw_args:  # 只有命名关键字参数
                copy = dict()
                # 只保留命名关键词参数
                for name in self._named_kw_args:
                    if name in kwargs:
                        copy[name] = kwargs[name]
                kwargs = copy  # kw中只存在命名关键词参数
            # 将request.match_info中的参数传入kwargs
            for k, v in request.match_info.items():
                if k in kwargs:
                    logging.warning('Duplicate arg name in named arg and kw args: %s' % k)
                kwargs[k] = v
        # 有请求参数，把请求信息装入参数字典
        if self._has_request_arg:
            kwargs['request'] = request

        # 如果参数中有无默认值的命名关键字参数
        if self._required_kw_args:
            for name in self._required_kw_args:
                # 若未传入参数值，报错。
                if name not in kwargs:
                    return web.HTTPBadRequest(text='Missing argument: %s' % name)

        # 至此，kw为视图函数fn真正能调用的参数
        # request请求中的参数，终于传递给了视图函数
        logging.info('call with args: %s' % str(kwargs))
        try:
            r = await self._func(**kwargs)
            return r
        except APIError as e:
            return dict(error=e.error, data=e.data, message=e.message)


def add_static(app):
    """
    Add static files view
    :param app:
    :return:
    """
    # Warning:
    # use add_static() for development only.
    # In production, static content should be processed by web servers like nginx or apache.
    pass
    # path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
    # css_path = os.path.join(path, 'css', )
    # font_path = os.path.join(path, 'fonts')
    # js_path = os.path.join(path, 'js')
    # img_path = os.path.join(path, 'img')
    # # app.router.add_static('/static/', path)
    # app.router.add_static('/css/', css_path)
    # app.router.add_static('/fonts/', font_path)
    # app.router.add_static('/js/', js_path)
    # app.router.add_static('/img/', img_path)
    #
    # """
    #     def add_static(self, prefix, path, *, name=None, expect_handler=None,
    #                chunk_size=256 * 1024,
    #                show_index=False, follow_symlinks=False,
    #                append_version=False):
    #     Add static files view.
    #
    #     prefix - url prefix
    #     path - folder with files
    #     aiohttp.web_urldispatcher
    # """
    # logging.info('add static files view %s -> %s' % ('/static/', path))
    # logging.info('add static files view %s -> %s' % ('/css/', css_path))
    # logging.info('add static files view %s -> %s' % ('/fonts/', font_path))
    # logging.info('add static files view %s -> %s' % ('/js/', js_path))
    # logging.info('add static files view %s -> %s' % ('/img/', img_path))


def add_route(app, fn):
    """
    注册视图url处理函数

    :param app:the web.application
    :param fn:the url func
    :return:None
    """
    method = getattr(fn, '__method__', None)
    path = getattr(fn, '__route__', None)

    # method and path不能为None，否则报错
    if method is None or (path is None):
        raise ValueError('@get or @post not defined in %s.' % str(fn))

    # 判断URL处理函数是否协程并且是生成器
    if not asyncio.iscoroutinefunction(fn) and (not inspect.isgeneratorfunction(fn)):
        # 将fn转变成协程
        fn = asyncio.coroutine(fn)
    logging.info(
        'add route %s %s -> %s(%s)'
        % (method, path, fn.__name__, ', '.join(inspect.signature(fn).parameters.keys())))

    app.router.add_route(method, path, RequestHandler(app, fn))
    """
     def add_route(self, method, path, handler,
                   *, name=None, expect_handler=None):
         resource = self.add_resource(path, name=name)
         return resource.add_route(method, handler,
                                   expect_handler=expect_handler)
    """


# 最后一步，把很多次add_route()注册的调用：
#   add_route(app, handles.index)
#   add_route(app, handles.blog)
#   add_route(app, handles.create_comment)
#   ...
#
# 变成自动扫描：
#   自动把handler模块的所有符合条件的函数注册了:
#   add_routes(app, 'handlers')

def add_routes(app, module_name):
    """
    导入模块，批量注册视图url处理函数
    :param app:
    :param module_name:模块名称
    :return:None
    """
    n = module_name.rfind('.')
    if n == (-1):  # 没有.，导入整个模块
        mod = __import__(module_name, globals(), locals())  # 等价于import module_name
        """
        __import__(name, globals=None, locals=None, fromlist=(), level=0) -> module

        Import a module. Because this function is meant for use by the Python
        interpreter and not for general use it is better to use
        importlib.import_module() to programmatically import a module.

        The globals argument is only used to determine the context;
        they are not modified.  The locals argument is unused.  The fromlist
        should be a list of names to emulate ``from name import ...'', or an
        empty list to emulate ``import name''.
        When importing a module from a package, note that __import__('A.B', ...)
        returns package A when fromlist is empty, but its submodule B when
        fromlist is not empty.  Level is used to determine whether to perform 
        absolute or relative imports. 0 is absolute while a positive number
        is the number of parent directories to search relative to the current module.
        """
    else:  # 如果导入模块其中的部分方法
        name = module_name[n+1:]
        mod = getattr(__import__(module_name[:n], globals(), locals(), [name]), name)  # 等价于import module_name.name
    # 注册模块中的所有方法，视图url处理函数
    for attr in dir(mod):
        # 是特殊的方法名，跳过
        if attr.startswith('_'):
            continue
        fn = getattr(mod, attr)
        if callable(fn):
            method = getattr(fn, '__method__', None)
            path = getattr(fn, '__route__', None)
            # 有'__method__' and '__route__'的才注册为视图url处理函数
            if method and path:
                add_route(app, fn)


if __name__ == '__main__':
    pass




