#-*- coding: utf-8 -*-
import sys
import os
import log
import logging
import fnmatch
import re
import docclass

from pprint import pprint
from random import randint
import telepot
import telepot.helper
from telepot.delegate import per_chat_id, create_open, per_application
from telepot.namedtuple import (
  ReplyKeyboardMarkup, KeyboardButton, 
  ReplyKeyboardHide, ForceReply, 
  InlineKeyboardMarkup, InlineKeyboardButton,
  InlineQueryResultArticle, InlineQueryResultPhoto, 
  InputTextMessageContent 
)

reload(sys)
sys.setdefaultencoding('utf-8')

class FileClassifier(telepot.helper.Monitor):
  def __init__(self, seed_tuple, classifier, srcPath, destPath):
    super(FileClassifier, self).__init__(seed_tuple, capture=[{'_': lambda msg: True}])
    self.cl = cl
    self.srcPath = srcPath
    self.destPath = destPath
    self.mode = ''
    self.edtYESNO = None
    self.kbdYESNO = InlineKeyboardMarkup(
        inline_keyboard=[
          [
            InlineKeyboardButton(text='YES', callback_data='YES'),
            InlineKeyboardButton(text='NO', callback_data='NO'),
          ],
        ])
    self.kbdMainFolder = InlineKeyboardMarkup(
        inline_keyboard=[
          [InlineKeyboardButton(text='Drama', callback_data='Drama')],
          [InlineKeyboardButton(text='Movies', callback_data='Movies')],
          [InlineKeyboardButton(text='Entertainment', callback_data='Entertainment')],
          [InlineKeyboardButton(text='Documentary', callback_data='Documentary')],
        ])

  def filefeeder(self):
    fileinfo = {}
    for root, dirnames, filenames in os.walk(self.srcPath):
      for filename in filenames:
        if filename.endswith(('.avi', '.mp4', '.mkv', '.smi', '.srt')):
          os.rename(os.path.join(root, filename), 
            os.path.join(root, filename.replace(' ', '_')))
          fileinfo['name'] = filename.replace(' ', '_')
          fileinfo['srcPath'] = os.path.join(root, filename.replace(' ', '_'))
          return fileinfo
    return None

  def filemove(self, fileinfo):
    # print(fileinfo['srcPath'])
    # print(fileinfo['destPath'])
    command = ' '.join(['mv', fileinfo['srcPath'], fileinfo['destPath']])
    print command
    os.system(command)
    # os.rename(src, dest)

  def kbdSubFolder(self, path):
    print(path)
    l = []
    for root, dirnames, filenames in os.walk(path):
      for dirname in dirnames:
        print(dirname)
        l.append([InlineKeyboardButton(text=dirname, callback_data=dirname)])
    return l

  def classify(self, chat_id):
    fileinfo = self.filefeeder()
    if fileinfo:
      try: 
        guess = str(self.cl.classify(fileinfo['name']))
        fileinfo['guess'] = guess
        fileinfo['destPath'] = os.path.join(self.destPath, guess)
        output = fileinfo['name'] + '\n=>' + guess
        self.fileinfo = fileinfo
        self.edtYESNO = self.bot.sendMessage(chat_id, output, 
                         reply_markup=self.kbdYESNO)
      except:
        self.fileinfo = None
        output = fileinfo['name'] + '\n' + fileinfo['srcPath'] + '\n' + 'failed ...'
        self.bot.sendMessage(chat_id, output)
    else:
      self.bot.sendMessage(chat_id, 'No files ...')

  def on_chat_message(self, msg):
    content_type, chat_type, chat_id = telepot.glance(msg)
    if msg['text'] == '/classify':
      self.mode = 'guess'
      self.classify(chat_id)

  def on_callback_query(self, msg):
    query_id, from_id, data = telepot.glance(msg, flavor='callback_query')
    
    if self.mode == 'guess': 
      if data == 'YES':
        print(self.fileinfo)
        self.filemove(self.fileinfo)
        self.cl.train(self.fileinfo['name'], self.fileinfo['guess'])
        self.fileinfo = None
        self.classify(from_id)
      elif data == 'NO':
        self.mode = 'mainFolder'
        self.bot.sendMessage(from_id, 'Choose main folder ...', 
          reply_markup=self.kbdMainFolder)
    elif self.mode == 'mainFolder': 
      path = os.path.join(self.destPath, data)
      self.fileinfo['guess'] = data
      self.fileinfo['destPath'] = os.path.join(self.destPath, data)
      buttons = self.kbdSubFolder(path)
      markup = InlineKeyboardMarkup(inline_keyboard=buttons)
      self.bot.sendMessage(from_id, 'Choose sub folder ...', 
        reply_markup = markup)
      self.mode = 'subFolder'
    elif self.mode == 'subFolder': 
      self.fileinfo['guess'] = '/'.join([self.fileinfo['guess'], data])
      self.fileinfo['destPath'] = os.path.join(self.fileinfo['destPath'], data)
      self.filemove(self.fileinfo)
      self.cl.train(self.fileinfo['name'], self.fileinfo['guess'])
      self.mode = ''
      self.fileinfo = None
      self.classify(from_id)

      

# Delegator Bot
class TestBot(telepot.DelegatorBot):
  def __init__(self, token, cl, srcPath, destPath):
    
    super(TestBot, self).__init__(token, 
    [
      (per_application(), create_open(FileClassifier, cl, srcPath, destPath)),
    ])


def sampletrain(cl):
  cl.train('디어마이프렌즈', 'Drama/디어마이프렌즈')
  cl.train('무한도전', 'Entertainment/무한도전')
  cl.train('infinite', 'Entertainment/무한도전')
  cl.train('challenge', 'Entertainment/무한도전')
  cl.train('특집다큐', 'Documentary')
  cl.train('런닝맨', 'Entertainment/런닝맨')
  cl.train('라디오스타', 'Entertainment/라디오스타')
  cl.train('38사', 'Drama/38사기동대')
  cl.train('기동대', 'Drama/38사기동대')
  cl.train('task', 'Drama/38사기동대')
  cl.train('force', 'Drama/38사기동대')
  cl.train('아는', 'Entertainment/아는형님')
  cl.train('형님', 'Entertainment/아는형님')
  cl.train('아는형님', 'Entertainment/아는형님')
  cl.train('언니들의', 'Entertainment/언니들의슬램덩크')
  cl.train('기동대', 'Drama/38사기동대')
  cl.train('닥터스', 'Drama/닥터스')
  cl.train('개그', 'Entertainment/개그콘서트')
  cl.train('콘서트', 'Entertainment/개그콘서트')
  cl.train('웃음을', 'Entertainment/웃찾사')
  cl.train('뷰티풀', 'Drama/뷰티풀마인드')
  cl.train('마인드', 'Drama/뷰티풀마인드')
  cl.train('원티드', 'Drama/원티드')
  cl.train('보컬전쟁', 'Entertainment/보컬전쟁')
  cl.train('신의', 'Entertainment/보컬전쟁')
  cl.train('목소리', 'Entertainment/보컬전쟁')
  cl.train('빅리그', 'Entertainment/코미디빅리그')
  cl.train('코미디', 'Entertainment/코미디빅리그')
  pass
  
########################################################################### 
  
SRC_PATH = "/home/pi/Videos/torrent-download/completed"
DEST_PATH = "/home/pi/Videos/torrent-download"

if __name__ == '__main__':
  try:
    cl = docclass.fisherclassifier(docclass.getwords) 
    cl.setdb('torrent.db')
    sampletrain(cl)


    logger = log.setupCustomLogger('testBot') 
    f = open('token.txt', 'r') 
    TOKEN = f.read().strip()
    f.close() 

    bot = TestBot(TOKEN, cl, SRC_PATH, DEST_PATH)
    bot.message_loop(run_forever='Listening...')

  except KeyboardInterrupt:
    print 'Interrupted'
    try:
      sys.exit(0)
    except SystemExit:
      os._exit(0)
    

        
