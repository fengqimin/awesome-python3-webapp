# -*- coding: utf-8 -*-

import asyncio
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
