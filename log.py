#-*- coding: utf-8 -*-
import logging 
import logging.handlers

fileMaxByte = 1024*1024*10 # 10MB

def setupCustomLogger(name):
  formatter = logging.Formatter('[%(levelname)s|%(filename)s:%(lineno)s] %(asctime)s > %(message)s')
  fileHandler = logging.handlers.RotatingFileHandler('./bot.log', maxBytes=fileMaxByte, backupCount=10)
  fileHandler.setFormatter(formatter) 
  streamHandler = logging.StreamHandler()
  streamHandler.setFormatter(formatter)

  logger = logging.getLogger(name)
  logger.setLevel(logging.DEBUG)
  logger.addHandler(fileHandler)
  logger.addHandler(streamHandler)
  return logger

