#-*- coding: utf-8 -*-
import sys
import os
import log
import logging

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
from services import searchFromTorrentKim
from torrentserver import deluge
from sqlite3 import dbapi2 as sqlite
from dbserver import dbserver
from apscheduler.schedulers.background import BackgroundScheduler

reload(sys)
sys.setdefaultencoding('utf-8')

class T2bot(telepot.helper.ChatHandler):
  def __init__(self, seed_tuple, timeout, search, db, server):
    super(T2bot, self).__init__(seed_tuple, timeout)
    self.search = search
    self.server = deluge()
    self.db = db
    self.torrents = []
    self.mode = ''

    # inline keyboards
    self.edtTorrents = None

    self.kbdTorrents = InlineKeyboardMarkup(
      inline_keyboard=[]
    )
   
  def on_close(self, e):
    pass

  # Check user is valid and welcome message
  def open(self, initial_msg, seed):
    if not self.db.isUser(self.chat_id):
      self.sender.sendMessage('user_id: %d is not a valid user' % (self.chat_id))
      return 
    self.sender.sendMessage('Welcome back')
 
  # Send inline buttons contain torrent title
  def showTorrentsMenu(self, torrents):
    l = [[InlineKeyboardButton(text=t['title'], callback_data=str(i))] 
          for i, t in enumerate(torrents) if t] 
    self.kbdTorrents = InlineKeyboardMarkup(inline_keyboard=l)
    self.edtTorrents = self.sender.sendMessage('Choose ...', 
                        reply_markup=self.kbdTorrents)


  # Send torrent info string 
  def showTorrentsProgress(self):
    ids = self.db.torrentIds(self.chat_id)
    if len(ids) == 0: 
      self.sender.sendMessage('There is no torrents downloading ...')
    else:
      info = [self.server.torrentInfoStr(id) for id in ids]
      # only torrent exists in server
      info = [t for t in info if t]
      if len(info) == 0: 
        self.sender.sendMessage('There is no torrents downloading ...')
      else: self.sender.sendMessage('\n\n'.join(info))

  # current torrent files downloaded
  def ongoingList(self):
    torrents = []
    ids = self.db.torrentIds(self.chat_id)
    torrents = [self.server.torrentInfo(id) for id in ids]
    torrents = [t for t in torrents if t is not None]
    return torrents
 
  def on_chat_message(self, msg): 
    content_type, chat_type, chat_id = telepot.glance(msg) 
    # check valid user
    if not self.db.isUser(chat_id):
      self.sender.sendMessage('user_id: %d is not a valid user' % (chat_id))
      return 
    
    # always consider text message
    if content_type == 'text': 
      # command - progress
      if msg['text'] == '/progress':
        self.mode = 'progress'
        self.showTorrentsProgress() 
        return

      # command - delete
      elif msg['text'] == '/delete':
        self.mode = 'delete'
        # clear message identifier saved
        if self.edtTorrents:
          id = telepot.message_identifier(self.edtTorrents)
          self.bot.editMessageText(id, '...', reply_markup=None)

        self.sender.sendMessage('Select torrent to delete ...')
        self.torrents = self.ongoingList()
        if len(self.torrents) == 0: 
          self.sender.sendMessage('There is no downloading files.')
          self.edtTorrents = None
        else:
          self.showTorrentsMenu(self.torrents) 

      # command - reboot
      elif msg['text'] == '/reboot':
  	  	self.sender.sendMessage('Torrent server rebooting ...')
  	  	self.sender.sendMessage('*** Do not enter message ***')
    		self.server.reboot()
  	  	self.sender.sendMessage('System ok ...')

      # search torrents file using self.search function
      else: 
        self.mode = 'search'
        if self.edtTorrents:
          id = telepot.message_identifier(self.edtTorrents)
          self.bot.editMessageText(id, '...', reply_markup=None)

        self.sender.sendMessage('searching ...') 
        self.torrents = self.search(unicode(msg['text'])) 

        if not len(self.torrents): 
          self.sender.sendMessage('There is no files searched.')
          self.edtTorrents = None
        else: 
          self.showTorrentsMenu(self.torrents)

    else: self.sender.sendMessage('You can only send text message.')

  # When user click a inline button
  def on_callback_query(self, msg): 
    query_id, from_id, data = telepot.glance(msg, flavor='callback_query')

    if not self.edtTorrents:
      self.bot.answerCallbackQuery(query_id, 
        text='Overdue list, please search again')
      return 

    id = telepot.message_identifier(self.edtTorrents) 
    torrent = self.torrents[int(data)]

    if self.mode == 'search':
      self.bot.editMessageText(id, 'Adding,  %s' % 
        self.torrents[int(data)]['title'], reply_markup=None)
      self.addTorrent(torrent['magnet'])

    elif self.mode == 'delete': 
      self.bot.editMessageText(id, 'Deleting, %s' % 
       self.torrents[int(data)]['title'], reply_markup=None)
      self.deleteTorrent(torrent['id'])

  # add torrent magnet to torrent server and db server 
  def addTorrent(self, magnet):
    torrentInfo = self.server.add(magnet) 
    if not torrentInfo:
      self.sender.sendMessage('Already in list')
      return

    torrentInfo['chat_id'] = self.chat_id
    self.db.addTorrent(torrentInfo)

  # remove torrent file from torrent server and db server
  def deleteTorrent(self, id):
    self.server.delete(id)
    self.db.deleteTorrent(self.chat_id, id)

# torrent monitoring
class jobmonitor(telepot.helper.Monitor):
  def __init__(self, seed_tuple, server, db):
    super(jobmonitor, self).__init__(seed_tuple, capture=[{'_': lambda msg: True}])
    self.server = server 
    self.db = db
    self.logger = logging.getLogger('bot')
    self.sched = BackgroundScheduler()
    self.sched.start()
    self.sched.add_job(self.torrentMonitor, 'interval', minutes=3)

    self.logger.debug('jobmonitor logger init ...')

  def on_chat_message(self, msg): 
    pass

  def on_callback_query(self, msg): 
    pass

  def on_close(self, e):
    self.logger.debug('jobmonitor will shutdown')
    self.shutdown()
   
  def shutdown(self):
    self.sched.shutdown()

  def torrentMonitor(self):
    self.logger.debug('========== DB ==========')
    fromDB = self.db.uncompleted() 
    self.logger.debug(fromDB)

    self.logger.debug('========== Server ==========')
    fromServer = self.server.completed() 
    self.logger.debug(fromServer)

    # extract complete torrents
    self.logger.debug('========== updateList ==========')
    updateList = []
    for dbt in fromDB:
      for st in fromServer:
        if dbt['id'] == st['id']:
          updateList.append({'id':dbt['id'], 'chat_id':dbt['chat_id'], 
            'title': st['title']}) 

    self.logger.debug(updateList) 

    for t in updateList:
      self.bot.sendMessage(t['chat_id'], 'downloaded\n' + t['title'])
      self.db.completeTorrent(t['chat_id'], t['id'])

# Delegator Bot
class chatbox(telepot.DelegatorBot):
  def __init__(self, token, search, db, server):
    self.search = search
    self.db = db
    self.server = server
    
    super(chatbox, self).__init__(token, 
    [
      (per_chat_id(), create_open(T2bot, 90, self.search, self.db, server)),
      (per_application(), create_open(jobmonitor, self.server, self.db)),
    ])

  def cron(self):
    pass
	
########################################################################### 

if __name__ == '__main__':
  try:
    logger = log.setupCustomLogger('bot')

    server = deluge()
    db = dbserver('torrent.db')
    f = open('token.txt', 'r') 

    TOKEN = f.read().strip()
    f.close() 

    bot = chatbox(TOKEN, searchFromTorrentKim, db, server)
    bot.message_loop(run_forever='Listening...')

  except KeyboardInterrupt:
    print 'Interrupted'
    try:
      sys.exit(0)
    except SystemExit:
      os._exit(0)
    

        
