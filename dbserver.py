#-*- coding: utf-8 -*-
from sqlite3 import dbapi2 as sqlite
from pprint import pprint

# sqlite db server
class dbserver:
  def __init__(self, dbfile):
    self.con = sqlite.connect(dbfile, check_same_thread=False)
    self.createTables()
  
  def createTables(self):
    self.con.execute(
      "create table if not exists users(chat_id primary key, username)"
    )

    self.con.execute(
      """create table if not exists torrents
      (
        id text
        , completed integer
        , stime datetime
        , etime datetime
        , chat_id integer
		, primary key(id, chat_id)
        , foreign key(chat_id) references users(chat_id)
      )
      """
    )
 
  # user check
  def isUser(self, chat_id):
    res = self.con.execute(
      "select username from users where chat_id = %d" % (chat_id)
    ).fetchone()
    return True if res else False

  # username
  def username(self, chat_id):
    res = self.con.execute(
      "select username from users where chat_id = %d" % chat_id
    ).fetchone()
    return res[0]

  # 
  def addTorrent(self, tinfo):
    try:
      with self.con: 
        self.con.execute(
          """
           insert into torrents values(?, 0, datetime('now', 'localtime'), NULL, ?)
          """ , (tinfo['id'], tinfo['chat_id'])
        )
    except sqlite.IntegrityError:
      print('db error: dup on val')
      pprint(tinfo) 

  # 
  def deleteTorrent(self, chat_id, id):
    try:
      with self.con:
        self.con.execute(
          "delete from torrents where chat_id = %d and id = '%s'" % (chat_id, id)
        )
    except sqlite.Error as err:
      print('db error: delete')
      pprint(err) 

  # 
  def torrentIds(self, chat_id):
    cur = self.con.execute("""
    select  id 
    from    torrents 
    where   chat_id = %d
    and     completed = 0
    """ % chat_id)
    results = cur.fetchall()
    return [r[0] for r in results]




