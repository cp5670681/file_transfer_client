import os
import logging
import logging.handlers

"""
日志模块，需要打印日志时，导入该文件的logger
消息严重程序依次递增
Log module, when you need to print the log, import the logger of this file

logger.debug(message)       debug log
logger.info(message)        info log
logger.warning(message)     warning log
logger.error(message)       error log
logger.critical(message)    critical log
"""

logger = logging.getLogger()
logger.setLevel(logging.INFO)

logpath = 'logs'

# If the logs folder does not exist, create it.
# 如果logs文件夹不存在，创建文件夹
if not os.path.exists(logpath):
    os.makedirs(logpath)

# At midnight every day, separate the log file of the previous day and save the logs by day
# 每天午夜，把前一天的日志文件分离出来，实现日志按天保存
rf_handler = logging.handlers.TimedRotatingFileHandler(
    filename=os.path.join(logpath, 'myapp.log'),
    when='midnight', interval=1, encoding='utf-8'
)

# 日志格式
# Log format
logging_format = logging.Formatter(
    '%(asctime)s - %(pathname)s[line:%(lineno)d] - %(levelname)s: %(message)s')
rf_handler.setFormatter(logging_format)
logger.addHandler(rf_handler)


