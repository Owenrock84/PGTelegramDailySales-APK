[app]
title = PG Telegram Reporter
package.name = pgtelegramreports
package.domain = com.owentools
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json,xlsx
version = 1.0.0
requirements = python3,kivy==2.3.1,pg8000,requests,openpyxl,telethon
orientation = portrait
fullscreen = 0
services = Queryscheduler:service/main.py:foreground
android.permissions = INTERNET,FOREGROUND_SERVICE,FOREGROUND_SERVICE_DATA_SYNC,POST_NOTIFICATIONS,WAKE_LOCK
android.api = 35
android.minapi = 23
android.accept_sdk_license = True
android.archs = arm64-v8a,armeabi-v7a
p4a.bootstrap = sdl2

[buildozer]
log_level = 2
warn_on_root = 1
