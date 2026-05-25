"""expand_vague_ins.py  (v3 — Taodian added, near-duplicates pruned)

Adjusted strategy:
  1. MobileWorld is the PRIMARY source so we can directly reuse its built-in
     deterministic eval environment (Docker'd Pixel-8 + per-task is_successful
     checkers in src/mobile_world/tasks/definitions/<folder>/*.py).
     Each MobileWorld entry carries `_mw_task_path` pointing to the original
     checker file; `_mw_task_class` is auto-resolved by AST parsing.
  2. EVERY app referenced in any new entry has populated `action_object_str`
     in app-data/knowledge-base/AppUi-final.json — guaranteeing VagueAider's
     L3 generation has real action chains to draw from.
  3. Near-duplicate MobileWorld variants (set_alarm × 4, plan_route_sms × 4,
     schedule_lunch × 2, share_photos × 2) have been pruned from earlier
     versions; one canonical entry kept per task pattern.

MobileWorld declared app_names  ->  KB AppUi-final.json canonical name
(only mappings with KB AOS coverage are usable; others are skipped):
  Mail        -> gmail              (KB id 23, 6 AOS funcs)        ✓ used
  Messages    -> 信息                (KB id 85, 7 AOS funcs)        ✓ used
  Calendar    -> 日历                (KB id 92, 5 AOS funcs)        ✓ used
  MCP-Amap    -> 高德地图(Amap)       (KB id 29, 5 AOS funcs)        ✓ used
  Maps        -> googleMap          (KB id 40, 8 AOS funcs)        ✓ used
  Chrome      -> Chrome / GoogleChrome (KB id 68/100, 5/7 AOS)    ✓ used
  Gallery     -> 相册                (KB id 88, 7 AOS funcs)        ✓ used
  Clock       -> 闹钟                (KB id 89, 10 AOS funcs)       ✓ used
  Taodian     -> 淘宝                (KB id 112, 12 AOS funcs)      ✓ used  ⭐ new
  --------- NOT usable ----------
  Camera      -> 相机 (KB id 83, NO AOS)                            ✗ skip
  Settings    -> 设置 (KB id 84, NO AOS)                            ✗ skip
  Contacts    -> (no KB equivalent)                                ✗ skip
  Files       -> (no KB equivalent)                                ✗ skip
  Mastodon    -> (no KB equivalent — X is closest, no AOS)         ✗ skip
  Mattermost  -> (no KB equivalent — Slack closest, no AOS)        ✗ skip
  Docreader   -> (no KB equivalent)                                ✗ skip
  MCP-arXiv / MCP-Github / MCP-jina / MCP-stockstar -> n/a         ✗ skip

KB apps WITHOUT action_object_str (do NOT use for L3 synthesis):
  铁路12306 / 飞猪旅行 / 去哪儿网 (note: '去哪儿旅行' id 97 DOES have AOS)
  设置 / 相机 / 邮件 / 应用商店 / DeepSeek / Google / Gemini / Slack /
  Zoom / Teams / Microsoft / 钉钉 / Steam / spotify / Twitch / Strava /
  Duolingo / Classroom / MyFitnessPal / 喜马拉雅 / PS / 剪映 / 醒图 /
  美图秀秀-(Meitu) / wps_office / Airbnb / Uber / 支付宝 / PayPal / Binance /
  Revolut / Wise / 云闪付 / 百度网盘 / 迅雷 / 飞书 / QQ邮箱 / grok /
  Doubao / 元宝 / 腾讯地图 / 航旅纵横 / trip / citymapper / grab /
  扫描全能王
"""

from __future__ import annotations

import json
import os

REPO = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
ORIG = os.path.join(REPO, "app-data", "Ins-bench", "Vague-ins.json")
OUT  = os.path.join(REPO, "app-data", "Ins-bench", "Vague-ins-expanded.json")


# Each new task is a 7-field dict matching the Vague-ins.json schema, plus:
#   _source_bench    : provenance tag (rewrite_v2 preserves unknown keys)
#   _mw_task_path    : MobileWorld task .py path (only on MobileWorld entries)
#   _mw_task_class   : MobileWorld BaseTask subclass name — used by
#                      `mw eval --task <ClassName>` for fanout in
#                      Mobile-Agent-E/instr_rewrite/mw_eval_runner.py
NEW_TASKS: list[dict] = [
    # ============================================================
    # MobileWorld (PRIMARY) — single-app tasks
    # ============================================================
    {
        "Task_id": 56, "Task Type": "系统软件",
        "Invovled_App_Name": "闹钟",
        "Original-INS": "Please set a wake-up alarm for me on Friday.",
        "Level1-INS": "Set my wake-up alarm for Friday.",
        "Level2-INS": "Open the Clock app and add a Friday-repeating alarm at the time I want (ask me for the time).",
        "Level3-INS": "Open the Clock app, tap the '+' button in the top right corner of the Alarm tab, ask the user for the desired alarm time and set it, tap the repeat option and select only 'Friday', then tap the 'Save' button in the top right corner.",
        "_source_bench": "MobileWorld",
        "_mw_task_path": "native/set_alarm_ask_user_1.py",
    },
    {
        "Task_id": 58, "Task Type": "社交媒体",
        "Invovled_App_Name": "信息",
        "Original-INS": "Delete all messages in SMS app sent from my company.",
        "Level1-INS": "Delete all the messages from my company.",
        "Level2-INS": "Open the Messages app and delete every SMS thread whose sender is my company.",
        "Level3-INS": "Open the Messages app, scroll through the conversation list, long-press the first message thread sent by the company to enter multi-select mode, tap each additional company message to add it to the selection, then tap the trash icon at the top and confirm to delete.",
        "_source_bench": "MobileWorld",
        "_mw_task_path": "messages/delete_messages_ask_user.py",
    },
    {
        "Task_id": 59, "Task Type": "社交媒体",
        "Invovled_App_Name": "信息",
        "Original-INS": "Delete the message about deployment issues in SMS app sent from my company.",
        "Level1-INS": "Delete the company message about deployment issues.",
        "Level2-INS": "Open the Messages app and delete the specific message about deployment issues sent from my company.",
        "Level3-INS": "Open the Messages app, tap the search icon at the top and type 'deployment' to locate the relevant thread, open the thread, long-press the message about deployment issues, tap the trash icon, then confirm the deletion.",
        "_source_bench": "MobileWorld",
        "_mw_task_path": "messages/delete_single_message_ask_user.py",
    },
    {
        "Task_id": 60, "Task Type": "系统软件",
        "Invovled_App_Name": "日历",
        "Original-INS": "My schedule on 10/20 is a bit full, please remove a few events.",
        "Level1-INS": "My schedule on 10/20 is too packed, drop a few events.",
        "Level2-INS": "Open the Calendar app, navigate to October 20, and delete a few of the events on that day.",
        "Level3-INS": "Open the Calendar app, tap the date picker at the top and navigate to October 20, tap on a low-priority event to view its details, tap the three-dot menu and choose 'Delete', confirm the deletion, then repeat for one or two more events on that day.",
        "_source_bench": "MobileWorld",
        "_mw_task_path": "calendar/delete_event_ask_user.py",
    },
    {
        "Task_id": 61, "Task Type": "系统软件",
        "Invovled_App_Name": "日历",
        "Original-INS": "How many deduplicated events are there in the calendar, from October 20 to October 26?",
        "Level1-INS": "How many unique events do I have between Oct 20 and Oct 26?",
        "Level2-INS": "Open the Calendar app, browse the events in the Oct 20–26 range, and report the count of distinct (deduplicated) events.",
        "Level3-INS": "Open the Calendar app, switch to Week view via the view-switcher at the top, navigate to the week containing October 20–26, scroll through each day to enumerate all events, mentally deduplicate identical titles, and report the final count.",
        "_source_bench": "MobileWorld",
        "_mw_task_path": "calendar/check_deduplicated_events.py",
    },
    {
        "Task_id": 62, "Task Type": "办公协助",
        "Invovled_App_Name": "gmail",
        "Original-INS": "Reply to Daniel's most recent email to tell him: 'I'll be there at 10:00 AM on Thursday.'",
        "Level1-INS": "Tell Daniel by email I'll be there at 10 AM Thursday.",
        "Level2-INS": "Open Gmail, find Daniel's most recent email, and reply with 'I'll be there at 10:00 AM on Thursday.'",
        "Level3-INS": "Open the Gmail app, in the inbox locate Daniel's most recent email by sender name and tap it open, tap the 'Reply' button at the bottom, type 'I'll be there at 10:00 AM on Thursday.' in the text field, then tap the send icon (blue triangle) at the top right.",
        "_source_bench": "MobileWorld",
        "_mw_task_path": "gmail/accept_meeting.py",
    },
    {
        "Task_id": 63, "Task Type": "办公协助",
        "Invovled_App_Name": "gmail",
        "Original-INS": "Send the file 'waiver.jpg' as an email attachment to bob@gmail.com. Title the email 'Updated waiver'.",
        "Level1-INS": "Email the waiver file to Bob with the title 'Updated waiver'.",
        "Level2-INS": "Open Gmail, compose a new email to bob@gmail.com with subject 'Updated waiver' and attach waiver.jpg.",
        "Level3-INS": "Open the Gmail app, tap the 'Compose' button at the bottom right, enter bob@gmail.com in the To field, type 'Updated waiver' in the Subject field, tap the paperclip icon at the top to attach a file, navigate to and select 'waiver.jpg', then tap the send icon (blue triangle) at the top right.",
        "_source_bench": "MobileWorld",
        "_mw_task_path": "gmail/send_waiver.py",
    },
    {
        "Task_id": 64, "Task Type": "办公协助",
        "Invovled_App_Name": "gmail",
        "Original-INS": "Could you reply to Daniel's most recent email to tell him I'll have to cancel the meeting on Thursday?",
        "Level1-INS": "Tell Daniel by email I have to cancel Thursday's meeting.",
        "Level2-INS": "Open Gmail, find Daniel's most recent email, and reply to cancel the Thursday meeting.",
        "Level3-INS": "Open the Gmail app, locate Daniel's most recent email in the inbox and tap it open, tap the 'Reply' button at the bottom, type a message like 'I'll have to cancel our meeting on Thursday — sorry for the late notice.' in the text field, then tap the send icon at the top right.",
        "_source_bench": "MobileWorld",
        "_mw_task_path": "gmail/cancel_meeting.py",
    },

    # ----- MobileWorld two-app -----
    {
        "Task_id": 65, "Task Type": "生活",
        "Invovled_App_Name": "高德地图(Amap)、信息",
        "Original-INS": "明天下午我朋友要来杭州西溪这边，你帮我查一下杭州明天白天的天气和情况和温度发送给我的朋友，电话100077788236",
        "Level1-INS": "明天朋友来杭州西溪，帮我查一下杭州明天白天的天气温度发给他。",
        "Level2-INS": "在高德地图中查询杭州明天白天的天气情况和温度，然后用信息app将结果短信发送给电话100077788236。",
        "Level3-INS": "打开高德地图app，点击中间的搜索框输入'杭州'选定城市，切到天气/服务卡片查看明天白天的天气状况和温度数值。切换到信息app，点击右下角的'写信息'按钮，在收件人栏输入电话号码100077788236，在正文中输入'杭州明天白天的天气：xx，温度xx度'，点击发送按钮。",
        "_source_bench": "MobileWorld",
        "_mw_task_path": "messages/send_weather_sms.py",
    },
    {
        "Task_id": 66, "Task Type": "生活",
        "Invovled_App_Name": "高德地图(Amap)、信息",
        "Original-INS": "中介给我发了两套房子的信息，我想比较一下哪一套离阿里西溪c园区开车更近，好决定租哪一间。把最近那套房子的地址发给我朋友 Mia",
        "Level1-INS": "比较一下中介发的两套房子哪一套离阿里西溪C园区更近，把更近的那套地址发给Mia。",
        "Level2-INS": "在信息app中查看中介发来的两套房子地址，用高德地图分别查两个地址到阿里西溪C园区的驾车距离，选出更近的一套，然后通过信息app把更近的那套房址发送给Mia。",
        "Level3-INS": "打开信息app找到中介发来的两套房子地址记下来。切到高德地图app，点击中间搜索框输入第一个房址查询，然后点击'路线'按钮，将终点设为'阿里西溪C园区'，记下驾车距离。返回搜索同样方法查第二个房址到园区的距离。比较后回到信息app，搜索联系人'Mia'进入聊天页，输入更近那套的地址并发送。",
        "_source_bench": "MobileWorld",
        "_mw_task_path": "messages/compare_apartments_distance_sms.py",
    },
    {
        "Task_id": 67, "Task Type": "生活",
        "Invovled_App_Name": "高德地图(Amap)、信息",
        "Original-INS": "我现在的位置在西溪园区亲橙客栈，家里有人突然感冒，你帮我查500米范围内的药店，以`name：address`的格式，每个药店一行，帮我短信给我妻子1997777900",
        "Level1-INS": "西溪园区附近500米的药店都有哪些？把列表短信发给我妻子。",
        "Level2-INS": "在高德地图中以西溪园区亲橙客栈为中心搜索500米范围内的药店，列出每家的名称和地址，然后用信息app把列表短信发送到号码1997777900。",
        "Level3-INS": "打开高德地图app，点击中间搜索框输入'西溪园区亲橙客栈'选中作为中心点，点击'周边'按钮选择'药店'分类，将范围筛选设为500米，记录每个搜索结果的名称和地址。打开信息app，点击新建消息按钮，收件人输入1997777900，在正文中按'name：address'格式逐行填入药店信息，点击发送。",
        "_source_bench": "MobileWorld",
        "_mw_task_path": "messages/search_pharmacy_task.py",
    },
    {
        "Task_id": 68, "Task Type": "办公协助",
        "Invovled_App_Name": "日历、闹钟",
        "Original-INS": "Set an alarm in Clock app to remind me of my meeting with Sam 5 minutes in advance.",
        "Level1-INS": "Set an alarm 5 minutes before my meeting with Sam.",
        "Level2-INS": "Open the Calendar app to find the meeting with Sam, then open the Clock app and add an alarm 5 minutes before its start time.",
        "Level3-INS": "Open the Calendar app, search for or scroll to the event titled with Sam to read its start time. Open the Clock app, tap the '+' in the Alarm tab, set the time to 5 minutes before that start time, leave repeat off, then tap 'Save' in the top right.",
        "_source_bench": "MobileWorld",
        "_mw_task_path": "calendar/check_event_and_set_alarm.py",
    },
    {
        "Task_id": 69, "Task Type": "办公协助",
        "Invovled_App_Name": "相册、gmail",
        "Original-INS": "Send some photos to Kevin via email, with text \"Here are some pictures for you.\"",
        "Level1-INS": "Email Kevin a few of my photos with a short note.",
        "Level2-INS": "Open the Gallery app to pick some photos, then share them via Gmail to Kevin with the message 'Here are some pictures for you.'",
        "Level3-INS": "Open the Gallery app, browse to All Photos, long-press a photo to enter multi-select and tap a few more photos to add, tap the share icon at the bottom and choose Gmail. In the compose screen, enter Kevin's email address in the To field, type 'Here are some pictures for you.' in the body, then tap the send icon at the top right.",
        "_source_bench": "MobileWorld",
        "_mw_task_path": "native/share_photos_ask_user.py",
    },
    {
        "Task_id": 70, "Task Type": "办公协助",
        "Invovled_App_Name": "gmail、闹钟",
        "Original-INS": "Check my email for the time of the Christmas party today. Set an alarm for one hour before then.",
        "Level1-INS": "Find today's Christmas party time in my email and set an alarm one hour before.",
        "Level2-INS": "Open Gmail to find today's Christmas party email and read its start time, then open the Clock app and add an alarm for one hour before that time.",
        "Level3-INS": "Open the Gmail app, in the inbox locate today's email about the Christmas party and tap it open to read the start time. Open the Clock app, tap the '+' in the Alarm tab, set the time to one hour before the party's start time, leave repeat off, then tap 'Save'.",
        "_source_bench": "MobileWorld",
        "_mw_task_path": "gmail/check_event_time.py",
    },
    {
        "Task_id": 71, "Task Type": "办公协助",
        "Invovled_App_Name": "高德地图(Amap)、gmail",
        "Original-INS": "我打算骑车上班，帮我估算萧山到阿里西溪C园区的距离(公里)和时间（分钟）把结果按`距离(公里),时间(分钟)`的格式发送到我的生活邮箱dylan@gmail.com，标题为`daily bike`",
        "Level1-INS": "帮我估算骑车从萧山到阿里西溪C园区的距离和时间，结果邮件发给我。",
        "Level2-INS": "在高德地图中查询从萧山到阿里西溪C园区的骑行距离和时间，然后用gmail将结果以'距离,时间'格式发送到dylan@gmail.com，标题为'daily bike'。",
        "Level3-INS": "打开高德地图app，点击搜索框输入起点'萧山'和终点'阿里西溪C园区'，在路线模式中选择'骑行'，查看顶部显示的距离和时间数字。打开gmail app，点击右下角的'撰写'按钮，在To栏输入dylan@gmail.com，主题栏输入'daily bike'，正文输入'距离(公里),时间(分钟)'格式的两个数字，点击右上角发送按钮。",
        "_source_bench": "MobileWorld",
        "_mw_task_path": "gmail/estimate_bike_route.py",
    },
    {
        "Task_id": 72, "Task Type": "办公协助",
        "Invovled_App_Name": "Chrome、gmail",
        "Original-INS": "Please check the number of stars and contributors on the AndroidWorld GitHub repository, then send an email to kevin_zhang@example.com with the subject line \"AndroidWorld Repository Stats\" and the following message body: There are XXX stars and XXX contributors in the AndroidWorld repository.",
        "Level1-INS": "Look up AndroidWorld's GitHub stars and contributors and email the numbers to Kevin.",
        "Level2-INS": "Use Chrome to open the AndroidWorld GitHub repository page and read its star count and contributor count, then use Gmail to email those numbers to kevin_zhang@example.com with subject 'AndroidWorld Repository Stats'.",
        "Level3-INS": "Open Google Chrome, tap the address bar and search 'github.com/google-research/android_world', open the first result, note the star count next to the Star button and the contributors count in the side panel. Open Gmail, tap Compose, enter kevin_zhang@example.com in To, type 'AndroidWorld Repository Stats' in Subject, type 'There are XXX stars and XXX contributors in the AndroidWorld repository.' (replacing the numbers) in the body, then tap the send icon.",
        "_source_bench": "MobileWorld",
        "_mw_task_path": "chrome/check_github_info.py",
    },
    {
        "Task_id": 74, "Task Type": "办公协助",
        "Invovled_App_Name": "gmail、日历",
        "Original-INS": "Check my email for the date and time of my meeting with Carl. Then, set a one hour calendar event titled 'Board Meeting'",
        "Level1-INS": "Find when I meet Carl in my email and add a one-hour 'Board Meeting' to my calendar.",
        "Level2-INS": "Open Gmail to find the email with the meeting date and time with Carl, then open the Calendar app and add a one-hour event titled 'Board Meeting' at that time.",
        "Level3-INS": "Open the Gmail app, locate and open the email referencing the meeting with Carl, note the date and start time. Open the Calendar app, tap the '+' to add a new event, type 'Board Meeting' in the title, set start time to that noted time and end time one hour later, then tap 'Save'.",
        "_source_bench": "MobileWorld",
        "_mw_task_path": "gmail/check_set_meet_time.py",
    },
    {
        "Task_id": 75, "Task Type": "办公协助",
        "Invovled_App_Name": "gmail、信息、日历",
        "Original-INS": "I received an email about the Next.js Conf. Please check my calendar. If I'm available, send the sender an SMS saying, 'I can attend the conference.' If not, reply with, 'Sorry, I",
        "Level1-INS": "Check my email about Next.js Conf, then tell the sender by SMS whether I can attend based on my calendar.",
        "Level2-INS": "Open Gmail to find the Next.js Conf email and read its date/time and the sender's phone number, open Calendar to check availability for that slot, then open Messages to text the sender 'I can attend the conference.' if free or a polite decline if not.",
        "Level3-INS": "Open the Gmail app, open the Next.js Conf email, note the conference start/end time and the sender's phone number. Open the Calendar app and navigate to that date to check whether the time slot is free. Open the Messages app, tap to compose a new message, enter the sender's phone number, type 'I can attend the conference.' (or a decline message if a conflict exists), then tap send.",
        "_source_bench": "MobileWorld",
        "_mw_task_path": "gmail/reply_email_via_sms_ask_user.py",
    },

    # ============================================================
    # MVISU-Bench Vague (cn) — Original is already L1, all KB-AOS
    # ============================================================
    {
        "Task_id": 76, "Task Type": "娱乐",
        "Invovled_App_Name": "网易云音乐",
        "Original-INS": "我想听音乐。",
        "Level1-INS": "我想听音乐。",
        "Level2-INS": "打开网易云音乐，挑一首推荐歌曲播放。",
        "Level3-INS": "打开网易云音乐app，点击底部的'每日推荐'或首页的推荐歌单，点击其中一首歌曲的播放按钮(黄底黑色三角形)开始播放。",
        "_source_bench": "MVISU-cn",
    },

    # ----- MVISU-Bench Vague (en) -----

    # ============================================================
    # AndroidDaily 高模糊度 — only KB-AOS apps (携程旅行 / 微信)
    # ============================================================
    {
        "Task_id": 86, "Task Type": "出行",
        "Invovled_App_Name": "携程旅行、微信",
        "Original-INS": "在携程上订一张下周五去三亚的机票,订好后把航班信息通过微信发给我老婆。",
        "Level1-INS": "订一张下周五去三亚的机票，订好后把航班信息发给我老婆。",
        "Level2-INS": "在携程旅行app中预订下周五飞往三亚的机票，然后切到微信将航班信息发送给微信好友'老婆'。",
        "Level3-INS": "打开携程app，点击首页'机票'图标，输入出发城市与目的地'三亚'，日期选下周五，从航班列表中挑选合适的一班点击预订完成支付，截图航班详情；切换到微信app，点击右上角放大镜搜索好友'老婆'，进入聊天页将截图发送过去。",
        "_source_bench": "AndroidDaily",
    },

    # ============================================================
    # AndroidArena — only KB-AOS apps (googleMap / 天气)
    # ============================================================
    {
        "Task_id": 88, "Task Type": "",
        "Invovled_App_Name": "googleMap",
        "Original-INS": "Find the nearest ATM.",
        "Level1-INS": "Find the nearest ATM.",
        "Level2-INS": "Open Google Maps and search for the nearest ATM to my current location.",
        "Level3-INS": "Open the Google Maps app, tap the search bar at the top, type 'ATM' and tap the search icon. Pick the first result on the map (closest by distance) to view its details and directions.",
        "_source_bench": "AndroidArena",
    },

    # ============================================================
    # AndroidWorld — only KB-AOS apps (闹钟 / 备忘录)
    # ============================================================

    # ============================================================
    # MobileWorld — 30 additional entries (Task_id 93-122)
    # All KB-AOS-only; goals lifted from MobileWorld task definitions.
    # ============================================================
    # ---- single-app: 闹钟 / 信息 / Chrome / googleMap / 日历 / gmail ----
    {
        "Task_id": 95, "Task Type": "社交媒体",
        "Invovled_App_Name": "信息",
        "Original-INS": "Send a message to Kevin to information him \"Your interview is scheduled for tomorrow morning at 10:30 AM\".",
        "Level1-INS": "Tell Kevin his interview is tomorrow at 10:30 AM.",
        "Level2-INS": "Open the Messages app and SMS Kevin: 'Your interview is scheduled for tomorrow morning at 10:30 AM'.",
        "Level3-INS": "Open the Messages app, tap the new-message button, search for or enter Kevin in the recipient field, type 'Your interview is scheduled for tomorrow morning at 10:30 AM' in the input box, then tap the send button.",
        "_source_bench": "MobileWorld",
        "_mw_task_path": "messages/send_interview_invitation_ask_user.py",
    },
    {
        "Task_id": 96, "Task Type": "信息搜索",
        "Invovled_App_Name": "Chrome",
        "Original-INS": "Use Chrome to search for Beijing highest temperature today. ONLY give a integer number denoted Celsius degree.",
        "Level1-INS": "What's the highest temperature in Beijing today?",
        "Level2-INS": "Open Chrome and search for Beijing's highest temperature today, then report the integer Celsius value.",
        "Level3-INS": "Open the Chrome app, tap the search bar at the top, type 'Beijing highest temperature today' and tap go, read the weather card or first search result to get the high-temperature value, then report it as an integer.",
        "_source_bench": "MobileWorld",
        "_mw_task_path": "chrome/check_weather.py",
    },
    {
        "Task_id": 97, "Task Type": "",
        "Invovled_App_Name": "googleMap",
        "Original-INS": "Open Google Maps and find which company is directly south of my company. ONLY output the company name in English.",
        "Level1-INS": "Which company sits directly south of mine?",
        "Level2-INS": "Open Google Maps, locate my company, and identify the company directly to its south.",
        "Level3-INS": "Open the Google Maps app, tap the search bar and type my company name, tap the result to center it on the map, then pan and zoom slightly south to read the label of the building/business immediately south, and report that company's name.",
        "_source_bench": "MobileWorld",
        "_mw_task_path": "map/check_neighbours_ask_user.py",
    },
    {
        "Task_id": 98, "Task Type": "",
        "Invovled_App_Name": "googleMap",
        "Original-INS": "Open Google Maps and find which company is directly south of Alibaba Hangzhou headquarters in Binjiang District. ONLY output the company name in English.",
        "Level1-INS": "Which company sits directly south of Alibaba Hangzhou HQ in Binjiang?",
        "Level2-INS": "Open Google Maps, find Alibaba's Hangzhou headquarters in Binjiang District, and identify the company directly to its south.",
        "Level3-INS": "Open the Google Maps app, tap the search bar and type 'Alibaba Hangzhou headquarters Binjiang', tap the result to focus on it, then pan slightly south to see the building/business immediately south and read its label.",
        "_source_bench": "MobileWorld",
        "_mw_task_path": "map/check_neighbours.py",
    },
    {
        "Task_id": 99, "Task Type": "",
        "Invovled_App_Name": "googleMap",
        "Original-INS": "What is the driving distance in kilometers from Beijing to my hometown? Response as the following format: beijing to xxx: distance km. xxx denotes the name of the hometown.",
        "Level1-INS": "How far is it to drive from Beijing to my hometown?",
        "Level2-INS": "Open Google Maps and check the driving distance in kilometers from Beijing to my hometown.",
        "Level3-INS": "Open the Google Maps app, tap the directions icon, set the start to 'Beijing' and the destination to my hometown, choose the driving mode, then read the displayed distance in kilometers and report it as 'beijing to <hometown>: <distance> km'.",
        "_source_bench": "MobileWorld",
        "_mw_task_path": "map/check_distance_ask_user_1.py",
    },
    {
        "Task_id": 100, "Task Type": "系统软件",
        "Invovled_App_Name": "日历",
        "Original-INS": "How many days of conference meetings did I schedule in October? Please only return the number of days, no other text.",
        "Level1-INS": "How many conference days did I schedule in October?",
        "Level2-INS": "Open the Calendar app and count the days in October that contain conference meetings.",
        "Level3-INS": "Open the Calendar app, switch to Month view via the view-switcher and navigate to October, scan each day for events whose titles mention 'conference', count the distinct days that contain such events, and report that integer.",
        "_source_bench": "MobileWorld",
        "_mw_task_path": "calendar/check_conference_duration.py",
    },
    {
        "Task_id": 101, "Task Type": "办公协助",
        "Invovled_App_Name": "gmail",
        "Original-INS": "Look for a file in my email titled 'receipts.jpg' and download it. Then, send it to to treasurer@gmail.com with the subject 'Proof of purchase', the email should mention the total amount spent in the email.",
        "Level1-INS": "Forward the receipts.jpg attachment to the treasurer with the total amount.",
        "Level2-INS": "Open Gmail, locate the email containing receipts.jpg, download it, then compose a new email to treasurer@gmail.com with subject 'Proof of purchase' that attaches the file and notes the total amount spent.",
        "Level3-INS": "Open the Gmail app, tap the search icon and search 'receipts.jpg', open the matching email and tap the attachment 'receipts.jpg' then download it. Tap the Compose button, enter treasurer@gmail.com in To, type 'Proof of purchase' in the Subject field, write the total amount spent in the body, tap the paperclip icon to attach the downloaded receipts.jpg, then tap the send icon.",
        "_source_bench": "MobileWorld",
        "_mw_task_path": "gmail/download_send_receipt.py",
    },
    {
        "Task_id": 102, "Task Type": "办公协助",
        "Invovled_App_Name": "gmail",
        "Original-INS": "Please check my email for any field trip forms sent from October 3rd onward. Download all of them and send them to principal@school.edu with the subject 'Field Trip Forms'. Then, tell me how many forms you found as a single number.",
        "Level1-INS": "Collect any field trip forms from my email since Oct 3 and forward them to the principal; tell me how many.",
        "Level2-INS": "Open Gmail to find all field-trip-form emails dated Oct 3 or later, download every attachment, then compose one email to principal@school.edu with subject 'Field Trip Forms' attaching all the forms, and report the count.",
        "Level3-INS": "Open the Gmail app, tap the search icon and search 'field trip form after:2025/10/03', open each matching email and tap each attachment to download it, count the total. Tap Compose, enter principal@school.edu in To, type 'Field Trip Forms' in Subject, attach all downloaded forms via the paperclip icon, type the count in the body, then send. Report the count number.",
        "_source_bench": "MobileWorld",
        "_mw_task_path": "gmail/send_forms.py",
    },

    # ---- two-app: 信息+高德地图 (Amap-MCP commute / route planning) ----
    {
        "Task_id": 103, "Task Type": "生活",
        "Invovled_App_Name": "高德地图(Amap)、信息",
        "Original-INS": "我从高德复制了一段终点坐标 120.0351,30.2809（阿里西溪附近），帮我用它查出详细的行政区划地址，然后短信给1766242644，按照\"坐标：地址\"的格式编写短信内容",
        "Level1-INS": "把这个坐标的详细地址查一下短信发给我。",
        "Level2-INS": "在高德地图中用坐标120.0351,30.2809查出详细的行政区划地址，再用信息app把'坐标：地址'格式的内容发给1766242644。",
        "Level3-INS": "打开高德地图app，点击中间搜索框，粘贴坐标'120.0351,30.2809'选中目标点，在结果详情页读取完整行政区划地址。打开信息app，点击新建消息按钮，收件人输入1766242644，正文按'坐标：地址'格式键入'120.0351,30.2809：<上一步读到的地址>'，点击发送。",
        "_source_bench": "MobileWorld",
        "_mw_task_path": "messages/send_location_address_sms.py",
    },
    {
        "Task_id": 104, "Task Type": "出行",
        "Invovled_App_Name": "高德地图(Amap)、信息",
        "Original-INS": "成都打车路线：从成都双流国际机场T2航站楼到锦江区春熙路南段8号酒店，途经宽窄巷子和锦里古街，把路线信息按规定格式短信发给Lucy 13900139000。",
        "Level1-INS": "帮我设计成都打车路线，途经宽窄巷子和锦里古街，把详细信息发给Lucy。",
        "Level2-INS": "在高德地图中规划从成都双流T2到春熙路南段8号酒店的打车路线，途经宽窄巷子和锦里古街，按最短距离排序，然后用信息app将4个地点名称坐标、浏览顺序、三段距离和总距离发送给Lucy 13900139000。",
        "Level3-INS": "打开高德地图app，在搜索框依次输入起点'成都双流国际机场T2航站楼'、途经点'宽窄巷子''锦里古街'和终点'成都市锦江区春熙路南段8号'，切到打车模式分别记录两种顺序的总距离选最短一组，记下各点的经纬度坐标和分段距离。打开信息app，新建消息，收件人填13900139000，按要求格式逐行键入4个地点的'名称：经度,纬度'、浏览顺序、三段驾车距离(米)和总距离(米)，点击发送。",
        "_source_bench": "MobileWorld",
        "_mw_task_path": "messages/plan_taxi_route_sms.py",
    },

    # ---- two-app: 信息+日历 (sms <-> calendar workflows) ----
    {
        "Task_id": 108, "Task Type": "社交媒体",
        "Invovled_App_Name": "信息、日历",
        "Original-INS": "I've received a lunch invitation via text message; please reply \"OK\" and schedule a lunch event ranging from 11 a.m. to 12 a.m. on Oct 17.",
        "Level1-INS": "Accept the SMS lunch invite and put it on my calendar (Oct 17, 11am–noon).",
        "Level2-INS": "Open Messages, reply 'OK' to the lunch invitation, then open Calendar and add a Lunch event on Oct 17 from 11 AM to 12 PM.",
        "Level3-INS": "Open the Messages app, locate the lunch invitation thread, type 'OK' in the input box and tap send. Open the Calendar app, tap the '+' to add a new event, type 'Lunch' as the title, set the date to October 17 with start time 11:00 AM and end time 12:00 PM, then tap 'Save'.",
        "_source_bench": "MobileWorld",
        "_mw_task_path": "calendar/schedule_lunch_via_sms_ask_user.py",
    },
    {
        "Task_id": 109, "Task Type": "社交媒体",
        "Invovled_App_Name": "信息、日历",
        "Original-INS": "I've received a coffee time invitation via text message; please check the calendar. If I am available in this time slot, reply \"OK\" and schedule a corresponding event on my calendar. Otherwise reply \"Not available in this time slot.\"",
        "Level1-INS": "Check my calendar for the SMS coffee invite and reply with the right answer.",
        "Level2-INS": "Open Messages to read the coffee time invitation, open Calendar to check whether that time slot is free, then reply 'OK' and add the event if free, otherwise reply 'Not available in this time slot.'",
        "Level3-INS": "Open the Messages app, open the coffee invitation thread and note the proposed time. Open the Calendar app and navigate to that date/time to see if it's free. If free: return to Messages, type 'OK' and send, then in Calendar tap '+' to add a 'Coffee' event at that time and tap Save. If conflict: return to Messages, type 'Not available in this time slot.' and send.",
        "_source_bench": "MobileWorld",
        "_mw_task_path": "calendar/schedule_coffee_time_via_sms.py",
    },
    {
        "Task_id": 110, "Task Type": "社交媒体",
        "Invovled_App_Name": "信息、日历",
        "Original-INS": "I've received a one-on-one meeting invitation from my boss. Please check my calendar and reply 'OK' if it's clear. If there's a scheduling conflict, please notify the person in the conflict event by SMS: 'Sorry, I can't attend the meeting.'",
        "Level1-INS": "Check my calendar for the 1:1 invite from my boss and handle the reply.",
        "Level2-INS": "Open Messages to read the 1-on-1 invitation from my boss, open Calendar to check that time slot, then reply 'OK' to the boss if free, or otherwise SMS the conflicting event's person 'Sorry, I can't attend the meeting.'",
        "Level3-INS": "Open the Messages app, read the boss's 1-on-1 invitation and note its proposed time. Open the Calendar app and navigate to that time slot. If empty: return to Messages and reply 'OK' to the boss. If a conflicting event exists, open that event to find its other participant's contact, then open Messages, compose a new SMS to that person, type 'Sorry, I can't attend the meeting.' and send.",
        "_source_bench": "MobileWorld",
        "_mw_task_path": "calendar/schedule_oneone_via_sms_ask_user.py",
    },
    {
        "Task_id": 111, "Task Type": "办公协助",
        "Invovled_App_Name": "信息、日历",
        "Original-INS": "Check my calendar and send an SMS notification to Mia with the dates of my arrival and departure from Paris. The message should contain only the two dates in MM/DD/YYYY format, separated by a comma.",
        "Level1-INS": "Text Mia my Paris arrival and departure dates.",
        "Level2-INS": "Open Calendar to read the Paris trip arrival and departure dates, then open Messages and SMS Mia those two dates in MM/DD/YYYY format separated by a comma.",
        "Level3-INS": "Open the Calendar app, search for or browse to the Paris-related events to read the arrival and departure dates. Open the Messages app, tap to compose a new message, select Mia as the recipient, type the two dates as 'MM/DD/YYYY,MM/DD/YYYY' (and nothing else) in the body, then tap send.",
        "_source_bench": "MobileWorld",
        "_mw_task_path": "calendar/check_conference_and_send_sms_1.py",
    },
    {
        "Task_id": 112, "Task Type": "办公协助",
        "Invovled_App_Name": "信息、日历",
        "Original-INS": "Check my calendar and send an SMS notification to Mia with the dates of my arrival and departure from Tokyo. The message should contain only the two dates in MM/DD/YYYY format, separated by a comma.",
        "Level1-INS": "Text Mia my Tokyo arrival and departure dates.",
        "Level2-INS": "Open Calendar to read the Tokyo trip arrival and departure dates, then open Messages and SMS Mia those two dates in MM/DD/YYYY format separated by a comma.",
        "Level3-INS": "Open the Calendar app, search for or browse to the Tokyo-related events to read the arrival and departure dates. Open the Messages app, tap to compose a new message, select Mia as the recipient, type the two dates as 'MM/DD/YYYY,MM/DD/YYYY' (and nothing else) in the body, then tap send.",
        "_source_bench": "MobileWorld",
        "_mw_task_path": "calendar/check_conference_and_send_sms_2.py",
    },

    # ---- two-app: 日历+其它 / 相册+其它 / gmail+其它 ----
    {
        "Task_id": 113, "Task Type": "出行",
        "Invovled_App_Name": "日历、高德地图(Amap)",
        "Original-INS": "我下周六10:00am-12:30pm要去「上海虹桥火车站」，添加事项到calender，事项为出差，你帮我找到离上海虹桥火车站10公里以内的景点，我周一上班前去参观下，按照\"景点名字：地址\"放入calender事件的描述中，多个景点按逗号分隔",
        "Level1-INS": "下周六我去上海虹桥火车站出差，顺便帮我找几个附近景点放进日程里。",
        "Level2-INS": "在日历中新建下周六10:00-12:30的出差事项'上海虹桥火车站'，在高德地图中查上海虹桥火车站10公里内的景点，把'景点名字：地址'用逗号拼接后填到该日历事件的描述里。",
        "Level3-INS": "打开高德地图app，搜索'上海虹桥火车站'，点击'周边'选'景点'并把范围设为10公里，记下若干景点的名称和地址。打开日历app，点击'+'新建事件，标题填'出差'、日期选下周六、时间10:00 AM到12:30 PM、地点'上海虹桥火车站'，在描述栏键入'景点1：地址1，景点2：地址2，...'，点击保存。",
        "_source_bench": "MobileWorld",
        "_mw_task_path": "calendar/add_business_trip_with_cafe.py",
    },
    {
        "Task_id": 114, "Task Type": "",
        "Invovled_App_Name": "日历、相册",
        "Original-INS": "Find all my food pics from the past month and help me classify them into different folders named travel locations. You can find where I visited from calendar.",
        "Level1-INS": "Sort last month's food photos into folders by travel city.",
        "Level2-INS": "Open Calendar to identify the cities I traveled to last month, then open Gallery, locate all food pictures from that month and move them into folders named after each city.",
        "Level3-INS": "Open the Calendar app and scan the past month's events for travel destinations, listing the cities you visited and their date ranges. Open the Gallery app, switch to Albums and create one folder per city. Browse the All Photos view, identify food pictures (use date to map to the corresponding city), long-press each food photo and move it into the matching city folder.",
        "_source_bench": "MobileWorld",
        "_mw_task_path": "work/photo_management.py",
    },
    {
        "Task_id": 116, "Task Type": "办公协助",
        "Invovled_App_Name": "gmail、信息",
        "Original-INS": "Check if I've received an email about the depart time for the CoolHacks hackathon. If not, text Carl (345 6784 3456) 'Do you know what time we're leaving tomorrow?'",
        "Level1-INS": "Find the hackathon depart time in my email, or text Carl if I haven't got one.",
        "Level2-INS": "Open Gmail to search for an email about the CoolHacks hackathon depart time; if none is found, open Messages and SMS Carl (3456784346) 'Do you know what time we're leaving tomorrow?'",
        "Level3-INS": "Open the Gmail app, tap the search icon and type 'CoolHacks depart time' to look for the relevant email. If a matching email exists, open it to read the depart time. Otherwise open the Messages app, compose a new SMS to 3456784346 (Carl), type 'Do you know what time we're leaving tomorrow?' in the body and tap send.",
        "_source_bench": "MobileWorld",
        "_mw_task_path": "gmail/check_depart_time.py",
    },
    {
        "Task_id": 117, "Task Type": "办公协助",
        "Invovled_App_Name": "gmail、信息",
        "Original-INS": "Check my email for the time of the math competition tomorrow. If it's between 12 and 5 pm, text Daniel (3522228876) 'Hey, could you help send Bob to the competition tomorrow? Thanks.'",
        "Level1-INS": "Look up tomorrow's math competition time in my email and text Daniel if it lands between noon and 5pm.",
        "Level2-INS": "Open Gmail to find the email with tomorrow's math competition time; if the time is between 12:00 and 17:00, open Messages and SMS Daniel (3522228876) 'Hey, could you help send Bob to the competition tomorrow? Thanks.'",
        "Level3-INS": "Open the Gmail app, search 'math competition' to find the relevant email and read the start time. If the time is between 12:00 PM and 5:00 PM, open the Messages app, compose a new SMS to 3522228876 (Daniel), type 'Hey, could you help send Bob to the competition tomorrow? Thanks.' and tap send. Otherwise do nothing.",
        "_source_bench": "MobileWorld",
        "_mw_task_path": "gmail/request_carpooling.py",
    },
    {
        "Task_id": 118, "Task Type": "办公协助",
        "Invovled_App_Name": "信息、gmail",
        "Original-INS": "Check all unread sms messages, delete spams, and provide a summary of recruitment messages to me via email by sending to dylan@gmail.com. Note I'm only interested in open data scientist role.",
        "Level1-INS": "Clean up my unread SMS and email me a recap of any data-scientist recruitment messages.",
        "Level2-INS": "Open Messages to read every unread SMS, delete spam threads, summarize the recruitment messages relevant to open data scientist roles, then open Gmail and email that summary to dylan@gmail.com.",
        "Level3-INS": "Open the Messages app and review each unread thread; long-press spam threads and tap the trash icon to delete them; for recruitment messages, note the role and key details. Filter to those mentioning open data scientist positions and compose a summary. Open Gmail, tap Compose, enter dylan@gmail.com in To, type a subject like 'SMS recruitment summary', paste the summary in the body and tap send.",
        "_source_bench": "MobileWorld",
        "_mw_task_path": "native/sms_management.py",
    },
    {
        "Task_id": 119, "Task Type": "出行",
        "Invovled_App_Name": "googleMap、信息",
        "Original-INS": "Search up how long it takes to drive from Orlando to Miami. Text Susan (4538997638) the approximate time I'll be there if I leave at 5 pm.",
        "Level1-INS": "Tell Susan when I'll get to Miami if I drive from Orlando at 5pm.",
        "Level2-INS": "Open Google Maps to check the driving duration from Orlando to Miami, then open Messages and SMS Susan (4538997638) with the approximate arrival time given a 5 PM departure.",
        "Level3-INS": "Open the Google Maps app, tap the directions icon, set Orlando as the start and Miami as the destination with driving mode, read the trip duration. Add that duration to 5:00 PM to get the arrival time. Open the Messages app, compose a new SMS to 4538997638 (Susan), type something like 'I should arrive around <HH:MM>.' and tap send.",
        "_source_bench": "MobileWorld",
        "_mw_task_path": "map/text_arrival_time.py",
    },
    {
        "Task_id": 120, "Task Type": "办公协助",
        "Invovled_App_Name": "googleMap、信息",
        "Original-INS": "Check my email for the location of the MCFT conference hotel, then text the address to Tom (4456547865). Use Google maps to tell me how long it would take to walk from the MIT Stata center to there. Only response the time in minutes. No other text.",
        "Level1-INS": "Get the MCFT conference hotel from my email, text it to Tom, and tell me how long it is to walk from MIT Stata.",
        "Level2-INS": "Open Gmail to find the MCFT conference hotel address, open Messages and SMS Tom (4456547865) with that address, then open Google Maps and check the walking duration from the MIT Stata Center to that hotel, reporting just the minutes.",
        "Level3-INS": "Open the Gmail app, search 'MCFT conference' to find the email and read the hotel address. Open the Messages app, compose a new SMS to 4456547865 (Tom), paste the address and send. Open the Google Maps app, tap directions, set the start to 'MIT Stata Center' and destination to that hotel, choose walking mode, read the duration in minutes and report it as a plain integer.",
        "_source_bench": "MobileWorld",
        "_mw_task_path": "gmail/check_conference_location.py",
    },
    {
        "Task_id": 121, "Task Type": "出行",
        "Invovled_App_Name": "高德地图(Amap)、gmail",
        "Original-INS": "帮我规划从杭州亲橙酒店到萧山机场之间规划一条驾车路线，把返回的路线信息组织成一段内容，instructions用逗号分隔，发送到我的生活邮箱dylan@gmail.com，标题为`daily travel`",
        "Level1-INS": "帮我查一下从杭州亲橙酒店到萧山机场怎么开车，邮件给我。",
        "Level2-INS": "在高德地图中查询从杭州亲橙酒店到萧山机场的驾车路线，把每一步的instruction用逗号拼接，然后通过gmail发送到dylan@gmail.com，标题为'daily travel'。",
        "Level3-INS": "打开高德地图app，点击路线规划，起点输入'杭州亲橙酒店'终点'萧山机场'选驾车模式，展开'路线详情'记下所有driving instructions并用逗号拼接成一段。打开gmail app，点击撰写按钮，To栏填dylan@gmail.com，主题栏填'daily travel'，正文粘贴上一步的instructions段落，点击发送。",
        "_source_bench": "MobileWorld",
        "_mw_task_path": "gmail/plan_route_task.py",
    },
    {
        "Task_id": 122, "Task Type": "出行",
        "Invovled_App_Name": "高德地图(Amap)、gmail",
        "Original-INS": "我想每天晚饭后从阿里巴巴西溪园区散步到西溪湿地。我家在「浙江省杭州市余杭区文一西路阿里巴巴西溪园区C区三号楼」，公园在「西溪国家湿地公园周家村主入口」，评估把总距离（公里）和预计时长(分钟)email到我的生活邮箱dylan@gmail.com，标题为daily walking",
        "Level1-INS": "估算一下我家到西溪湿地散步的距离和时间，邮件给我。",
        "Level2-INS": "在高德地图中估算从'阿里西溪园区C区三号楼'到'西溪国家湿地公园周家村主入口'的步行距离(公里)和时长(分钟)，然后通过gmail发送到dylan@gmail.com，标题为'daily walking'。",
        "Level3-INS": "打开高德地图app，路线规划起点输入'浙江省杭州市余杭区文一西路阿里巴巴西溪园区C区三号楼'，终点输入'西溪国家湿地公园周家村主入口'，切换步行模式，记下显示的距离(公里)与时长(分钟)。打开gmail app，撰写新邮件，To栏填dylan@gmail.com，主题栏填'daily walking'，正文写入'距离x.xx公里，时长xx分钟'，点击发送。",
        "_source_bench": "MobileWorld",
        "_mw_task_path": "work/calculate_walking_route_email.py",
    },

    # ============================================================
    # MobileWorld — Taodian (mall/) entries (Task_id 123-130)
    # MW's `Taodian` app maps to KB's `淘宝` (id=112, 12 AOS funcs).
    # L3 chains adapted from 淘宝's action_object_str:
    #   商品搜索 / 下单购买 / 加入购物车 / 订单物流查询 / 新增地址 / 售后服务
    # ============================================================
    {
        "Task_id": 123, "Task Type": "生活",
        "Invovled_App_Name": "淘宝",
        "Original-INS": "帮我在淘店下单购物车里的iphone 15 pro，寄到浙江省杭州市余杭区阿里巴巴西溪C区，收件人张先生，收件人电话13800138000。如需登录，可以通过短信验证码。在支付页面让我操作",
        "Level1-INS": "帮我下单购物车里的iPhone 15 Pro，寄到公司收件人张先生。",
        "Level2-INS": "在淘宝app的购物车中勾选iPhone 15 Pro下单，收货地址填'浙江省杭州市余杭区阿里巴巴西溪C区 张先生 13800138000'，在支付页让我操作。",
        "Level3-INS": "打开淘宝app，若提示登录则切换'短信验证码登录'输入手机号收码登录。点击右下角笑脸图标进入'我的淘宝'，进入购物车页，勾选iPhone 15 Pro，点击'结算'。若收件人地址中没有目标地址，点击'新增地址'输入'浙江省杭州市余杭区阿里巴巴西溪C区 张先生 13800138000'并保存。回到结算页选中该地址，点击'提交订单'进入支付页等待用户操作。",
        "_source_bench": "MobileWorld",
        "_mw_task_path": "mall/item_checkout.py",
    },
    {
        "Task_id": 124, "Task Type": "生活",
        "Invovled_App_Name": "淘宝",
        "Original-INS": "最近天气变冷了，请帮我从淘店app的购物车中删除所有短袖T恤衬衫。如果需要登录，可以通过短信验证码登录。",
        "Level1-INS": "天冷了，把我购物车里的短袖T恤都删掉。",
        "Level2-INS": "在淘宝app的购物车中找出所有短袖T恤衬衫并删除；若需登录用短信验证码。",
        "Level3-INS": "打开淘宝app，若弹出登录则切换'短信验证码登录'输入手机号收码登录。点击右下角笑脸图标进入'我的淘宝'，进入'购物车'页，浏览每件商品的标题，找到含'短袖T恤/衬衫/T-shirt'字样的商品，左滑或长按后点击'删除'确认；逐件重复直至全部删除。",
        "_source_bench": "MobileWorld",
        "_mw_task_path": "mall/cart_management.py",
    },
    {
        "Task_id": 125, "Task Type": "生活",
        "Invovled_App_Name": "淘宝",
        "Original-INS": "Find the three most expensive items in the TaoDian app shopping cart and calculate their total price. Respond only with an integer representing the total price, with no other text.",
        "Level1-INS": "What's the total price of the three priciest items in my cart?",
        "Level2-INS": "Open Taobao's cart, identify the three most expensive items, sum their prices, and report only the integer total.",
        "Level3-INS": "Open the Taobao app, tap the smiley-face icon labelled '我的淘宝' at the bottom right, enter the '购物车' (cart) page, scroll through every item and note its price, pick the three highest, add them up, and report the integer total with no other text.",
        "_source_bench": "MobileWorld",
        "_mw_task_path": "mall/check_cart_price_1.py",
    },
    {
        "Task_id": 126, "Task Type": "生活",
        "Invovled_App_Name": "淘宝",
        "Original-INS": "请帮我算一下在淘店上最近1个月我总共花了多少钱。请只回答一个整数, 不要返回任何其他文本.",
        "Level1-INS": "我最近一个月在淘宝花了多少钱？",
        "Level2-INS": "在淘宝app里查看最近1个月的订单总金额，只回答整数。",
        "Level3-INS": "打开淘宝app，点击右下角笑脸图标进入'我的淘宝'，点击'我的订单'(或'查看全部订单')，将筛选时间范围设为最近1个月，向下滚动遍历订单列表，把每单实付金额累加起来，最终只回复整数总额。",
        "_source_bench": "MobileWorld",
        "_mw_task_path": "mall/recent_total_expense.py",
    },
    {
        "Task_id": 127, "Task Type": "生活",
        "Invovled_App_Name": "淘宝",
        "Original-INS": "帮我在淘店上找一双白色的鞋，日常通勤穿的，按我平时穿的码下单，默认收件人和地址",
        "Level1-INS": "帮我买一双日常通勤的白色鞋，按我平时穿的码。",
        "Level2-INS": "在淘宝app搜索白色通勤鞋，挑一双合适的按我常用尺码下单，地址用默认。",
        "Level3-INS": "打开淘宝app，点击顶部搜索栏输入'白色 通勤 鞋'，点击右侧红色'搜索'按钮，从结果列表里点开一款评价好的商品进入详情页，在尺码选项中选择我常穿的码数，点击底部红色'立即购买'，结算页保留默认收件人地址，点击'提交订单'进入支付页。",
        "_source_bench": "MobileWorld",
        "_mw_task_path": "mall/search_white_sneakers_checkout_ask_user.py",
    },
    {
        "Task_id": 128, "Task Type": "生活",
        "Invovled_App_Name": "淘宝、信息",
        "Original-INS": "Find the items awaiting shipment in TaoDian and send an SMS reminder to the recipient, including the product name and order number, with no other text.",
        "Level1-INS": "Text the recipient the product name and order number for my pending-shipment items.",
        "Level2-INS": "Open the Taobao app, list items awaiting shipment in My Orders, then open the Messages app and SMS each recipient the product name and order number (text only).",
        "Level3-INS": "Open the Taobao app, tap '我的淘宝' at the bottom right, tap the truck icon labelled '待发货' to view items awaiting shipment. For each item, read its product name, order number, and the recipient's phone in the order detail. Open the Messages app, compose a new SMS to that phone, type only '<product name> <order number>' in the body, and send.",
        "_source_bench": "MobileWorld",
        "_mw_task_path": "mall/cart_info_notification.py",
    },
    {
        "Task_id": 129, "Task Type": "生活",
        "Invovled_App_Name": "淘宝",
        "Original-INS": "之前我给朋友在淘店上买了一双鞋，帮我看一下他脚多少尺码。请只回答一个整数, 不要返回任何其他文本.",
        "Level1-INS": "我之前给朋友买了一双鞋，他脚多少码？",
        "Level2-INS": "在淘宝app的历史订单里找之前给朋友买的鞋，查看下单时选的尺码，只回答整数。",
        "Level3-INS": "打开淘宝app，点击右下角笑脸图标进入'我的淘宝'，点击'我的订单'，向下滚动找到那笔给朋友买鞋的订单，点击订单进入详情页，查看商品规格栏中的尺码数字，只回复该整数。",
        "_source_bench": "MobileWorld",
        "_mw_task_path": "mall/check_purchased_item.py",
    },
    {
        "Task_id": 130, "Task Type": "生活",
        "Invovled_App_Name": "淘宝",
        "Original-INS": "Help me calculate the prices of items in the Taodian shopping cart separately for me and my roommate, tell me how much each person needs to pay. Answer in the format 'me/roommate:amount,amount'.",
        "Level1-INS": "Split my cart between me and my roommate and tell me what each of us owes.",
        "Level2-INS": "Open Taobao's cart, group items by owner (me vs roommate) using their memos, sum each bucket, and report 'me/roommate:amount,amount'.",
        "Level3-INS": "Open the Taobao app, tap '我的淘宝' at the bottom right, enter the '购物车' page. For each item, expand the entry to read its memo/owner tag to determine if it's mine or my roommate's. Sum the prices in each bucket, then report the result in the exact format 'me/roommate:<my_total>,<roommate_total>'.",
        "_source_bench": "MobileWorld",
        "_mw_task_path": "mall/calculate_cart_prices_by_owner_ask_user.py",
    },
]


MW_TASK_ROOT = os.path.join(
    REPO, "MobileWorld", "MobileWorld", "src", "mobile_world", "tasks", "definitions"
)


def _resolve_mw_class(rel_path: str) -> str:
    """Read a MobileWorld task .py file and return its first BaseTask subclass name."""
    import re
    fp = os.path.join(MW_TASK_ROOT, rel_path)
    with open(fp, "r", encoding="utf-8") as f:
        src = f.read()
    m = re.search(r"class\s+(\w+)\s*\([^)]*BaseTask[^)]*\)", src)
    if not m:
        raise RuntimeError(f"no BaseTask subclass in {rel_path}")
    return m.group(1)


def _enrich_mw_entries(entries: list[dict]) -> None:
    """Populate `_mw_task_class` for every MobileWorld entry by parsing the file."""
    for t in entries:
        if t.get("_source_bench") != "MobileWorld":
            continue
        if "_mw_task_path" not in t:
            raise RuntimeError(f"MobileWorld entry {t['Task_id']} missing _mw_task_path")
        t["_mw_task_class"] = _resolve_mw_class(t["_mw_task_path"])


def main() -> None:
    with open(ORIG, "r", encoding="utf-8") as f:
        existing = json.load(f)
    existing_ids = {t["Task_id"] for t in existing}
    new_ids = {t["Task_id"] for t in NEW_TASKS}
    overlap = existing_ids & new_ids
    if overlap:
        raise SystemExit(f"Task_id collision with existing entries: {sorted(overlap)}")

    # Resolve class names from task files (idempotent).
    _enrich_mw_entries(NEW_TASKS)

    # Verify every new entry uses ONLY apps with action_object_str (sanity).
    kb_path = os.path.join(REPO, "app-data", "knowledge-base", "AppUi-final.json")
    with open(kb_path, "r", encoding="utf-8") as f:
        kb = json.load(f)
    with_aos = {a["app_name"].strip() for a in kb if a.get("action_object_str")}
    # Surface aliases the schema field might use.
    aliases_to_canonical = {
        "微信": "微信", "美图": "美图秀秀", "网易云": "网易云音乐",
        "高德地图": "高德地图(Amap)", "笔记": "备忘录/笔记", "备忘录": "备忘录/笔记",
        "Gmail": "gmail",
    }

    def split_apps(raw: str) -> list[str]:
        # Split only on CN/EN comma-like separators — preserve internal spaces
        # so multi-word app names like "Amazon Shopping" stay intact.
        import re
        return [a.strip() for a in re.split(r"[、，,/]+", raw or "") if a.strip()]

    warnings: list[tuple[int, str, str]] = []
    for t in NEW_TASKS:
        for raw in split_apps(t["Invovled_App_Name"]):
            canon = aliases_to_canonical.get(raw, raw)
            if canon not in with_aos:
                warnings.append((t["Task_id"], raw, canon))
    if warnings:
        print("⚠ apps WITHOUT action_object_str detected:")
        for tid, raw, canon in warnings:
            print(f"  Task_id={tid}  raw={raw!r}  canon={canon!r}")
    else:
        print("✓ all new entries use only KB-AOS apps")

    merged = existing + NEW_TASKS

    # Reindex Task_id sequentially 1..N (original 50 first, then new entries),
    # removing the historical gaps. Stable keys for MobileWorld entries are
    # _mw_task_class / _mw_task_path (NOT Task_id), so the eval runner is
    # unaffected. Keep the pre-reindex id under `_orig_task_id` for traceback.
    for new_id, t in enumerate(merged, start=1):
        if t.get("Task_id") != new_id:
            t["_orig_task_id"] = t.get("Task_id")
        t["Task_id"] = new_id

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)

    print(f"\nexisting: {len(existing)}")
    print(f"new:      {len(NEW_TASKS)}")
    print(f"merged:   {len(merged)}  -> {OUT}")

    by_src: dict[str, int] = {}
    by_lang: dict[str, int] = {}
    for t in NEW_TASKS:
        by_src[t["_source_bench"]] = by_src.get(t["_source_bench"], 0) + 1
        import re
        lang = "cn" if re.search(r"[一-鿿]", t["Level1-INS"]) else "en"
        by_lang[lang] = by_lang.get(lang, 0) + 1
    print("\nnew-entry breakdown by source bench:")
    for k, v in sorted(by_src.items(), key=lambda x: -x[1]):
        share = v * 100 / len(NEW_TASKS)
        print(f"  {k:14s} {v:3d}  ({share:.0f}%)")
    print("\nnew-entry breakdown by language:")
    for k, v in sorted(by_lang.items()):
        print(f"  {k:4s} {v}")


if __name__ == "__main__":
    main()
