# encoding: utf-8

import typing, fastapi, urllib, aiohttp, secrets, datetime, pydantic, hmac, os
import pony.orm as pony
import settings, funcs, models

app = fastapi.FastAPI()
models.db.bind(**settings.DATABASE)
models.db.generate_mapping(create_tables=True)

@app.get("/")
def home():
	return { "status" : "ok" }
#end home

class MemberData(pydantic.BaseModel):
	username : str
	password : str
#end MemberData

@app.post("/api/new-user")
def new_user(body : MemberData):
	"""
	注册新用户
	"""
	
	with pony.db_session:
		if models.User.get(username=body.username):
			return { "status" : "error", "reason" : "username already exists" }
	#end with
	
	account = None
	with pony.db_session:
		account = models.Account()
	
	salt = os.urandom(16)
	password = hmac.new(body.password.encode("utf-8"), salt, "sha256").digest()
	
	with pony.db_session:
		user = models.User(account_id=account.id, username=body.username, password=password, salt=salt)
	return { "status" : "ok", "openid" : account.openid }
#end new_user

@app.post("/api/user-login")
def new_user(body : MemberData):
	"""
	用户登录
	"""
	
	account = None
	with pony.db_session:
		user = models.User.get(username=body.username)
		if not user:
			return { "status" : "error", "reason" : "bad username or password" }
		if not hmac.compare_digest(hmac.new(body.password.encode("utf-8"), user.salt, "sha256").digest(), user.password):
			return { "status" : "error", "reason" : "bad username or password" }
		account = models.Account.get(id=user.account_id)
	#end with
	
	return { "status" : "ok", "openid" : account.openid }
#end new_user

class NewAppData(pydantic.BaseModel):
	client_id : str
	secret : str
#end NewAppData

@app.post("/api/new-app/{openid}")
async def new_app(openid : str, body : NewAppData):
	"""
	添加新的应用程序
	"""
	
	# 确认 openid 有效
	account = None
	with pony.db_session:
		account = models.Account.get(openid=openid)
		if not account:
			return { "status" : "error", "reason" : "openid not found" }
	#end with
	
	# 验证 client_id 和 secret
	try:
		result = await funcs.get_access_token_without_code(body.client_id, body.secret)
	except:
		return { "status" : "error", "reason" : "network error" }
	if "error_description" in result:
		return { "status" : "error", "reason" : result["error_description"] }
	
	# 查重
	with pony.db_session:
		if models.Application.get(account_id=account.id, client_id=body.client_id):
			return { "status" : "error", "reason" : "client_id already exists" }
	#end with
	
	# 添加
	dbapp = None
	with pony.db_session:
		dbapp = models.Application(account_id=account.id, client_id=body.client_id, secret=body.secret)
	#end with
	
	return { "status" : "ok", "app_id" : dbapp.id }
#end new_app

class SetAppData(pydantic.BaseModel):
	secret : str
#end SetAppData

@app.post("/api/set-app/{openid}/{app_id}")
async def set_app(openid : str, app_id : int, body : SetAppData):
	"""
	更新现有的app secret
	"""
	
	# 确认 openid 有效
	account = None
	with pony.db_session:
		account = models.Account.get(openid=openid)
		if not account:
			return { "status" : "error", "reason" : "openid not found" }
	#end with
	
	# 获取 app
	dbapp = None
	with pony.db_session:
		dbapp = models.Application.get(id=app_id, account_id=account.id)
		if not dbapp:
			return { "status" : "error", "reason" : "app_id not found" }
	#end with
	
	# 验证 client_id 和 secret
	try:
		result = await funcs.get_access_token_without_code(dbapp.client_id, body.secret)
	except:
		return { "status" : "error", "reason" : "network error" }
	if "error_description" in result:
		with pony.db_session:
			models.Event(app_id=dbapp.id, error_no=4, message=result["error_description"])
			models.Application.get(id=dbapp.id).set(valid=False)
		return { "status" : "error", "reason" : result["error_description"] }
	#end if
	
	# 更新 secret
	with pony.db_session:
		models.Application.get(id=dbapp.id).set(secret=body.secret, valid=(dbapp.access_token and dbapp.refresh_token and dbapp.expires_in))
	
	return { "status" : "ok" }
#end set_app

@app.get("/api/app-authorize/{openid}/{app_id}")
async def authorize_app(openid : str, app_id : int, response: fastapi.Response, host : str = fastapi.Header(None)):
	"""
	登录以获取授权
	"""
	
	# 确认 openid 有效
	account = None
	with pony.db_session:
		account = models.Account.get(openid=openid)
		if not account:
			return { "status" : "error", "reason" : "openid not found" }
	#end with
	
	# 获取 app
	dbapp = None
	with pony.db_session:
		dbapp = models.Application.get(id=app_id, account_id=account.id)
		if not dbapp:
			return { "status" : "error", "reason" : "app_id not found" }
	#end with
	
	scherma = "http" if host.startswith("localhost") else "https"
	data = {
		"client_id" : dbapp.client_id,
		"redirect_uri" : f"{scherma}://{host}/api/app-result",
		"scope" : "offline_access mail.read mail.readbasic mail.readwrite",
		"response_mode" : "query",
		"response_type" : "code",
		"state" : f"{account.id}|{app_id}",
	}
	
	response.headers["Location"] = "https://login.microsoftonline.com/common/oauth2/v2.0/authorize?" + urllib.parse.urlencode(data)
	return { "status" : "ok", "redirect_uri" : response.headers["Location"] }
#end authorize_app

@app.get("/api/app-result")
async def app_result(
	state : typing.Optional[str] = None,
	code : typing.Optional[str] = None,
	error_description : typing.Optional[str] = None,
	host : str = fastapi.Header(None)):
	"""
	接收返回结果
	"""
	
	if error_description:
		return { "status" : "error", "reason" : error_description }
	
	if not state or not code:
		return { "status" : "ok" }
	
	try:
		account_id, app_id = state.split("|")
	except:
		return { "status" : "error", "reason" : "bad state" }
	
	dbapp = None
	with pony.db_session:
		dbapp = models.Application.get(id=app_id, account_id=account_id)
		if not dbapp:
			return { "status" : "error", "reason" : "state invalid" }
	#end with
	
	scherma = "http" if host.startswith("localhost") else "https"
	redirect_uri = f"{scherma}://{host}/api/app-result"
	token = await funcs.get_access_token(code, dbapp.client_id, dbapp.secret, redirect_uri)
	if "error_description" in token:
		with pony.db_session:
			models.Event(app_id=app_id, error_no=1, message=token.get("error_description"))
			models.Application.get(id=app_id).set(valid=False)
		return { "status" : "error", "reason" : token.get("error_description") }
	#end if
	
	mail = await funcs.get_mail(token.get("access_token"))
	if "error_description" in mail:
		with pony.db_session:
			models.Event(app_id=app_id, error_no=2, message=mail.get("error_description"))
			models.Application.get(id=app_id).set(valid=False)
		return { "status" : "error", "reason" : mail.get("error_description") }
	#end if
	
	with pony.db_session:
		models.Application.get(id=dbapp.id).set(
			access_token=token.get("access_token"),
			refresh_token=token.get("refresh_token"),
			expires_in=datetime.datetime.now() + datetime.timedelta(seconds=token.get("expires_in")),
			valid=True,
		)
	#end with
	
	return { "status" : "ok", "mail_count" : len(mail.get("value", [])) }
#end app_result

@app.get("/api/app-update/{openid}/{app_id}")
async def app_update(openid : str, app_id : int, host : str = fastapi.Header(None)):
	"""
	获取邮件数量
	"""
	
	# 确认 openid 有效
	account = None
	with pony.db_session:
		account = models.Account.get(openid=openid)
		if not account:
			return { "status" : "error", "reason" : "openid not found" }
	#end with
	
	# 获取 app
	dbapp = None
	with pony.db_session:
		dbapp = models.Application.get(id=app_id, account_id=account.id)
		if not dbapp:
			return { "status" : "error", "reason" : "app_id not found" }
	#end with
	
	if not dbapp.valid:
		event = pony.select(e for e in models.Event if e.app_id == dbapp.id and e.error_no).order_by(pony.desc(models.Event.timestamp)).first()
		if event:
			return { "status" : "error", "reason" : "bad app: " + event.message }
		return { "status" : "error", "reason" : "bad app" }
	#end if
	
	# 刷新 access_token
	if dbapp.expires_in <= datetime.datetime.now():
		scherma = "http" if host.startswith("localhost") else "https"
		redirect_uri = f"{scherma}://{host}/api/app-result"
		token = await funcs.refresh_token(dbapp.refresh_token, dbapp.client_id, dbapp.secret, redirect_uri)
		if "error_description" in token:
			return { "status" : "error", "reason" : token.get("error_description") }
		
		with pony.db_session:
			models.Application.get(id=dbapp.id).set(
				access_token=token.get("access_token"),
				refresh_token=token.get("refresh_token", dbapp.refresh_token),
				expires_in=datetime.datetime.now() + datetime.timedelta(seconds=token.get("expires_in")),
			)
		#end with
	#end if
	
	mail = await funcs.get_mail(dbapp.access_token)
	if "error_description" in mail:
		with pony.db_session:
			models.Event(app_id=dbapp.id, error_no=3, message=mail.get("error_description"))
			models.Application.get(id=dbapp.id).set(valid=False)
		return { "status" : "error", "reason" : mail.get("error_description") }
	#end if
	
	with pony.db_session:
		models.Event(app_id=dbapp.id, message="got {} mail".format(len(mail.get("value", []))))
	
	return { "status" : "ok", "mail_count" : len(mail.get("value", [])) }
#end app_update
