from apscheduler.schedulers.background import BackgroundScheduler
import time

class Scheduler(object):
  def __init__(self):
    self.sched = BackgroundScheduler()
    self.sched.start()
    self.job_id = ''

  def __del__(self):
    self.shutdown()

  def shutdown(self):
    self.sched.shutdown()

  def kill_scheduler(self, job_id):
    try:
      self.sched.remove_job(job_id)
    except:
      print 'fail to stop scheduler'
      return

  def hello(self, type, job_id):
    print('%s scheduler process_id[%s] : %d' % (type, job_id, time.localtime().tm_sec))


  def scheduler(self, type, job_id):
    print '%s scheduler start' % type
    if type == 'interval':
      self.sched.add_job(self.hello, type, seconds=10, id=job_id, args=(type,job_id))
    elif type == 'cron':
      self.sched.add_job(self.hello, type, day_of_week='mon-fri', 
        hour='0-23', second='*/2', id=job_id, args=(type, job_id))


if __name__ == '__main__':
  scheduler = Scheduler()
  scheduler.scheduler('cron', '1')
  scheduler.scheduler('interval', '2')

  count = 0
  while True:
    print 'Running main process ...'
    time.sleep(1)
    count += 1
    if count == 10:
      scheduler.kill_scheduler('1')
      print 'Kill cron schedule'
    elif count == 30:
      scheduler.kill_scheduler('2')
      print 'Kill interval schedule'
