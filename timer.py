# encoding: utf-8

import datetime, random
from aio_timers import Timer
import pony.orm as pony
import models, settings

def last_time():
	soon = None
	now = datetime.datetime.now()
	with pony.db_session:
		soon = pony.select(a.next for a in models.Application if a.next > now and a.valid).min()
	print("next: {} - {} = ".format(soon, now, soon - now))
	if soon:
		return (soon - now).seconds
	return settings.SLEEP_TIME
#end last_next_time

async def callback():
	results = []
	with pony.db_session:
		for a in pony.select(a for a in models.Application if a.next <= datetime.datetime.now() and a.valid):
			results.append(await models.update_app(a, a.redirect_uri))
			a.set(next=datetime.datetime.now() + datetime.timedelta(seconds=random.randint(a.min_interval.seconds, a.max_interval.seconds)))
		#end for
		pony.commit()
	#end with
	
	if results:
		print("auto update: {}".format(len(list(filter(lambda x: "value" in x, results)))))
	
	next = last_time()
	Timer(next, callback, callback_async=True)
	print("next auto update: {}s".format(next))
#end callback

Timer(1, callback, callback_async=True)
