# encoding: utf-8

import datetime, secrets, os
import pony.orm as pony

db = pony.Database()

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
#end Application

class Event(db.Entity):
	id = pony.PrimaryKey(int, auto=True)
	app_id = pony.Required(int, index=True)
	timestamp = pony.Required(datetime.datetime, index=True, default=datetime.datetime.now)
	error_no = pony.Required(int, default=0)
	message = pony.Optional(str)
#end Event
