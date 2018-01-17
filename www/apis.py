# -*- coding: utf-8 -*-

"""
JSON API definition.
"""

# import json, logging, inspect, functools


class Page(object):
    """
    Page object for display pages.
    """
    def __init__(self, item_count, page_index=1, page_size=10):
        """
        Init Pagination by item_count, page_index and page_size.
        分页显示
        :param item_count:需要显示的内容数量
        :param page_index:当前在哪页
        :param page_size:每页显示的数量

        """
        self.item_count = item_count
        self.page_size = page_size
        self.page_count = item_count // page_size + (1 if item_count % page_size > 0 else 0)
        if (item_count == 0) or (page_index > self.page_count):
            self.offset = 0  # 内容偏移量
            self.page_index = 1
            self.limit = 0  # 每页显示的内容上限
        else:
            self.page_index = page_index
            self.offset = self.page_size * (page_index - 1)
            self.limit = self.page_size
        self.has_next = self.page_count > self.page_index
        self.has_previous = self.page_index > 1

    def __str__(self):
        return 'item_count: %s, page_count: %s, page_index: %s, page_size: %s, offset: %s, limit: %s' \
               % (self.item_count, self.page_count, self.page_index, self.page_size, self.offset, self.limit)


# 我们需要对Error进行处理，因此定义一个APIError，这种Error是指API调用时发生了逻辑错误（比如用户不存在），
# 其他的Error视为Bug，返回的错误代码为internalerror。
# 客户端调用API时，必须通过错误代码来区分API调用是否成功。
# 错误代码是用来告诉调用者出错的原因。很多API用一个整数表示错误码，这种方式很难维护错误码，客户端拿到错误码还需要查表得知错误信息。
# 更好的方式是用字符串表示错误代码，不需要看文档也能猜到错误原因。
class APIError(Exception):
    """
    the base APIError。
    """
    def __init__(self, error, data='', message=''):
        super(APIError, self).__init__(message)
        self.error = error
        self.data = data
        self.message = message


class APIValueError(APIError):
    """
    Indicate the input value has error or invalid. The data specifies the error field of input form.
    """
    def __init__(self, error_field, message=''):
        super(APIValueError, self).__init__('value:not found', error_field, message)


class APIResourceNotFoundError(APIError):
    """
    Indicate the resource was not found. The data specifies the resource name.
    """
    def __init__(self, resource_name, message=''):
        super(APIResourceNotFoundError, self).__init__('resource:not found', resource_name, message)


class APIPermissionError(APIError):
    """
    Indicate the api has no permission.
    """
    def __init__(self, message=''):
        super(APIPermissionError, self).__init__('permission:forbidden', 'permission', message)


if __name__ == '__main__':
    p1 = Page(0, 1)
    print(p1)

    p2 = Page(3, 1)
    print(p2)

    p3 = Page(91, 10, 10)
    print(p3)
