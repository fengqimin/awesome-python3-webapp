# -*- coding: utf-8 -*-

"""
Day 4 - 编写Model
阅读: 71713

有了ORM，我们就可以把Web App需要的3个表用Model表示出来：
"""
import time, uuid
from orm import Model, StringField, BooleanField, FloatField, TextField


def next_id():
    return '%015d%s000' % (int(time.time() * 1000), uuid.uuid4().hex)


if __name__ == '__main__':
    print(next_id())

    model = Model(name='Frank')
    model['key'] = next_id()
    print(model)
