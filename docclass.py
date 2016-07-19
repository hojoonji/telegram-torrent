# -*- coding: utf-8 -*-
import re 
import math 
from sqlite3 import dbapi2 as sqlite

def getwords(doc): 
  EXCL = ['hdtv', 'h264', '720p', '1080p', 'rumors', 'avi', 'mp4', 'mkv',
    'x264', '1080i', 'sodihd', 'rtp', 'film', 'cinebus', '450p', 'aac',
    'unknown', 'with',]  
  splitter = re.compile('[\_:.,\- \[\]]+')
  words = [s.lower().strip() for s in splitter.split(doc) if s.lower() not in EXCL]
  return dict([(w, 1) for w in words])
  
class classifier:
  def __init__(self, getFeatures, filename=None):
    self.fc = {}
    self.cc = {}
    self.getFeatures = getFeatures
    
  def setdb(self, dbfile):
    self.con = sqlite.connect(dbfile, check_same_thread=False)
    self.con.execute('create table if not exists fc(feature, category, count)')
    self.con.execute('create table if not exists cc(category, count)')
  
  # feature 에 대한 결과분류값을 증가시킨다.
  # 예를 들어 'spam' 에 'bad' 라는 분류값을 증가시킨다.
  def incf(self, f, cat):
    count = self.fcount(f, cat)
    if count == 0:
      self.con.execute("insert into fc values('%s', '%s', 1)" % (f, cat))
    else:
      self.con.execute(
        "update fc set count = %d where feature='%s' and category = '%s'" % 
        (count+1, f, cat))
    
  # 결과분류값을 증가시킨다.  
  # 예를 들어 'good' 이라는 분류값을 증가시킨다.
  def incc(self, cat):
    count = self.catcount(cat)
    if count == 0:
      self.con.execute("insert into cc values('%s', 1)" % (cat))
    else:
      self.con.execute(
        "update cc set count = %d where category = '%s'" % (count+1, cat))
   
  # 특정 feature 의 category 개수를 반환한다. 
  # 예를 들어 'spam' 이라는 feature 에서 'good' 이라고 분류된 개수
  def fcount(self, f, cat):
    res = self.con.execute(
      "select count from fc where feature='%s' and category='%s'" % (f, cat)).fetchone()
    if res == None: return 0
    else: return float(res[0])
    
  # 특정 category 에 속한 개수를 반환한다.  
  # 예를 들어 'good' 이라고 결정된 문서수
  def catcount(self, cat):
    res = self.con.execute(
      "select count from cc where category = '%s'" % (cat)).fetchone()
    if res == None: return 0
    else: return float(res[0])
  
  # 전체 분류개수를 반환한다. 예를 들어 전체 문서수 
  def totalcount(self):
    res = self.con.execute(
      "select sum(count) from cc").fetchone()
    if res == None: return 0
    else: return res[0]
   
  # 분류를 반환한다. 
  def categories(self):
    cur = self.con.execute("select category from cc")
    return [d[0] for d in cur]
    
  def train(self, item, cat):
    features = self.getFeatures(item)
    for f in features: self.incf(f, cat)
    self.incc(cat)
    self.con.commit()
  
  # 특정 feature 가 어떤 분류에 있을 확률  
  def fprob(self, f, cat):
    if self.catcount(cat) == 0: return 0
    return self.fcount(f, cat) / self.catcount(cat)
    
  # 가중확률 
  # 출현빈도가 낮은 단어에 대해 적절한 보정처리를 한다.
  def weightedprob(self, f, cat, prf, weight=1.0, ap=0.5):
    basicprob = prf(f, cat)
    totals = sum([self.fcount(f, c) for c in self.categories()])
    bp = ((weight*ap)+(totals*basicprob))/(weight+totals)
    return bp
    
 
class naivebayes(classifier):
  def __init__(self, getFeatures):
    classifier.__init__(self, getFeatures)
    self.thresholds= {}
  
  def docprob(self, item, cat):
    features = self.getFeatures(item)
    
    p = 1
    for f in features: p *= self.weightedprob(f, cat, self.fprob)
    return p
  
  # bayes's theorm
  # P(Cat|Doc) = P(Doc|Cat) * (P(Cat)/P(Doc))  
  # 여기서 P(Doc) 은 1로 생각한다.
  def prob(self, item, cat):
    catprob = self.catcount(cat)/self.totalcount()
    docprob = self.docprob(item, cat)
    return docprob * catprob
  
  # 분류에 대한 임계치 설정  
  def setthreshold(self, cat, t):
    self.thresholds[cat] = t
  
  # 분류에 대한 임계치 반환  
  def getthreshold(self, cat):
    if cat not in self.thresholds: return 1.0
    return self.thresholds[cat]
  
  # item 의 분류를 정한다.
  # 가중치가 설정된 분류의 경우, 가중치를 설정해서 선택된 분류를 사용할 
  # 것인지 결정한다.
  # threshold 를 사용한다.
  def classify(self, item, default=None):
    probs = {}
    max = 0.0
    # 가장 높은 확률의 분류를 찾는다.
    for cat in self.categories():
      probs[cat] = self.prob(item, cat)
      if probs[cat] > max:
        max = probs[cat]
        best = cat
        
    for cat in probs:
      if cat == best: continue
      # 타분류 * 가중치 > 가장높은확률 을 넘지 못하면, 기본값을 반환한다.
      if probs[cat] * self.getthreshold(best) > probs[best]: return default
    return best
    

class fisherclassifier(classifier):
  def __init__(self, getFeatures):
    classifier.__init__(self, getFeatures)
    self.minimums = {}
    
  def setminimum(self, cat, min):
    self.minimums[cat] = min
    
  def getminimum(self, cat):
    if cat in self.minimums: return self.minimums[cat]
    return 0
  
  # P(F|CAT)
  # feature 가 특정 cat 에 속할 확률, 즉 전체 cat 중에서 특정 cat 에 
  # 속할 확률을 구한다.
  def cprob(self, f, cat):
    clf = self.fprob(f, cat)
    if clf == 0: return 0 
    
    freqsum = sum([self.fprob(f, c) for c in self.categories()])
    p = clf / (freqsum)
    return p
    
  def invchi2(self, chi, df):
    m = chi / 2.0 
    sum = term = math.exp(-m)
    for i in range(1, df//2):
      term *= m / i
      sum += term 
    return min(sum, 1.0)
    
  def fisherprob(self, item, cat):
    p = 1
    features = self.getFeatures(item)
    for f in features: p *= self.weightedprob(f, cat, self.cprob)
    fscore = -2 * math.log(p)
    return self.invchi2(fscore, len(features)*2)
    
  def classify(self, item, default=None):
    best = default 
    max = 0.0
    for c in self.categories():
      p = self.fisherprob(item, c)
      if p > self.getminimum(c) and p > max: 
        best = c 
        max = p
    return best
  
