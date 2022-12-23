# encoding: utf-8

import datetime, random, asyncio, inspect
import pony.orm as pony
import models, settings

def last_time():
	soon = None
	now = datetime.datetime.now()
	with pony.db_session:
		soon = pony.select(a.next for a in models.Application if a.next > now and a.valid).min()
	# print("next: {} - {} = {}".format(soon, now, soon - now))
	if soon:
		next = soon - now
		return next.seconds + next.microseconds / 1000000
	return settings.SLEEP_TIME
#end last_next_time

async def callback():
	results = []
	now = datetime.datetime.now()
	with pony.db_session:
		for a in pony.select(a for a in models.Application if a.next <= now and a.valid).for_update():
			results.append(await models.update_app(a, a.redirect_uri))
			a.set(next = now + datetime.timedelta(seconds = random.randint(a.min_interval.seconds, a.max_interval.seconds)))
		#end for
	#end with
	
	if results:
		print("auto update: {}".format(len(list(filter(lambda x: "value" in x, results)))))
	#end if
	
	next = last_time()
	print("now {} next auto update: {}s".format(now, next))
	return next
#end callback

async def timer(init_interval, cb, args=[], kwargs={}):
	if isinstance(init_interval, (int, float)):
		await asyncio.sleep(init_interval)
	elif isinstance(init_interval, datetime.timedelta):
		await asyncio.sleep(init_interval.seconds + init_interval.microseconds / 1000000)
	elif isinstance(init_interval, datetime.datetime):
		next = init_interval - datetime.datetime.now()
		await asyncio.sleep(next.seconds + next.microseconds / 1000000)
	#end if
	
	if inspect.isasyncgenfunction(cb):
		async for next_interval in cb(*args, **kwargs):
			if isinstance(next_interval, (int, float)):
				await asyncio.sleep(next_interval)
			elif isinstance(next_interval, datetime.timedelta):
				await asyncio.sleep(next_interval.seconds + next_interval.microseconds / 1000000)
			elif isinstance(next_interval, datetime.datetime):
				next = next_interval - datetime.datetime.now()
				await asyncio.sleep(next.seconds + next.microseconds / 1000000)
		#end for
	elif inspect.iscoroutinefunction(cb):
		next_interval = await cb(*args, **kwargs)
		while next_interval:
			if isinstance(next_interval, (int, float)):
				await asyncio.sleep(next_interval)
			elif isinstance(next_interval, datetime.timedelta):
				await asyncio.sleep(next_interval.seconds + next_interval.microseconds / 1000000)
			elif isinstance(next_interval, datetime.datetime):
				next = next_interval - datetime.datetime.now()
				await asyncio.sleep(max(0, next.seconds + next.microseconds / 1000000))
			next_interval = await cb(*args, **kwargs)
		#end while
	elif inspect.isgeneratorfunction(cb):
		for next_interval in cb(*args, **kwargs):
			if isinstance(next_interval, (int, float)):
				await asyncio.sleep(next_interval)
			elif isinstance(next_interval, datetime.timedelta):
				await asyncio.sleep(next_interval.seconds + next_interval.microseconds / 1000000)
			elif isinstance(next_interval, datetime.datetime):
				next = next_interval - datetime.datetime.now()
				await asyncio.sleep(next.seconds + next.microseconds / 1000000)
		#end for
	else:
		next_interval = cb(*args, **kwargs)
		while next_interval:
			if isinstance(next_interval, (int, float)):
				await asyncio.sleep(next_interval)
			elif isinstance(next_interval, datetime.timedelta):
				await asyncio.sleep(next_interval.seconds + next_interval.microseconds / 1000000)
			elif isinstance(next_interval, datetime.datetime):
				next = next_interval - datetime.datetime.now()
				await asyncio.sleep(next.seconds + next.microseconds / 1000000)
			next_interval = cb(*args, **kwargs)
		#end while
	#end if
#end timer

asyncio.ensure_future(timer(1, callback))
