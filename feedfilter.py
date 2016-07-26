# -*- coding: utf-8 -*-
import feedparser
import re 

def read(feed, classifier):
  f = feedparser.parse(feed)
  for entry in f['entries']:
    print 
    print '----'
    print 'Title:     ' + entry['title'].encode('utf-8')
    print 'Publisher: ' + entry['publisher'].encode('utf-8')
    print 
    print entry['summary'].encode('utf-8')
    
    fulltext = '%s\n%s\n%s' % (entry['title'], entry['publisher'], entry['summary'])
    
    print 'Guess: ' + str(classifier.classify(entry))
    
    cl = raw_input('Enter category: ')
    classifier.train(entry, cl)
                
def entryfeatures(entry):
  splitter = re.compile('\\W*')
  f = {}

  # 제목에는 특정 태그를 달고 단어별로 분리한다. 
  titlewords = [s.lower() for s in splitter.split(entry['title']) 
                 if len(s) > 2 and len(s) < 20]
  for w in titlewords: f['Title:'+w] = 1
  
  # 요약에서 단어를 추출함 
  summarywords = [s.lower() for s in splitter.split(entry['summary']) 
    if len(s) > 2 and len(s) < 20]
  
  # 요약의 단어를 feature 에 추가한다.    
  # 대문자로만 이루어진 단어개수를 센다. 
  # 두 단어로 이루어진 feature 를 추가한다.
  uc = 0
  for i in range(len(summarywords)):
    w = summarywords[i]
    f[w] = 1
    if w.isupper(): uc += 1
    
    if i < len(summarywords)-1:
      twowords = ' '.join(summarywords[i:i+1])
      f[twowords] = 1
      
  f['Publisher:' + entry['publisher']] = 1
 
  # 대문자 비율이 30% 를 넘으면 대문자 특성을 추가한다.
  if float(uc)/len(summarywords) > 0.3: f['UPPERCASE'] = 1
  
  return f
                        
        
        
        
        