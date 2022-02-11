# encoding: utf-8

import aiohttp, urllib

async def refresh_token(token, client_id, client_secret, redirect_uri):
	data = {
		"client_id" : client_id,
		"grant_type" : "refresh_token",
		"scope" : "mail.read mail.readbasic mail.readwrite",
		"refresh_token" : token,
		"redirect_uri" : redirect_uri,
		"client_secret" : client_secret,
	}
	
	headers = {
		"Content-Type" : "application/x-www-form-urlencoded",
	}
	
	async with aiohttp.request("POST", "https://login.microsoftonline.com/common/oauth2/v2.0/token", data=urllib.parse.urlencode(data).encode("utf-8"), headers=headers) as response:
		return await response.json()
	#end with
#end refresh_token

async def get_access_token(code, client_id, client_secret, redirect_uri):
	data = {
		"client_id" : client_id,
		"grant_type" : "authorization_code",
		"scope" : "mail.read mail.readbasic mail.readwrite",
		"code" : code,
		"redirect_uri" : redirect_uri,
		"client_secret" : client_secret,
	}
	
	headers = {
		"Content-Type" : "application/x-www-form-urlencoded",
	}
	
	async with aiohttp.request("POST", "https://login.microsoftonline.com/common/oauth2/v2.0/token", data=urllib.parse.urlencode(data).encode("utf-8"), headers=headers) as response:
		return await response.json()
	#end with
#end get_access_token

async def get_mail(token):
	headers = {
		"Authorization" : "Bearer " + token,
		# "Prefer: outlook.body-content-type" : "text",
	}
	
	async with aiohttp.request("GET", "https://graph.microsoft.com/v1.0/me/messages?$select=sender,subject", headers=headers) as response:
		return await response.json()
	#end with
#end get_mail

async def get_access_token_without_code(client_id, client_secret):
	data = {
		"client_id" : client_id,
		"scope" : "https://graph.microsoft.com/.default",
		"client_secret" : client_secret,
		"grant_type" : "client_credentials",
	}
	
	headers = {
		"Content-Type" : "application/x-www-form-urlencoded",
	}
	
	async with aiohttp.request("POST", "https://login.microsoftonline.com/common/oauth2/v2.0/token", data=urllib.parse.urlencode(data).encode("utf-8"), headers=headers) as response:
		return await response.json()
	#end with
#end get_access_token_without_code
