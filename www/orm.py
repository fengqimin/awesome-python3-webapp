# -*- coding: utf-8 -*-

import logging, asyncio
import aiomysql


def log(sql, args=()):
    """

    :param sql:``str`` 执行的sql语句
    :param args:``tuple`` SQL参数
    :return:
    """
    logging.info('sql:%s' % sql)


# 创建连接池
async def create_pool(loop, **kwargs):
    """
    我们需要创建一个全局的连接池，每个HTTP请求都可以从连接池中直接获取数据库连接。使用连接池的好处是不必频繁地打开和关闭数据库连接，
    而是能复用就尽量复用。连接池由全局变量__pool存储，缺省情况下将编码设置为utf8，自动提交事务：
    :param loop:
    :param kwargs:
    :return:
    """
    logging.info('create database connection pool...')
    global __pool
    __pool = await aiomysql.create_pool(
        host=kwargs.get('host', 'localhost'),
        port=kwargs.get('port', 3306),
        user=kwargs.get('user'),
        password=kwargs['password'],
        db=kwargs['db'],
        charset=kwargs.get('charset', 'utf8'),
        autocommit=kwargs.get('autocommit', True),
        maxsize=kwargs.get('maxsize', 10),
        minsize=kwargs.get('minsize', 1),
        loop=loop
    )


# Select
async def select(sql, args, size=None):
    """
    要执行SELECT语句，我们用select函数执行，需要传入SQL语句和SQL参数：
    :param sql: ``str`` SQL语句
    :param args: ``tuple`` SQL参数
    :param size:``int`` number of rows to return. 如果传入size参数，就通过fetchmany()获取最多指定数量的记录，否则，通过fetchall()获取所有记录。
    :return:``list`` of fetched rows
    """
    log(sql, args)
    global __pool
    async with __pool.get() as conn:
        async with conn.cursor() as cur:
            # SQL语句的占位符是?，而MySQL的占位符是 % s，select() 函数在内部自动替换。
            # 注意要始终坚持使用带参数的SQL，而不是自己拼接SQL字符串，这样可以防止SQL注入攻击。
            await cur.execute(sql.replace('?', '%s'), args or ())
            if size:
                result = await cur.fetchmany(size)
            else:
                result = await cur.fetchall()
        logging.info('rows returned: %s' % len(result))
        return result


# Insert, Update, Delete
# 要执行INSERT、UPDATE、DELETE语句，可以定义一个通用的execute()函数，因为这3种SQL的执行都需要相同的参数，以及返回一个整数表示影响的行数：
async def execute(sql, args, autocommit=True):
    """Executes the given Insert, Update or Delete operation

        Executes the given operation substituting any markers with
        the given parameters.

        For example, getting all rows where id is 5:
          cursor.execute("INSERT INTO Websites (name, url, alexa, country) VALUES (%s,%s,%s,%s)",
          ('百度','https://www.baidu.com/','4','CN'))

    :param sql: ``str`` sql statement
    :param args: ``tuple`` or ``list`` of arguments for sql query
    :param autocommit:``bool``, toggle autocommit
    :return: ``int``, number of rows that has been produced of affected
    """
    log(sql)
    global __pool
    async with __pool.get() as pool_connect:
        if not autocommit:
            pool_connect.begin()
        try:
            async with pool_connect.cursor(aiomysql.DictCursor) as pool_cur:
                await pool_cur.execute(sql.replace('?', '%s'), args)
                rows_affected = pool_cur.rowcount  # Returns the number of rows that has been produced of affected.
        except Exception as e:
            if not autocommit:
                await pool_connect.rollback()
            raise Exception(e)
        return rows_affected

"""
ORM

有了基本的select()和execute()函数，我们就可以开始编写一个简单的ORM了。
设计ORM需要从上层调用者角度来设计。
我们先考虑如何定义一个User对象，然后把数据库表users和它关联起来。

from orm import Model, StringField, IntegerField

class User(Model):
    __table__ = 'users'

    id = IntegerField(primary_key=True)
    name = StringField()

注意到定义在User类中的__table__、id和name是类的属性，不是实例的属性。
所以，在类级别上定义的属性用来描述User对象和表的映射关系，而实例属性必须通过__init__()方法去初始化，所以两者互不干扰：

# 创建实例:
user = User(id=123, name='Michael')
# 存入数据库:
user.insert()
# 查询所有User对象:
users = User.findAll()
"""


# Field和各种Field子类，用于映射各种数据字段：
class Field(object):
    def __init__(self, name, column_type, primary_key, default):
        """
        各种数据字段的基类
        :param name:``str``字段名称
        :param column_type:``str`` the type of field
        :param primary_key:``bool`` 是否为主键
        :param default:
        """
        self.name = name
        self.column_type = column_type
        self.primary_key = primary_key
        self.default = default

    def __str__(self):
        return '<%s, %s:%s>' % (self.__class__.__name__, self.column_type, self.name)

    def __getattr__(self, item):
        for item in ['name', 'column_type', 'primary_key', 'default']:
            return self[item]


def create_args_string(num):
    """
    create args string
    :param num: ``int`` the number of args
    :return:``list'' of args of string
    """
    L = []
    for n in range(num):
        L.append('?')
    return ', '.join(L)


# BIGINT 8 字节 	(-9 233 372 036 854 775 808，9 223 372 036 854 775 807) 	(0，18 446 744 073 709 551 615) 	极大整数值
class IntegerField(Field):
    def __init__(self, name=None, primary_key=False, default=0):
        super().__init__(name, 'bigint', primary_key, default)


# VARCHAR 	0-65535 字节 	变长字符串
class StringField(Field):
    def __init__(self, name=None, primary_key=False, default=None, ddl='varchar(100)'):
        super().__init__(name, ddl, primary_key, default)


# BOOL / BOOLEAN 布尔类型
class BooleanField(Field):
    def __init__(self, name=None, default=None):
        super().__init__(name, 'boolean', False, default)


# REAL就是DOUBLE ，如果SQL服务器模式包括REAL_AS_FLOAT选项，REAL是FLOAT的同义词而不是DOUBLE的同义词。
class FloatField(Field):
    def __init__(self, name=None, primary_key=False, default=0.0):
        super().__init__(name, 'real', primary_key, default)


# text 	string长度+2字节 	字符串，最大长度为0-65535个字节
class TextField(Field):
    def __init__(self, name=None, default=None):
        super().__init__(name, 'text', False, default)


class ModelMetaclass(type):
    """
    the metaclass of Model
    这样，任何继承自Model的类（比如User），会自动通过ModelMetaclass扫描映射关系，并存储到自身的类属性如__table__、__mappings__中。


    """
    def __new__(cls, name, bases, attrs):
        """

        :param name:``str`` the name of table
        :param bases:
        :param attrs:``dict``
        :return:
        """
        # 排除Model类本身
        if name == 'Model':
            return type.__new__(cls, name, bases, attrs)

        # 获取table名称:
        table_name = attrs.get('__table__', None) or name
        logging.info('found model: %s (table: %s)' % (name, table_name))

        # 获取所有的属性名和主键名:
        mappings = dict()
        fields = []
        primary_key = None
        for k, v in attrs.items():
            if isinstance(v, Field):  # 如果是Field类就保存到映射关系中
                mappings[k] = v
                logging.info(' found mapping %s->%s' % (k, v))
                # 找到主键:
                if v.primary_key:
                    # 检查主键是否重复
                    if primary_key:
                        raise Exception('Duplicate primary key for field: %s' % k)
                    primary_key = k
                else:
                    fields.append(k)
        # 没有找到主键
        if not primary_key:
            raise Exception('Primary key not found.')
        # 清空属性字典中已找到的Field
        for k in mappings.keys():
            attrs.pop(k)

        # 把fields列表中的内容添加``后映射到escaped_fields列表中
        escaped_fields = list(map(lambda f: '`%s`' % f, fields))

        # 保存属性字典
        attrs['__mappings__'] = mappings  # 保存属性和列的映射关系
        attrs['__table__'] = name  # 假设表名和类名一致
        attrs['__primary_key__'] = primary_key   # 主键属性名
        attrs['__fields__'] = fields  # 除主键外的属性名

        # 构造默认的SELECT, INSERT, UPDATE和DELETE语句:
        attrs['__select__'] = 'select `%s`, %s from `%s`' % (primary_key, ', '.join(escaped_fields), table_name)
        attrs['__insert__'] = 'insert into `%s` (%s, `%s`) values (%s)' % (
            table_name, ', '.join(escaped_fields),
            primary_key, create_args_string(len(escaped_fields) + 1))
        attrs['__update__'] = 'update `%s` set %s where `%s`=?' % (
            table_name, ', '.join(map(lambda f: '`%s`=?' % (mappings.get(f).name or f), fields)), primary_key)
        attrs['__delete__'] = 'delete from `%s` where `%s`=?' % (table_name, primary_key)
        # print(attrs.items())
        return type.__new__(cls, name, bases, attrs)


class Model(dict, metaclass=ModelMetaclass):
    """
    然后，我们往Model类添加class方法，就可以让所有子类调用class方法：
    class Model(dict):

        ...

        @classmethod
        @asyncio.coroutine
        def find(cls, pk):
            ' find object by primary key. '
            rs = yield from select('%s where `%s`=?' % (cls.__select__, cls.__primary_key__), [pk], 1)
            if len(rs) == 0:
                return None
            return cls(**rs[0])

    User类现在就可以通过类方法实现主键查找：
    user = yield from User.find('123')
    往Model类添加实例方法，就可以让所有子类调用实例方法：
    """

    def __init__(self, **kw):
        super(Model, self).__init__(**kw)

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(r"'Model' object has no attribute '%s'" % key)

    def __setattr__(self, key, value):
        self[key] = value

    def getValue(self, key):
        return getattr(self, key, None)

    def getValueOrDefault(self, key):
        value = getattr(self, key, None)
        if value is None:
            field = self.__mappings__[key]
            if field.default is not None:
                value = field.default() if callable(field.default) else field.default
                logging.debug('using default value for %s: %s' % (key, str(value)))
                setattr(self, key, value)
        return value

    @classmethod
    async def findAll(cls, where=None, args=None, **kw):
        """ find objects by where clause. """
        sql = [cls.__select__]
        if where:
            sql.append('where')
            sql.append(where)
        if args is None:
            args = []
        orderBy = kw.get('orderBy', None)
        if orderBy:
            sql.append('order by')
            sql.append(orderBy)
        limit = kw.get('limit', None)
        if limit is not None:
            sql.append('limit')
            if isinstance(limit, int):
                sql.append('?')
                args.append(limit)
            elif isinstance(limit, tuple) and len(limit) == 2:
                sql.append('?, ?')
                args.extend(limit)
            else:
                raise ValueError('Invalid limit value: %s' % str(limit))
        rs = await select(' '.join(sql), args)
        return [cls(**r) for r in rs]

    @classmethod
    async def findNumber(cls, selectField, where=None, args=None):
        ' find number by select and where. '
        sql = ['select %s _num_ from `%s`' % (selectField, cls.__table__)]
        if where:
            sql.append('where')
            sql.append(where)
        rs = await select(' '.join(sql), args, 1)
        if len(rs) == 0:
            return None
        return rs[0]['_num_']

    @classmethod
    async def find(cls, pk):
        """ find object by primary key. """
        rs = await select('%s where `%s`=?' % (cls.__select__, cls.__primary_key__), [pk], 1)
        if len(rs) == 0:
            return None
        return cls(**rs[0])

    async def save(self):
        args = list(map(self.getValueOrDefault, self.__fields__))
        args.append(self.getValueOrDefault(self.__primary_key__))
        rows = await execute(self.__insert__, args)
        if rows != 1:
            logging.warning('failed to insert record: affected rows: %s' % rows)

    async def update(self):
        args = list(map(self.getValue, self.__fields__))
        args.append(self.getValue(self.__primary_key__))
        rows = await execute(self.__update__, args)
        if rows != 1:
            logging.warning('failed to update by primary key: affected rows: %s' % rows)

    async def remove(self):
        args = [self.getValue(self.__primary_key__)]
        rows = await execute(self.__delete__, args)
        if rows != 1:
            logging.warning('failed to remove by primary key: affected rows: %s' % rows)


if __name__ == '__main__':
    f = IntegerField(name='id', default=500)
    print(f, f.default)

    import pymysql
    conn = pymysql.connect(
        host='localhost',
        port=3306,
        user='root',
        password='PEP-3156/tulip',
        db='mysql',
        charset='utf8'
    )
    cur = conn.cursor()
    cur.execute("select version()")
    for i in cur:
        print(i)
    cur.execute("use awesome")
    cur.execute("select * from users")
    print(cur.fetchall())
    cur.close()
    conn.close()


