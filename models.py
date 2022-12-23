# encoding: utf-8

import datetime, secrets, os, random
import pony.orm as pony
import funcs

db = pony.Database()
# pony.set_sql_debug(True)

class Account(db.Entity):
	id = pony.PrimaryKey(int, auto=True)
	openid = pony.Required(str, index=True, unique=True, default=secrets.token_urlsafe)
#end Account

class User(db.Entity):
	id = pony.PrimaryKey(int, auto=True)
	account_id = pony.Required(int)
	username = pony.Required(str, index=True, unique=True)
	password = pony.Required(bytes)
	salt = pony.Required(bytes)
#end User

class Application(db.Entity):
	id = pony.PrimaryKey(int, auto=True)
	account_id = pony.Required(int, index=True)
	client_id = pony.Required(str)
	secret = pony.Required(str)
	access_token = pony.Optional(str)
	refresh_token = pony.Optional(str)
	expires_in = pony.Optional(datetime.datetime)
	valid = pony.Required(bool, default=False)
	pony.composite_key(account_id, client_id)
	redirect_uri = pony.Optional(str)
	min_interval = pony.Required(datetime.timedelta, default=lambda: datetime.timedelta(seconds=3600))
	max_interval = pony.Required(datetime.timedelta, default=lambda: datetime.timedelta(seconds=7200))
	next = pony.Required(datetime.datetime, default=lambda: datetime.datetime.now() + datetime.timedelta(seconds=random.randint(3600, 7200)), index=True)
	
	def after_delete(self):
		with pony.db_session:
			pony.delete(e for e in Event if e.app_id == self.id)
	#end after_delete
#end Application

class Event(db.Entity):
	id = pony.PrimaryKey(int, auto=True)
	app_id = pony.Required(int, index=True)
	timestamp = pony.Required(datetime.datetime, index=True, default=datetime.datetime.now)
	error_no = pony.Required(int, default=0)
	message = pony.Optional(str)
#end Event

async def update_app(dbapp, redirect_uri):
	now = datetime.datetime.now()
	
	# 刷新 access_token
	if dbapp.expires_in <= now:
		try:
			token = await funcs.refresh_token(dbapp.refresh_token, dbapp.client_id, dbapp.secret, redirect_uri)
		except:
			return { "status" : "error", "reason" : "network error" }
		
		if "error_description" in token:
			with pony.db_session:
				Event(app_id=dbapp.id, error_no=4, message=token.get("error_description"))
				Application.get(id=dbapp.id).set(valid=False)
			return { "status" : "error", "reason" : token.get("error_description") }
		#end if
		
		with pony.db_session:
			Application.get(id = dbapp.id).set(
				access_token = token.get("access_token"),
				refresh_token = token.get("refresh_token", dbapp.refresh_token),
				expires_in = now + datetime.timedelta(seconds=token.get("expires_in")),
			)
			dbapp = Application.get(id=dbapp.id)
		#end with
	#end if
	
	# 获取邮件
	try:
		mail = await funcs.get_mail(dbapp.access_token)
	except:
		return { "status" : "error", "reason" : "network error" }
	if "error_description" in mail:
		with pony.db_session:
			Event(app_id=dbapp.id, error_no=3, message=mail.get("error_description"))
			Application.get(id=dbapp.id).set(valid=False)
		return { "status" : "error", "reason" : mail.get("error_description") }
	#end if
	
	with pony.db_session:
		Event(app_id=dbapp.id, message="got {} mail".format(len(mail.get("value", []))))
	
	return mail
#end update_app
