# -*- coding: utf-8 -*-

"""
url handlers
"""
import hashlib
import json
import logging
import re
import time

from aiohttp import web

from apis import Page, APIError, APIValueError, APIPermissionError
from config import configs
from coroweb import get, post
from models import User, Comment, Blog, next_id


# import markdown2


def check_admin(request):
    """
    Check whether user is an administrator
    :param request:
    :return:
    """
    if request.__user__ is None or not request.__user__.admin:
        raise APIPermissionError()


def get_page_index(page_str):
    """
    获取当前访问页
    :param page_str:
    :return:page_index
    """
    p = 1
    try:
        p = int(page_str)
    except ValueError as e:
        pass
    if p < 1:
        p = 1
    return p


COOKIE_NAME = 'awesession'
_COOKIE_KEY = configs.session.secret


def user2cookie(user, max_age):
    """
    计算加密cookie
    Generate cookie str by user.
    :param user:
    :param max_age:
    :return:
    """
    # build cookie string by: id-expires-sha1
    expires = str(int(time.time() + max_age))
    s = '%s-%s-%s-%s' % (user.id, user.passwd, expires, _COOKIE_KEY)
    L = [user.id, expires, hashlib.sha1(s.encode('utf-8')).hexdigest()]
    return '-'.join(L)


async def cookie2user(cookie_str):
    """
    解密cookie
    Parse cookie and load user if cookie is valid.
    :param cookie_str:
    :return:
    """
    if not cookie_str:
        return None
    try:
        L = cookie_str.split('-')
        if len(L) != 3:
            return None
        uid, expires, sha1 = L
        if int(expires) < time.time():
            return None
        user = await User.find(uid)
        if user is None:
            return None
        s = '%s-%s-%s-%s' % (uid, user.passwd, expires, _COOKIE_KEY)
        if sha1 != hashlib.sha1(s.encode('utf-8')).hexdigest():
            logging.info('invalid sha1')
            return None
        user.passwd = '******'
        return user
    except Exception as e:
        logging.exception(e)
        return None


def text2html(text):
    lines = map(lambda s: '<p>%s</p>' % s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'),
                filter(lambda s: s.strip() != '', text.split('\n')))
    return ''.join(lines)


@get('/')
async def index(*, page='1'):
    page_index = get_page_index(page)
    num = await Blog.findNumber('count(id)')
    page = Page(num)
    if num == 0:
        blogs = []
    else:
        blogs = await Blog.findall(orderBy='created_at desc', limit=(page.offset, page.limit))
    print('@get index')
    return {
        '__template__': 'blogs.html',
        'page': page,
        'blogs': blogs
    }


@get('/blog/{id}')
async def get_blog(id):
    blog = await Blog.find(id)
    comments = await Comment.findall('blog_id=?', [id], orderBy='created_at desc')
    for c in comments:
        c.html_content = text2html(c.content)
    # blog.html_content = markdown2.markdown(blog.content)
    return {
        '__template__': 'blog.html',
        'blog': blog,
        'comments': comments
    }


@get('/register')
def register(request):
    return {
        '__template__': 'register.html',
    }


@get('/api/users')
async def api_get_users(*, page='1'):
    # page_index = get_page_index(page)
    # item_count = await User.findNumber('count(id)')
    # logging.debug('page_index is %d,item_count is  %d' % (page_index, item_count))
    #
    # p = Page(item_count, page_index)
    # if item_count == 0:
    #     return dict(page=p, users=())
    # users = await User.findall(orderBy='created_at desc', limit=(p.offset, p.limit))
    # for u in users:
    #     u.passwd = '******'
    # return dict(page=p, users=users)
    users = await User.findall(orderBy='created_at desc')
    for u in users:
        u.passwd = '******'
    return dict(users=users)


@post('/api/users')
async def api_register_user(*, email, name, passwd):
    """
    用户注册
    用户管理是绝大部分Web网站都需要解决的问题。用户管理涉及到用户注册和登录。
    用户注册相对简单，我们可以先通过API把用户注册这个功能实现了：
    :param email:
    :param name:
    :param passwd:
    :return:
    """
    _RE_EMAIL = re.compile(r'^[a-z0-9\.\-\_]+\@[a-z0-9\-\_]+(\.[a-z0-9\-\_]+){1,4}$')
    _RE_SHA1 = re.compile(r'^[0-9a-f]{40}$')
    if not name or not name.strip():
        raise APIValueError('name')
    if not email or not _RE_EMAIL.match(email):
        raise APIValueError('email')
    if not passwd or not _RE_SHA1.match(passwd):
        raise APIValueError('passwd')
    users = await User.findall('email=?', [email])
    # 邮箱不能重复
    if len(users) > 0:
        raise APIError('register:failed', 'email', 'Email is already exist.')
    uid = next_id()
    sha1_passwd = '%s:%s' % (uid, passwd)
    user = User(
        id=uid,
        name=name.strip(),
        email=email,
        passwd=hashlib.sha1(sha1_passwd.encode('utf-8')).hexdigest(),
        image='http://www.gravatar.com/avatar/%s?d=mm&s=120' % hashlib.md5(email.encode('utf-8')).hexdigest()
    )  # 密码用sha1加密
    await user.save()
    # make session cookie:
    r = web.Response()
    r.set_cookie(COOKIE_NAME, user2cookie(user, 86400), max_age=86400, httponly=True)
    user.passwd = '******'
    r.content_type = 'application/json'
    r.body = json.dumps(user, ensure_ascii=False).encode('utf-8')
    return r


@get('/signin')
def signin(request):
    return {
        '__template__': 'signin.html',
    }


@post('/api/authenticate')
async def authenticate(*, email, passwd):
    """
    用户登录API
    用户登录比用户注册复杂。由于HTTP协议是一种无状态协议，而服务器要跟踪用户状态，就只能通过cookie实现。
    大多数Web框架提供了Session功能来封装保存用户状态的cookie。

    Session的优点是简单易用，可以直接从Session中取出用户登录信息。
    Session的缺点是服务器需要在内存中维护一个映射表来存储用户登录信息，如果有两台以上服务器，就需要对Session做集群，
    因此，使用Session的Web App很难扩展。

    我们采用直接读取cookie的方式来验证用户登录，每次用户访问任意URL，都会对cookie进行验证，
    这种方式的好处是保证服务器处理任意的URL都是无状态的，可以扩展到多台服务器。

    由于登录成功后是由服务器生成一个cookie发送给浏览器，所以，要保证这个cookie不会被客户端伪造出来。
    实现防伪造cookie的关键是通过一个单向算法（例如SHA1），举例如下：
    当用户输入了正确的口令登录成功后，服务器可以从数据库取到用户的id，并按照如下方式计算出一个字符串：
        "用户id" + "过期时间" + SHA1("用户id" + "用户口令" + "过期时间" + "SecretKey")

    当浏览器发送cookie到服务器端后，服务器可以拿到的信息包括：
        用户id
        过期时间
        SHA1值
    如果未到过期时间，服务器就根据用户id查找用户口令，并计算：
        SHA1("用户id" + "用户口令" + "过期时间" + "SecretKey")
    并与浏览器cookie中的哈希进行比较，如果相等，则说明用户已登录，否则，cookie就是伪造的。
    这个算法的关键在于SHA1是一种单向算法，即可以通过原始字符串计算出SHA1结果，但无法通过SHA1结果反推出原始字符串。
    所以登录API可以实现如下：
    :param email:
    :param passwd:
    :return:
    """
    if not email:
        raise APIValueError('email', 'Invalid email.')
    if not passwd:
        raise APIValueError('passwd', 'Invalid password.')
    users = await User.findall('email=?', [email])
    if len(users) == 0:
        raise APIValueError('email', 'Email not exist.')
    user = users[0]
    # check passwd:
    sha1 = hashlib.sha1()
    sha1.update(user.id.encode('utf-8'))
    sha1.update(b':')
    sha1.update(passwd.encode('utf-8'))
    if user.passwd != sha1.hexdigest():
        raise APIValueError('passwd', 'Invalid password.')
    # authenticate ok, set cookie:
    r = web.Response()
    r.set_cookie(COOKIE_NAME, user2cookie(user, 86400), max_age=86400, httponly=True)
    user.passwd = '******'
    r.content_type = 'application/json'
    r.body = json.dumps(user, ensure_ascii=False).encode('utf-8')
    return r


