# -*- coding: utf-8 -*-

"""
部署到服务器时，通常需要修改数据库的host等信息，直接修改config_default.py不是一个好办法，
更好的方法是编写一个config_override.py，用来覆盖某些默认设置：
"""
# config_override.py

configs = {
    'db': {
        'host': '127.0.0.1'
    }
}
