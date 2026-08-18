import asyncio
import datetime as dt
import json
import os
import sys
import time
from pathlib import Path

argument=os.environ.get("PYTHON_SERVICE_ARGUMENT","")
config_file=Path(argument)
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from core import fill_daily_sales_template, parse_target_spec, parse_targets, run_queries, send_bot_files, send_bot_message
from telethon import TelegramClient


def job(cfg):
    folder=config_file.parent/"reports"; results=run_queries(cfg); report_file,message=fill_daily_sales_template(results,folder)
    tg=cfg["telegram"]; targets=parse_targets(tg["targets"]); caption=cfg["schedule"].get("caption") or "Daily Sales"; attach=cfg["schedule"].get("format")=="message+xlsx"
    if tg["mode"]=="bot":
        send_bot_message(tg["bot_token"],targets,message)
        if attach: send_bot_files(tg["bot_token"],targets,[report_file],caption)
    else:
        async def send():
            client=TelegramClient(str(config_file.parent/"telegram_user"),int(tg["api_id"]),tg["api_hash"]); await client.connect()
            try:
                if not await client.is_user_authorized(): raise RuntimeError("Telegram user session is not logged in.")
                for target in targets:
                    entity,topic_id=parse_target_spec(target)
                    await client.send_message(entity,message,reply_to=topic_id)
                    if attach: await client.send_file(entity,str(report_file),caption=caption,reply_to=topic_id)
            finally: await client.disconnect()
        asyncio.run(send())


last_date=None
while True:
    try:
        cfg=json.loads(config_file.read_text(encoding="utf-8")); hour,minute=map(int,cfg["schedule"]["time"].split(":")); now=dt.datetime.now()
        if now.hour==hour and now.minute==minute and last_date!=now.date():
            last_date=now.date(); job(cfg)
    except Exception as exc:
        print("Scheduler error:",exc,flush=True)
    time.sleep(20)
