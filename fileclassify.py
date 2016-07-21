#-*- coding: utf-8 -*-
import sys
import os
import log
import logging
import fnmatch
import re
import docclass
import shutil

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
    self.logger = logging.getLogger('fileclassifier')
    self.logger.debug('FileClassifier logger init')
    self.cl = cl
    self.srcPath = srcPath
    self.destPath = destPath
    self.mode = ''
    self.spchars = re.compile('[\s\'!\(\)\,]')
    self.edtMsg = None
    self.kbdYESNO = InlineKeyboardMarkup(
        inline_keyboard=[
          [
            InlineKeyboardButton(text='YES', callback_data='YES'),
            InlineKeyboardButton(text='NO', callback_data='NO'),
          ],
        ])
    self.kbdMainFolder = InlineKeyboardMarkup(inline_keyboard=self.folders(self.destPath))

  # remove special chars
  def correctPath(self):
    for root, dirnames, filenames in os.walk(self.srcPath):
      if root != self.srcPath:
        if len(filenames) == 0:
          try:
            os.rmdir(root)
          except:
            self.logger.debug('rmdir error')

    for root, dirnames, filenames in os.walk(self.srcPath):
      currentPath = root 
      newPath = self.spchars.sub('_', currentPath)
      os.rename(currentPath, newPath)

    for root, dirnames, filenames in os.walk(self.srcPath):
      for filename in filenames:
        currentFilename = filename
        newFileName = self.spchars.sub('_', currentFilename)
        os.rename(os.path.join(root, currentFilename), os.path.join(root, newFileName))

  def fileList(self):
    l = []
    for root, dirnames, filenames in os.walk(self.srcPath):
      for filename in filenames:
        if filename.endswith(('.avi', '.mp4', '.mkv', '.smi', '.srt', '.mpg')):
          fileInfo = {'name':filename, 'srcPath': os.path.join(root, filename)}
          l.append(fileInfo)
    return l

  def fileFeeder(self):
    if len(self.files) > 0:
        idx = randint(0, len(self.files)-1)
        fileInfo = self.files[idx]
        del self.files[idx]
        return fileInfo
    else: return None

  def fileMove(self, fileInfo):
    try:
      shutil.move(fileInfo['srcPath'], fileInfo['destPath'])
    except IOError, e:
      self.logger.error(e)


  def folders(self, path):
    l = []
    for dirname in os.listdir(path):
      l.append([InlineKeyboardButton(text=dirname, callback_data=dirname)])
    l.append([InlineKeyboardButton(text='New folder ...', callback_data='new_folder')])
    return l

  def classify(self, chat_id):
    fileInfo = self.fileFeeder()
    if fileInfo:
      try: 
        guess = str(self.cl.classify(fileInfo['name']))
        self.mode = 'guess'
        fileInfo['guess'] = guess
        fileInfo['destPath'] = os.path.join(self.destPath, guess)
        output = fileInfo['name'] + '\n=> ' + guess
        self.fileInfo = fileInfo
        self.edtMsg = self.bot.sendMessage(chat_id, output, 
                         reply_markup=self.kbdYESNO)
      except: 
        self.mode = 'mainFolder'
        self.fileInfo = fileInfo
        output = fileInfo['name'] + '\n' + fileInfo['srcPath'] + '\n ' + 'failed ...'
        self.bot.sendMessage(chat_id, output)
        self.edtMsg = self.bot.sendMessage(chat_id, 'Choose main folder ...', 
          reply_markup=self.kbdMainFolder)
    else:
      self.bot.sendMessage(chat_id, 'No files ...')

  def editLastMessage(self, msg):
    if self.edtMsg:
      id = telepot.message_identifier(self.edtMsg)
      self.bot.editMessageText(id, msg, reply_markup=None)
      self.edtMsg = None

  def on_chat_message(self, msg):
    content_type, chat_type, chat_id = telepot.glance(msg)

    if msg['text'] == '/classify': 
      self.fileInfo = None
      self.files = None
      self.editLastMessage('...')

      self.correctPath()
      self.files = self.fileList() 
      self.classify(chat_id)

    elif self.mode == 'create_folder':
      newfolder = msg['text']

      newpath = os.path.join(self.fileInfo['destPath'], newfolder)
      if not os.path.exists(newpath):
        os.makedirs(newpath)
      self.fileInfo['guess'] = '/'.join([self.fileInfo['guess'], newfolder])
      self.fileInfo['destPath'] = os.path.join(self.fileInfo['destPath'], newfolder)
      self.fileMove(self.fileInfo)
      self.cl.train(self.fileInfo['name'], self.fileInfo['guess'])
      self.mode = 'guess'
      self.fileInfo = None
      self.classify(chat_id)

  def on_callback_query(self, msg):
    query_id, from_id, data = telepot.glance(msg, flavor='callback_query')
    
    if self.mode == 'guess': 
      if data == 'YES':
        self.fileMove(self.fileInfo)
        self.cl.train(self.fileInfo['name'], self.fileInfo['guess'])
        self.fileInfo = None
        
        msg = 'file move ... ok'
        self.editLastMessage(msg)

        self.classify(from_id)
      elif data == 'NO':
        self.mode = 'mainFolder'
        self.editLastMessage('...') 
        msg = 'Choose main folder for ' + self.fileInfo['name'] + ' ...'
        self.edtMsg = self.bot.sendMessage(from_id, msg, 
          reply_markup=self.kbdMainFolder)
    elif self.mode == 'mainFolder': 
      path = os.path.join(self.destPath, data)
      self.fileInfo['guess'] = data
      self.fileInfo['destPath'] = os.path.join(self.destPath, data)
      buttons = self.folders(path)
      markup = InlineKeyboardMarkup(inline_keyboard=buttons)
      self.editLastMessage('...')
      msg = 'Choose sub folder for ' + self.fileInfo['name'] + ' ...'
      self.edtMsg = self.bot.sendMessage(from_id, msg, reply_markup = markup)
      self.mode = 'subFolder'
    elif self.mode == 'subFolder': 
      if data == 'new_folder':
        self.mode = 'create_folder'
        self.editLastMessage('...')
        self.edtMsg = self.bot.sendMessage(from_id, 'Input folder name')
        return

      self.fileInfo['guess'] = '/'.join([self.fileInfo['guess'], data])
      self.fileInfo['destPath'] = os.path.join(self.fileInfo['destPath'], data)
      self.fileMove(self.fileInfo)
      self.cl.train(self.fileInfo['name'], self.fileInfo['guess'])
      self.editLastMessage('file move ok')
      self.fileInfo = None 
      self.classify(from_id)

# Delegator Bot
class ChatBot(telepot.DelegatorBot):
  def __init__(self, token, cl, srcPath, destPath):
    
    super(ChatBot, self).__init__(token, 
    [
      (per_application(), create_open(FileClassifier, cl, srcPath, destPath)),
    ])


def sampleTrain(cl):
  # cl.train('디어마이프렌즈', 'Drama/디어마이프렌즈')
  # cl.train('무한도전', 'Entertainment/무한도전')
  # cl.train('infinite', 'Entertainment/무한도전')
  # cl.train('challenge', 'Entertainment/무한도전')
  # cl.train('특집다큐', 'Documentary')
  # cl.train('런닝맨', 'Entertainment/런닝맨')
  # cl.train('라디오스타', 'Entertainment/라디오스타')
  # cl.train('38사', 'Drama/38사기동대')
  # cl.train('기동대', 'Drama/38사기동대')
  # cl.train('task', 'Drama/38사기동대')
  # cl.train('force', 'Drama/38사기동대')
  # cl.train('아는', 'Entertainment/아는형님')
  # cl.train('형님', 'Entertainment/아는형님')
  # cl.train('아는형님', 'Entertainment/아는형님')
  # cl.train('언니들의', 'Entertainment/언니들의슬램덩크')
  # cl.train('기동대', 'Drama/38사기동대')
  # cl.train('닥터스', 'Drama/닥터스')
  # cl.train('개그', 'Entertainment/개그콘서트')
  # cl.train('콘서트', 'Entertainment/개그콘서트')
  # cl.train('웃음을', 'Entertainment/웃찾사')
  # cl.train('뷰티풀', 'Drama/뷰티풀마인드')
  # cl.train('마인드', 'Drama/뷰티풀마인드')
  # cl.train('원티드', 'Drama/원티드')
  # cl.train('보컬전쟁', 'Entertainment/보컬전쟁')
  # cl.train('신의', 'Entertainment/보컬전쟁')
  # cl.train('목소리', 'Entertainment/보컬전쟁')
  # cl.train('빅리그', 'Entertainment/코미디빅리그')
  # cl.train('코미디', 'Entertainment/코미디빅리그')
  pass
  
########################################################################### 
  
SRC_PATH = "/home/pi/Videos/torrent-download/completed"
DEST_PATH = "/home/pi/Videos/torrent-download"

if __name__ == '__main__':
  try:
    cl = docclass.fisherclassifier(docclass.getwords) 
    cl.setdb('torrent.db')
    sampleTrain(cl)

    logger = log.setupCustomLogger('fileclassifier', 'fileclassifier.log') 
    f = open('token_classify.txt', 'r') 
    TOKEN = f.read().strip()
    f.close() 

    bot = ChatBot(TOKEN, cl, SRC_PATH, DEST_PATH)
    bot.message_loop(run_forever='Listening...')

  except KeyboardInterrupt:
    print 'Interrupted'
    try:
      sys.exit(0)
    except SystemExit:
      os._exit(0)
    

        
