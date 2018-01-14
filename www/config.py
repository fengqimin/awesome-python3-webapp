# -*- coding: utf-8 -*-

"""
把config_default.py作为开发环境的标准配置，把config_override.py作为生产环境的标准配置，
我们就可以既方便地在本地开发，又可以随时把应用部署到服务器上。

应用程序读取配置文件需要优先从config_override.py读取。为了简化读取配置文件，可以把所有配置读取到统一的config.py中：
"""
# config.py
import config_default


# 为了简化操作，给重载dict类，添加x.y操作
class MyDict(dict):

    def __init__(self, names=(), values=(), **kw):
        super(MyDict, self).__init__(**kw)
        for k, v in zip(names, values):
            self[k] = v
            print(k, v)

    def __getattr__(self, key):
        try:
            return self[key]
        except AttributeError:
            raise AttributeError(r"'Dict' object has no attribute '%s'" % key)

    def __setattr__(self, key, value):
        self[key] = value

    @classmethod
    def tomydict(cls, d):
        pass


# 用把override中的内容合并到default中
def merge(default, override):
    d = {}
    for k, v in default.items():
        # 如果在override中有default中存在的key值
        if k in override:
            # 如果key对应的value值还是一个字典，就递归调用
            if isinstance(v, dict):
                d[k] = merge(v, override[k])
            else:
                d[k] = override[k]
        else:
            d[k] = default[k]

    return d


def toDict(d):
    D = MyDict()
    for k, v in d.items():
        D[k] = toDict(v) if isinstance(v, dict) else v
    return D


configs = config_default.configs

try:
    import config_override
    configs = merge(configs, config_override.configs)
except ImportError:
    pass

configs = toDict(configs)
if __name__ == '__main__':
    print(configs)
    print(configs.db.host)
