# -*- coding: utf-8 -*-

"""
Day 4 - 编写Model
阅读: 71713

有了ORM，我们就可以把Web App需要的3个表用Model表示出来：
Models for user, blog, comment.
"""
import time
import uuid
from orm import Model, StringField, BooleanField, FloatField, TextField, IntegerField


def next_id():
    return '%015d%s000' % (int(time.time() * 1000), uuid.uuid4().hex)


class User(Model):
    """ """

    __table__ = 'users'

    id = StringField(primary_key=True, default=next_id, ddl='varchar(50)')
    email = StringField(ddl='varchar(50)')
    passwd = StringField(ddl='varchar(50)')
    admin = BooleanField(default=False)
    name = StringField(ddl='varchar(50)')
    image = StringField(ddl='varchar(500)')
    created_at = FloatField(default=time.time)


"""
在编写ORM时，给一个Field增加一个default参数可以让ORM自己填入缺省值，非常方便。并且，缺省值可以作为函数对象传入，在调用save()时自动计算。

例如，主键id的缺省值是函数next_id，创建时间created_at的缺省值是函数time.time，可以自动设置当前日期和时间。

日期和时间用float类型存储在数据库中，而不是datetime类型，这么做的好处是不必关心数据库的时区以及时区转换问题，排序非常简单，
显示的时候，只需要做一个float到str的转换，也非常容易。
"""


class Blog(Model):
    __table__ = 'blogs'

    id = StringField(primary_key=True, default=next_id, ddl='varchar(50)')
    user_id = StringField(ddl='varchar(50)')
    user_name = StringField(ddl='varchar(50)')
    user_image = StringField(ddl='varchar(500)')
    name = StringField(ddl='varchar(50)')
    summary = StringField(ddl='varchar(200)')
    content = TextField()
    created_at = FloatField(default=time.time)


class Comment(Model):
    __table__ = 'comments'

    id = StringField(primary_key=True, default=next_id, ddl='varchar(50)')
    blog_id = StringField(ddl='varchar(50)')
    user_id = StringField(ddl='varchar(50)')
    user_name = StringField(ddl='varchar(50)')
    user_image = StringField(ddl='varchar(500)')
    content = TextField()
    created_at = FloatField(default=time.time)


if __name__ == '__main__':
    from orm import create_pool
    import asyncio
    from config import configs

    async def test(loop):
        await create_pool(loop=loop, **configs.db)
        print('create_pool')
        users = await User.findall()
        for user in users:
            print(user)


    loop = asyncio.get_event_loop()
    loop.run_until_complete(test(loop))
    loop.run_forever()
    loop.stop()




