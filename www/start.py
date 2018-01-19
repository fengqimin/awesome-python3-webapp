# -*- coding: utf-8 -*-

# import app
import logging

logging.basicConfig(level=logging.DEBUG)
logging.debug('debug message')
logging.info('info message')
logging.warning('warning message')
logging.error('error message')
logging.critical('critical message')
# local_ip = socket.gethostbyname(socket.gethostname())  # 得到本地ip

# event_loop = asyncio.get_event_loop()
# # event_loop.run_until_complete(app.init(event_loop))
# event_loop.run_forever()

# INFO: root:rows
# returned: 1, result is [{'id': '001516033272829693a2b07be12495a9664daccdb943d80000',
#                          'user_id': '001516200548170aa45533e688446d9868fac9e7f0eb069000', 'user_name': 'fengqimin',
#                          'user_image': 'about:blank', 'name': 'Test Blog',
#                          'summary': ' INSERT inserts new rows into an existing table. ',
#                          'content': 'The INSERT ... VALUES and INSERT ... SET forms of the statement insert rows based on explicitly specified values. The INSERT ... SELECT form inserts rows selected from another table or tables. INSERT with an ON DUPLICATE KEY UPDATE clause enables existing rows to be updated if a row to be inserted would cause a duplicate value in a UNIQUE index or PRIMARY KEY. ',
#                          'created_at': 1516031862.5230603}]
# [
# {'id': '001516200548170aa45533e688446d9868fac9e7f0eb069000',
# 'email': 'fengqimin@msn.com',
#   'passwd': '60dc68d7f8144c1f2309eefefe46883019360d31',
# 'admin': 0,
# 'name': 'fengqimin',
#   'image': 'http://www.gravatar.com/avatar/3427f88ce4c6fcd91d737543abf7bba3?d=mm&s=120',
#   'created_at': 1516200548.17015}]
