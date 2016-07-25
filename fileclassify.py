#-*- coding: utf-8 -*-
import sys
import os
import log
import logging
import fnmatch
import re
import docclass
import shutil
import json
from apscheduler.schedulers.background import BackgroundScheduler

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
  def __init__(self, seed_tuple, classifier, srcPath, destPath, baseProb):
    super(FileClassifier, self).__init__(seed_tuple, capture=[{'_': lambda msg: True}])
    self.logger = logging.getLogger('fileclassifier')
    self.logger.debug('FileClassifier logger init')
    self.cl = cl
    self.srcPath = srcPath
    self.destPath = destPath
    self.mode = ''
    self.spchars = re.compile('[\s\'!\(\)\,]')
    self.edtMsg = None
    self.files = None
    self.folders = None

    self.baseProb = float(baseProb)
    self.autoFiles = None
    self.autoFileInfo = None
    self.autoSched = BackgroundScheduler()
    self.autoSched.start()
    self.autoSched.add_job(self.autoClassify, 'interval', hours=1)

    self.autoClassify()

    self.kbdYESNO = InlineKeyboardMarkup(
        inline_keyboard=[
          [
            InlineKeyboardButton(text='YES', callback_data='YES'),
            InlineKeyboardButton(text='NO', callback_data='NO'),
            InlineKeyboardButton(text='PASS', callback_data='PASS'),
          ],
        ])
    self.kbdMainFolder = InlineKeyboardMarkup(inline_keyboard=self.folderButtons(self.destPath))

  # remove special chars
  def correctPath(self):
    for root, dirnames, filenames in os.walk(self.srcPath):
      if root != self.srcPath:
        if len(filenames) == 0:
          try:
            os.rmdir(root)
          except Exception, e:
            self.logger.debug('rmdir error')
            self.logger.debug(e)

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
        if filename.endswith(('.avi', '.mp4', '.mkv', '.smi', '.srt', '.mpg', '.ts')):
          fileInfo = {'name':filename, 'srcPath': os.path.join(root, filename)}
          l.append(fileInfo)
    return l

  def folderList(self):
    l = []
    for dirname in os.listdir(self.srcPath):
      folderInfo = {}
      folderInfo['srcPath'] = os.path.join(self.srcPath, dirname)
      folderInfo['name'] = dirname
      l.append(folderInfo)
    return l

  def fileFeeder(self, files):
    if len(files) > 0:
        idx = randint(0, len(files)-1)
        fileInfo = files[idx]
        del files[idx]
        return fileInfo
    else: return None

  def folderFeeder(self, folders):
    if len(folders) > 0:
        idx = randint(0, len(folders)-1)
        folderInfo = folders[idx]
        del folders[idx]
        return folderInfo
    else: return None

  def fileMove(self, fileInfo):
    # self.logger.debug(fileInfo)
    try:
      shutil.move(fileInfo['srcPath'], fileInfo['destPath'])
      # self.logger.debug('file move ok')
    except Exception, e:
      self.logger.debug('file move failed')
      self.logger.error(e)


  def folderButtons(self, path):
    l = []
    for dirname in os.listdir(path):
      l.append([InlineKeyboardButton(text=dirname, callback_data=dirname)])
    return l

  def autoClassify(self):
    oks = []
    failed = []
    self.autoFiles = self.fileList()
    for fileInfo in self.autoFiles:
      try:
        guess, prob = self.cl.classify(fileInfo['name'])
        self.logger.debug('file: %s, base: %.2f, guess: %s prob: %.2f' % (filInfo['name'], self.baseProb, guess, prob))
        if float(prob) >= self.baseProb:
          fileInfo['guess'] = str(guess)
          fileInfo['destPath'] = os.path.join(self.destPath, guess, fileInfo['name'])
          self.fileMove(fileInfo)
          self.cl.train(fileInfo['name'], fileInfo['guess'])
          msg = 'auto move %s\n=> %s(%.2f)' % (fileInfo['name'], fileInfo['guess'], prob)
          
          self.bot.sendMessage(28204859, msg)
        else:
          self.logger.debug('prob is low')
          pass
      except:
        pass

  def folderClassify(self, chat_id):
    folderInfo = self.folderFeeder(self.folders)
    if folderInfo:
      msg = 'folder move: %s to ...' % folderInfo['name']
      self.folderInfo = folderInfo
      self.bot.sendMessage(chat_id, msg, reply_markup=self.kbdMainFolder)
    else:
      self.bot.sendMessage(chat_id, 'No more folders ...')
      
  def classify(self, chat_id):
    # self.logger.debug('in classify')
    fileInfo = self.fileFeeder(self.files)
    # self.logger.debug('get new file')
    if fileInfo:
      try: 
        # self.logger.debug('before guess')
        guess, prob = self.cl.classify(fileInfo['name'])
        # self.logger.debug('after guess')
        self.mode = 'guess'
        fileInfo['guess'] = str(guess)
        fileInfo['destPath'] = os.path.join(self.destPath, guess, fileInfo['name'])
        output = '%s\n => %s(%.2f)' % (fileInfo['name'], guess, prob)
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
      # get new file list only user request
      self.files = self.fileList() 
      self.classify(chat_id)

    elif msg['text'] == '/movefolder': 
      self.folders = None
      self.editLastMessage('...')

      self.folders = self.folderList()
      self.mode = 'move_folder'
      self.folderClassify(chat_id)

    elif self.mode == 'create_folder':
      newfolder = msg['text']

      newpath = os.path.join(self.fileInfo['destPath'], newfolder)
      if not os.path.exists(newpath):
        os.makedirs(newpath)
      self.fileInfo['guess'] = '/'.join([self.fileInfo['guess'], newfolder])
      self.fileInfo['destPath'] = os.path.join(self.fileInfo['destPath'], newfolder, self.fileInfo['name'])
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
      elif data == 'PASS':
        self.editLastMessage('file passed ...')
        self.classify(from_id)
    
    elif self.mode == 'move_folder': 
      self.folderInfo['destPath'] = os.path.join(self.destPath, data)
      self.logger.debug(self.folderInfo)
      self.fileMove(self.folderInfo)
      self.editLastMessage('folder move ok')
      self.folderInfo = None
      self.folderClassify(from_id)

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
      self.fileInfo['destPath'] = os.path.join(self.fileInfo['destPath'], data, self.fileInfo['name'])
      self.fileMove(self.fileInfo)
      self.cl.train(self.fileInfo['name'], self.fileInfo['guess'])
      self.editLastMessage('file move ok')
      self.fileInfo = None 
      self.classify(from_id)

# Delegator Bot
class ChatBot(telepot.DelegatorBot):
  def __init__(self, token, cl, srcPath, destPath, baseProb):
    
    super(ChatBot, self).__init__(token, 
    [
      (per_application(), create_open(FileClassifier, cl, srcPath, destPath, baseProb)),
    ])


def sampleTrain(cl):
  # cl.train('디어마이프렌즈', 'K-Dram a/디어마이프렌즈')
  # cl.train('무한도전', 'Entertainment/무한도전')
  # cl.train('infinite', 'Entertainment/무한도전')
  # cl.train('challenge', 'Entertainment/무한도전')
  # cl.train('특집다큐', 'Documentary')
  # cl.train('런닝맨', 'Entertainment/런닝맨')
  # cl.train('라디오스타', 'Entertainment/라디오스타')
  # cl.train('38사', 'K-Drama/38사기동대')
  # cl.train('기동대', 'K-Drama/38사기동대')
  # cl.train('task', 'K-Drama/38사기동대')
  # cl.train('force', 'K-Drama/38사기동대')
  # cl.train('아는', 'Entertainment/아는형님')
  # cl.train('형님', 'Entertainment/아는형님')
  # cl.train('아는형님', 'Entertainment/아는형님')
  # cl.train('언니들의', 'Entertainment/언니들의슬램덩크')
  # cl.train('기동대', 'K-Drama/38사기동대')
  # cl.train('닥터스', 'K-Drama/닥터스')
  # cl.train('개그', 'Entertainment/개그콘서트')
  # cl.train('콘서트', 'Entertainment/개그콘서트')
  # cl.train('웃음을', 'Entertainment/웃찾사')
  # cl.train('뷰티풀', 'K-Drama/뷰티풀마인드')
  # cl.train('마인드', 'K-Drama/뷰티풀마인드')
  # cl.train('원티드', 'K-Drama/원티드')
  # cl.train('보컬전쟁', 'Entertainment/보컬전쟁')
  # cl.train('신의', 'Entertainment/보컬전쟁')
  # cl.train('목소리', 'Entertainment/보컬전쟁')
  # cl.train('빅리그', 'Entertainment/코미디빅리그')
  # cl.train('코미디', 'Entertainment/코미디빅리그')
  pass
  
########################################################################### 

if __name__ == '__main__':
  try:
    cl = docclass.fisherclassifier(docclass.getwords) 
    cl.setdb('torrent.db')
    sampleTrain(cl)

    logger = log.setupCustomLogger('fileclassifier', 'fileclassifier.log') 

   
    with open('setting.json', 'r') as f:
      setting = json.load(f)

    TOKEN = str(setting['token']['classify'])
    SRC_PATH = str(setting['src_path'])
    DEST_PATH = str(setting['dest_path'])
    BASE_PROB = float(setting['base_prob'])

    bot = ChatBot(TOKEN, cl, SRC_PATH, DEST_PATH, BASE_PROB)
    bot.message_loop(run_forever='Listening...')

  except KeyboardInterrupt:
    print 'Interrupted'
    try:
      sys.exit(0)
    except SystemExit:
      os._exit(0)
    

        
