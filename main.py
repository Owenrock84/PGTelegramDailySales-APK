"""Android Kivy interface. Build with buildozer.spec."""
import asyncio
import json
import os
import threading
from pathlib import Path

from kivy.app import App
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.checkbox import CheckBox
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput
from telethon import TelegramClient, errors
try:
    from telethon.tl.functions.messages import GetForumTopicsRequest
    FORUM_TOPICS_PEER_ARGUMENT = "peer"
except ImportError:
    from telethon.tl.functions.channels import GetForumTopicsRequest
    FORUM_TOPICS_PEER_ARGUMENT = "channel"

from core import fill_daily_sales_template, parse_target_spec, parse_targets, run_queries, send_bot_files, send_bot_message


def lab(text):
    widget=Label(text=text,size_hint_y=None,height=dp(34),halign="left",valign="middle")
    widget.bind(size=lambda obj,size:setattr(obj,"text_size",size)); return widget


class ReporterAndroid(App):
    def build(self):
        self.title="PG Telegram Reporter"; self.fields={}; self.session=str(Path(self.user_data_dir)/"telegram_user")
        outer=BoxLayout(orientation="vertical",padding=dp(8),spacing=dp(6))
        outer.add_widget(lab("[b]PostgreSQL → Telegram Reporter[/b]"))
        scroll=ScrollView(); form=GridLayout(cols=1,size_hint_y=None,spacing=dp(4)); form.bind(minimum_height=form.setter("height")); scroll.add_widget(form)
        self._field(form,"host","PostgreSQL host/IP"); self._field(form,"port","Port","5432")
        self._field(form,"database","Database name"); self._field(form,"db_user","Database user"); self._field(form,"db_password","Database password",password=True)
        form.add_widget(lab("SSL mode")); self.ssl_mode=Spinner(text="require",values=("require","allow-self-signed","disable"),size_hint_y=None,height=dp(44)); form.add_widget(self.ssl_mode)
        self._field(form,"query1","Query 1 — Yesterday: Bet, Win, Hand, Gross, Profit",multiline=True,height=130)
        self._field(form,"query2","Query 2 — MTD: Bet, Win, Hand, Gross, Profit",multiline=True,height=130)
        form.add_widget(lab("Telegram posting mode")); self.mode=Spinner(text="bot",values=("bot","user"),size_hint_y=None,height=dp(44)); form.add_widget(self.mode)
        self._field(form,"bot_token","BotFather token",password=True)
        self._field(form,"api_id","Telegram API ID"); self._field(form,"api_hash","Telegram API Hash",password=True); self._field(form,"phone","Phone (+60…)")
        self._field(form,"code","Login code (not saved)"); self._field(form,"password","Telegram 2FA (not saved)",password=True)
        self._field(form,"targets","Selected groups/topics — @group or @group|topic_id",multiline=True,height=120)
        self._field(form,"time","Daily time HH:MM","09:00")
        form.add_widget(lab("Delivery mode")); self.output=Spinner(text="message",values=("message","message+xlsx"),size_hint_y=None,height=dp(44)); form.add_widget(self.output)
        self._field(form,"caption","Attachment caption (message+xlsx only)","Daily Sales")
        secret=BoxLayout(size_hint_y=None,height=dp(48)); self.save_secrets=CheckBox(size_hint_x=None,width=dp(48)); secret.add_widget(self.save_secrets); secret.add_widget(lab("Save passwords/tokens in Android private app storage")); form.add_widget(secret)
        outer.add_widget(scroll)
        for title,method in [("SAVE SETTINGS",self.save),("SEND LOGIN CODE",self.send_code),("LOGIN USER",self.login),("SCAN USER GROUPS / TOPICS",self.scan_groups),("RUN NOW",self.run_now),("START DAILY SERVICE",self.start_service)]:
            button=Button(text=title,size_hint_y=None,height=dp(48)); button.bind(on_release=lambda _btn,fn=method:fn()); outer.add_widget(button)
        self.status=lab("Configure both read-only queries and selected Telegram groups."); self.status.height=dp(60); outer.add_widget(self.status)
        self.load(); return outer

    def _field(self,parent,key,title,value="",password=False,multiline=False,height=44):
        parent.add_widget(lab(title)); field=TextInput(text=value,password=password,multiline=multiline,size_hint_y=None,height=dp(height)); parent.add_widget(field); self.fields[key]=field

    def data(self,for_storage=False):
        f=self.fields
        cfg={"database":{"host":f["host"].text.strip(),"port":f["port"].text.strip(),"name":f["database"].text.strip(),"user":f["db_user"].text.strip(),"password":f["db_password"].text,"ssl":self.ssl_mode.text},
             "query1":f["query1"].text.strip(),"query2":f["query2"].text.strip(),
             "telegram":{"mode":self.mode.text,"bot_token":f["bot_token"].text.strip(),"api_id":f["api_id"].text.strip(),"api_hash":f["api_hash"].text.strip(),"phone":f["phone"].text.strip(),"targets":f["targets"].text.strip()},
             "schedule":{"time":f["time"].text.strip(),"format":self.output.text,"caption":f["caption"].text.strip()}}
        if for_storage and not self.save_secrets.active:
            cfg["database"]["password"]=""; cfg["telegram"]["bot_token"]=""; cfg["telegram"]["api_hash"]=""
        return cfg

    @property
    def config_file(self): return Path(self.user_data_dir)/"config.json"

    def save(self):
        self.config_file.write_text(json.dumps(self.data(True),indent=2),encoding="utf-8"); self.set_status("Settings saved in Android private app storage.")

    def load(self):
        if not self.config_file.exists(): return
        try:
            cfg=json.loads(self.config_file.read_text(encoding="utf-8")); db=cfg["database"]; tg=cfg["telegram"]; sc=cfg["schedule"]
            mapping={"host":db["host"],"port":db["port"],"database":db["name"],"db_user":db["user"],"db_password":db.get("password",""),"query1":cfg["query1"],"query2":cfg["query2"],"bot_token":tg.get("bot_token",""),"api_id":tg.get("api_id",""),"api_hash":tg.get("api_hash",""),"phone":tg.get("phone",""),"targets":tg.get("targets",""),"time":sc["time"],"caption":sc.get("caption","")}
            for key,value in mapping.items(): self.fields[key].text=str(value)
            self.ssl_mode.text=db.get("ssl","require"); self.mode.text=tg.get("mode","bot"); self.output.text=sc.get("format","xlsx")
        except Exception as exc: self.alert("Load error",str(exc))

    def set_status(self,text): Clock.schedule_once(lambda *_:setattr(self.status,"text",text))
    def alert(self,title,text):
        def show(*_):
            box=BoxLayout(orientation="vertical",padding=dp(8)); box.add_widget(Label(text=text)); ok=Button(text="OK",size_hint_y=None,height=dp(48)); pop=Popup(title=title,content=box,size_hint=(.92,.5)); ok.bind(on_release=pop.dismiss); box.add_widget(ok); pop.open()
        Clock.schedule_once(show)
    def background(self,fn,*args): threading.Thread(target=lambda:self._safe(fn,*args),daemon=True).start()
    def _safe(self,fn,*args):
        try: fn(*args)
        except Exception as exc: self.alert("Error",str(exc)); self.set_status(f"FAILED: {exc}")

    def send_code(self):
        cfg=self.data()["telegram"]; self.background(lambda:asyncio.run(self._send_code(cfg)))
    async def _send_code(self,cfg):
        client=TelegramClient(self.session,int(cfg["api_id"]),cfg["api_hash"]); await client.connect()
        try:
            if await client.is_user_authorized(): self.set_status("User account is already logged in.")
            else: await client.send_code_request(cfg["phone"]); self.set_status("Code sent. Enter it and tap LOGIN USER.")
        finally: await client.disconnect()

    def login(self):
        cfg=self.data()["telegram"]; code=self.fields["code"].text.strip(); password=self.fields["password"].text
        self.background(lambda:asyncio.run(self._login(cfg,code,password)))
    async def _login(self,cfg,code,password):
        client=TelegramClient(self.session,int(cfg["api_id"]),cfg["api_hash"]); await client.connect()
        try:
            if not await client.is_user_authorized():
                try: await client.sign_in(cfg["phone"],code)
                except errors.SessionPasswordNeededError: await client.sign_in(password=password)
            self.set_status("Telegram user login successful.")
        finally: await client.disconnect()

    def scan_groups(self):
        cfg=self.data()["telegram"]
        self.background(lambda:asyncio.run(self._scan_groups(cfg)))
    async def _scan_groups(self,cfg):
        client=TelegramClient(self.session,int(cfg["api_id"]),cfg["api_hash"]); await client.connect()
        try:
            if not await client.is_user_authorized(): raise RuntimeError("Login to Telegram user mode first.")
            groups=[]
            async for dialog in client.iter_dialogs():
                if not dialog.is_group: continue
                value=f"@{dialog.entity.username}" if getattr(dialog.entity,"username",None) else str(dialog.id)
                groups.append((dialog.name,value))
                if getattr(dialog.entity,"forum",False):
                    kwargs={FORUM_TOPICS_PEER_ARGUMENT:dialog.entity,"q":"","offset_date":None,"offset_id":0,"offset_topic":0,"limit":100}
                    forum=await client(GetForumTopicsRequest(**kwargs))
                    for topic in forum.topics:
                        if getattr(topic,"title",None): groups.append((f"{dialog.name} → {topic.title}",f"{value}|{topic.id}"))
            Clock.schedule_once(lambda *_:self._group_picker(groups))
            self.set_status(f"Found {len(groups)} groups/topics.")
        finally: await client.disconnect()
    def _group_picker(self,groups):
        content=BoxLayout(orientation="vertical",padding=dp(6),spacing=dp(4)); grid=GridLayout(cols=1,size_hint_y=None,spacing=dp(2)); grid.bind(minimum_height=grid.setter("height")); checks=[]
        for name,value in groups:
            row=BoxLayout(size_hint_y=None,height=dp(48)); check=CheckBox(size_hint_x=None,width=dp(46)); row.add_widget(check); row.add_widget(lab(name)); grid.add_widget(row); checks.append((check,value))
        scroll=ScrollView(); scroll.add_widget(grid); content.add_widget(scroll)
        use=Button(text="USE SELECTED",size_hint_y=None,height=dp(48)); content.add_widget(use)
        popup=Popup(title="Select Telegram groups/topics",content=content,size_hint=(.96,.9))
        def apply(*_):
            self.fields["targets"].text="\n".join(value for check,value in checks if check.active); popup.dismiss()
        use.bind(on_release=apply); popup.open()

    def run_now(self): self.background(self._job,self.data())
    def _job(self,cfg):
        self.set_status("Running Yesterday and MTD queries…"); results=run_queries(cfg); report_file,message=fill_daily_sales_template(results,Path(self.user_data_dir)/"reports")
        targets=parse_targets(cfg["telegram"]["targets"]); caption=cfg["schedule"].get("caption") or "Daily Sales"; attach=cfg["schedule"].get("format")=="message+xlsx"
        if not targets: raise RuntimeError("No Telegram targets configured.")
        if cfg["telegram"]["mode"]=="bot":
            send_bot_message(cfg["telegram"]["bot_token"],targets,message,self.set_status)
            if attach: send_bot_files(cfg["telegram"]["bot_token"],targets,[report_file],caption,self.set_status)
        else: asyncio.run(self._send_user(cfg,targets,message,report_file if attach else None,caption))
        self.set_status("Daily Sales message sent successfully.")
    async def _send_user(self,cfg,targets,message,report_file,caption):
        tg=cfg["telegram"]; client=TelegramClient(self.session,int(tg["api_id"]),tg["api_hash"]); await client.connect()
        try:
            if not await client.is_user_authorized(): raise RuntimeError("Login to Telegram user mode first.")
            for target in targets:
                entity,topic_id=parse_target_spec(target)
                await client.send_message(entity,message,reply_to=topic_id)
                if report_file: await client.send_file(entity,str(report_file),caption=caption,reply_to=topic_id)
        finally: await client.disconnect()

    def start_service(self):
        self.save()
        if not self.save_secrets.active: self.alert("Secrets required","Enable saving secrets so the background service can connect after the app closes."); return
        try:
            from android import mActivity
            from jnius import autoclass
            service=autoclass("com.owentools.pgtelegramreports.ServiceQueryscheduler")
            service.start(mActivity,str(self.config_file)); self.set_status("Android foreground daily service started.")
        except Exception as exc: self.alert("Service error",str(exc))


ReporterAndroid().run()
