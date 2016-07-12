#-*- coding: utf-8 -*-
import feedparser

def searchFromTorrentKim(keyword, max=10):
  url = 'https://torrentkim1.net/bbs/rss.php?k=' 
  result = []
  d = feedparser.parse(url + keyword) 
  for entry in d.entries[0:max]:
    result.append({'title': entry.title, 'magnet': entry.link})
  return result
      
      
      
    
    
    