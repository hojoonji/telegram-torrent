#-*- coding: utf-8 -*-
import sys
from pprint import pprint
from random import randint
import telepot
import telepot.helper
from telepot.delegate import per_chat_id, create_open
from telepot.namedtuple import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardHide, ForceReply
from telepot.namedtuple import InlineKeyboardMarkup, InlineKeyboardButton 
from telepot.namedtuple import InlineQueryResultArticle, InlineQueryResultPhoto, InputTextMessageContent 
from services import searchFromTorrentKim
from torrentserver import deluge
from sqlite3 import dbapi2 as sqlite
from dbserver import dbserver

reload(sys)
sys.setdefaultencoding('utf-8')

message_with_home_keyboard = None
message_with_torrents_keyboard = None

class T2bot(telepot.helper.ChatHandler):
  def __init__(self, seed_tuple, timeout, search, db):
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

  def open(self, initial_msg, seed):
    if not self.db.isUser(self.chat_id):
      self.sender.sendMessage('user_id: %d is not a valid user' % (self.chat_id))
      return 
    self.sender.sendMessage('자네 왔는가.')
  
  def showTorrentsMenu(self, torrents):
#    pprint(torrents)
    l = [[InlineKeyboardButton(text=t['title'], callback_data=str(i))] 
          for i, t in enumerate(torrents) if t] 
    self.kbdTorrents = InlineKeyboardMarkup(inline_keyboard=l)
    self.edtTorrents = self.sender.sendMessage('선택하세요 ...', reply_markup=self.kbdTorrents)


  def showTorrentsProgress(self):
    ids = self.db.torrentIds(self.chat_id)
    if len(ids) == 0: 
      self.sender.sendMessage('진행중인 토렌트가 없습니다.')
    else:
      info = [self.server.torrentInfoStr(id) for id in ids]
      self.sender.sendMessage('\n\n'.join(info))

  def ongoingList(self):
    torrents = []
    ids = self.db.torrentIds(self.chat_id)
    torrents = [self.server.torrentInfo(id) for id in ids]
    return torrents
  
  def on_chat_message(self, msg): 
    content_type, chat_type, chat_id = telepot.glance(msg) 
    if not self.db.isUser(chat_id):
      self.sender.sendMessage('user_id: %d is not a valid user' % (chat_id))
      return 
    
    # always search user input
    if content_type == 'text': 
      if msg['text'] == '/progress':
        self.mode = 'progress'
        self.showTorrentsProgress() 
        return

      elif msg['text'] == '/delete':
        self.mode = 'delete'
        if self.edtTorrents:
          id = telepot.message_identifier(self.edtTorrents)
          bot.editMessageText(id, '...', reply_markup=None)

        self.sender.sendMessage('Select torrent to delete ...')
        self.torrents = self.ongoingList()
        if not len(self.torrents): self.sender.sendMessage('진행 중인 토렌트가 없습니다.')
        else:
          self.showTorrentsMenu(self.torrents) 

      else: 
        self.mode = 'search'
        if self.edtTorrents:
          id = telepot.message_identifier(self.edtTorrents)
          bot.editMessageText(id, '...', reply_markup=None)

        self.sender.sendMessage('검색중 ...') 
        self.torrents = self.search(unicode(msg['text'])) 

        if not len(self.torrents): self.sender.sendMessage('검색된 파일이 없습니다.')
        else: 
          self.showTorrentsMenu(self.torrents)

    else: self.sender.sendMessage('문자만 입력하실 수 있습니다.')

  def on_callback_query(self, msg): 
    query_id, from_id, data = telepot.glance(msg, flavor='callback_query')

    if not self.edtTorrents:
      self.bot.answerCallbackQuery(query_id, text='Overdue list, please search again')
      return 

    id = telepot.message_identifier(self.edtTorrents) 
    torrent = self.torrents[int(data)]

    if self.mode == 'search':
      bot.editMessageText(id, '추가,  %s' % self.torrents[int(data)]['title'], reply_markup=None)
      self.addTorrent(torrent['magnet'])

    elif self.mode == 'delete': 
      bot.editMessageText(id, '삭제, %s' % self.torrents[int(data)]['title'], reply_markup=None)
      self.deleteTorrent(torrent['id'])

  def addTorrent(self, magnet):
    torrentInfo = self.server.add(magnet) 
    torrentInfo['chat_id'] = self.chat_id
    self.db.addTorrent(torrentInfo)

  def deleteTorrent(self, id):
    self.server.delete(id)
    self.db.deleteTorrent(self.chat_id, id)
    
db = dbserver('torrent.db')
TOKEN = 'YOUR TOKEN'
bot = telepot.DelegatorBot(TOKEN, 
  [
    (per_chat_id(), create_open(T2bot, 90, searchFromTorrentKim, db)),
  ])

bot.message_loop(run_forever='Listening...')
        
