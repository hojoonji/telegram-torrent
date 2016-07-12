#-*- coding: utf-8 -*- 
import os
from pprint import pprint
from time import sleep

# 토렌트 서버로 deluge 를 사용한다.
class deluge:
  def __init__(self):
    pass 
  
  # 마그넷을 추가하고 고유id를 반환한다.
  def add(self, magnet): 
    command = "deluge-console add " + magnet 
    beforeTorrents = self.ongoing()
    os.system(command)
    sleep(1)
    afterTorrents = self.ongoing()
    newone = [x for x in afterTorrents if x not in beforeTorrents]
    if len(newone) >= 1:
      torrentInfo = newone[0]
      return torrentInfo
        
  # 선택된 토렌트를 삭제한다.
  def delete(self, id):
    command = "deluge-console rm " + id
    os.system(command)
  
  # deluge 에 올라와있는 토렌트 목록  
  def ongoing(self):
    command = "deluge-console info"
    info = os.popen(command).read()
    return self.parse(info)

  # 토렌트 정보를 문자열로 반환한다.
  def torrentInfoStr(self, id):
    command = "deluge-console info " + id
    info = os.popen(command).read()
    return info

  # 토렌트 정보를 dict 형태로 반환
  def torrentInfo(self, id):
    command = "deluge-console info " + id
    info = os.popen(command).read() 
    return self.parse(info)[0] if len(info) != 0 else None
 
  # deluge-console info 의 output 을 parsing 한다. 
  def parse(self, info, torrentSep='\n \n', lineSep = '\n'):
    if info == '': return []

    parsed = []
    # 토렌트 단위로 자른다.
    torrents = info.split(torrentSep)
    for torrent in torrents:
      torrentInfo = {}

      lines = torrent.split(lineSep) 

      if lines[0] == ' ': del lines[0]
      if len(lines) == 0: return None

      for line in lines:
        tokens = line.split(': ')
        if tokens[0] == 'Name':
          torrentInfo['title'] = tokens[1]
        elif tokens[0] == 'ID':
          torrentInfo['id'] = tokens[1]
        elif tokens[0] == 'State':
          torrentInfo['status'] = (tokens[1].split(' '))[0].lower()
        elif tokens[0] == 'Seeds':
          torrentInfo['seeds'] = line
        elif tokens[0] == 'Size':
          torrentInfo['size'] = line
        elif tokens[0] == 'Seed time':
          torrentInfo['seed time'] = line
        elif tokens[0] == 'Progress': 
          torrentInfo['progress'] = (tokens[1].split(' '))[0].lower()

      parsed.append(torrentInfo)
    return parsed if len(parsed) > 0 else None


    
      
      
      
      
      
    
    
