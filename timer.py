# encoding: utf-8

import datetime
from aio_timers import Timer
import pony.orm as pony
import models, settings

timer = None

def last_time():
	last = pony.select(a for a in models.Application if a.next > datetime.datetime.now() and a.valid).order_by(a.next).first()
	if last:
		return (datetime.datetime.now() - last.next).seconds
	return settings.SLEEP_TIME
#end last_next_time

async def callback():
	results = []
	with pony.db_session:
		for t in pony.select(app for app in models.Application if app.next <= datetime.datetime.now() and app.valid):
			results.append(await models.update_app(app))
			t.set(next=datetime.datetime.now() + t.interval)
		#end for
	#end with
	
	if results:
		print(results)
	
	global timer
	timer = Timer(last_time(), callback, callback_args=[])
#end callback

timer = Timer(1, callback, callback_args=[])
