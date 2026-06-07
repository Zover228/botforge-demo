# -*- coding: utf-8 -*-
"""
BOTFORGE DEMO BOT — Webhook режим для Render.com
=================================================
Переменные окружения (ставить в Render → Environment):
  BOT_TOKEN   = токен от BotFather
  ADMIN_ID    = твой Telegram ID (число)
  RENDER_URL  = https://ИМЯ_ПРИЛОЖЕНИЯ.onrender.com
"""

import asyncio, logging, os, sqlite3, time
from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

# ── Настройки из переменных окружения ──────────────────────────
BOT_TOKEN   = os.environ["BOT_TOKEN"]
ADMIN_ID    = int(os.environ.get("ADMIN_ID", "0"))
RENDER_URL  = os.environ.get("RENDER_URL", "").rstrip("/")
PORT        = int(os.environ.get("PORT", "8080"))
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL  = f"{RENDER_URL}{WEBHOOK_PATH}"

SITE_URL    = "https://strong-sawine-5c2e92.netlify.app"
CONTACT_TG  = "botforgeadmin"

logging.basicConfig(level=logging.INFO)
dp = Dispatcher()

# ── База данных ─────────────────────────────────────────────────
db = sqlite3.connect("demo.db", check_same_thread=False)
db.execute("""CREATE TABLE IF NOT EXISTS users(
    uid INTEGER PRIMARY KEY, username TEXT, name TEXT,
    joined_at REAL, last_seen REAL, actions INTEGER DEFAULT 0
)""")
db.commit()

def track(uid, uname="", fname="", action=False):
    now = time.time()
    if db.execute("SELECT 1 FROM users WHERE uid=?",(uid,)).fetchone():
        db.execute("UPDATE users SET last_seen=?,actions=actions+? WHERE uid=?",
                   (now, 1 if action else 0, uid))
    else:
        db.execute("INSERT INTO users VALUES(?,?,?,?,?,0)",(uid,uname,fname,now,now))
    db.commit()

# ── Клавиатуры ──────────────────────────────────────────────────
def kb_main():
    b = InlineKeyboardBuilder()
    b.button(text="🤖 Что умеют наши боты?",        callback_data="capabilities")
    b.button(text="📅 ДЕМО: Запись клиентов",        callback_data="demo_booking")
    b.button(text="🛍 ДЕМО: Каталог и магазин",      callback_data="demo_catalog")
    b.button(text="❓ ДЕМО: Поддержка / FAQ",        callback_data="demo_faq")
    b.button(text="📣 ДЕМО: Автоворонка продаж",     callback_data="demo_funnel")
    b.button(text="📊 Посчитать ROI для бизнеса",   callback_data="roi_start")
    b.button(text="💰 Цены и тарифы",               callback_data="pricing")
    b.button(text="🎯 Пройти аудит на сайте →",     url=f"{SITE_URL}/#audit")
    b.button(text="💬 Написать нам",                url=f"https://t.me/{CONTACT_TG}")
    b.adjust(1); return b.as_markup()

def kb_back():
    b = InlineKeyboardBuilder()
    b.button(text="‹ В меню",              callback_data="menu")
    b.button(text="💬 Заказать такой бот", url=f"https://t.me/{CONTACT_TG}")
    b.adjust(1); return b.as_markup()

def kb_order():
    b = InlineKeyboardBuilder()
    b.button(text="✅ Хочу такой бот →",  url=f"https://t.me/{CONTACT_TG}")
    b.button(text="‹ В меню",             callback_data="menu")
    b.adjust(1); return b.as_markup()

# ── /start ──────────────────────────────────────────────────────
@dp.message(CommandStart())
async def cmd_start(message: Message):
    uid   = message.from_user.id
    uname = message.from_user.username or ""
    fname = message.from_user.full_name or ""
    is_new = not db.execute("SELECT 1 FROM users WHERE uid=?",(uid,)).fetchone()
    track(uid, uname, fname)
    if is_new and uid != ADMIN_ID:
        try:
            await message.bot.send_message(ADMIN_ID,
                f"👤 <b>Новый пользователь демо!</b>\n@{uname} · {fname}\nID: {uid}")
        except: pass
    await message.answer(
        "👋 <b>Привет! Это демо-бот BotForge.</b>\n\n"
        "Здесь можно попробовать разные типы Telegram-ботов "
        "которые мы делаем для бизнеса — прямо сейчас.\n\n"
        "Выбирайте что хотите посмотреть 👇",
        reply_markup=kb_main()
    )

@dp.callback_query(F.data == "menu")
async def show_menu(cb: CallbackQuery):
    await cb.message.edit_text(
        "👋 <b>Демо-бот BotForge</b>\n\nВыбирайте что хотите посмотреть 👇",
        reply_markup=kb_main()
    )
    await cb.answer()

# ── Возможности ─────────────────────────────────────────────────
@dp.callback_query(F.data == "capabilities")
async def show_cap(cb: CallbackQuery):
    track(cb.from_user.id, action=True)
    await cb.message.edit_text(
        "🤖 <b>Что умеют боты которые мы делаем:</b>\n\n"
        "📅 <b>Запись и бронирование</b>\nКлиент выбирает услугу → день → время. "
        "Бот напоминает сам. Отмен на 40% меньше.\n\n"
        "🛍 <b>Каталог и магазин</b>\nКатегории, карточки, корзина, оплата прямо в Telegram.\n\n"
        "❓ <b>Поддержка 24/7</b>\nОтвечает на 80% вопросов автоматически. "
        "Сложные — передаёт оператору.\n\n"
        "📣 <b>Автоворонка</b>\nСерия писем прогревает клиента и ведёт к покупке без вашего участия.\n\n"
        "📋 <b>Приём заявок</b>\nФорма → данные в Telegram и Google Таблицу. Ни одна не потеряется.\n\n"
        "🔗 <b>Интеграции</b>\namoCRM, Bitrix24, Google Sheets, 1С, YClients, Stripe.\n\n"
        "📱 <b>Mini App</b>\nПолноценное веб-приложение внутри Telegram без установки.",
        reply_markup=kb_back()
    )
    await cb.answer()

# ── ДЕМО: Запись ────────────────────────────────────────────────
SERVICES = ["✂️ Стрижка — $25","💅 Маникюр — $30","🧖 Уход за лицом — $45","💇 Окрашивание — $80"]
DAYS     = ["Понедельник 9 июня","Вторник 10 июня","Среда 11 июня","Четверг 12 июня","Пятница 13 июня"]
TIMES    = ["10:00","11:30","13:00","14:30","16:00","17:30"]

@dp.callback_query(F.data == "demo_booking")
async def demo_booking(cb: CallbackQuery):
    track(cb.from_user.id, action=True)
    b = InlineKeyboardBuilder()
    for i,s in enumerate(SERVICES): b.button(text=s, callback_data=f"bs_{i}")
    b.button(text="‹ В меню", callback_data="menu")
    b.adjust(1)
    await cb.message.edit_text(
        "📅 <b>ДЕМО: Бот записи на услуги</b>\n\n"
        "Работает 24/7 — клиент записывается сам, вы получаете уведомление. "
        "Напоминания отправляются автоматически.\n\nВыберите услугу:",
        reply_markup=b.as_markup()
    )
    await cb.answer()

@dp.callback_query(F.data.startswith("bs_"))
async def booking_service(cb: CallbackQuery):
    idx = int(cb.data[3:])
    b = InlineKeyboardBuilder()
    for i,d in enumerate(DAYS): b.button(text=d, callback_data=f"bd_{idx}_{i}")
    b.button(text="‹ Назад", callback_data="demo_booking")
    b.adjust(1)
    await cb.message.edit_text(
        f"✅ <b>{SERVICES[idx]}</b>\n\nВыберите день:", reply_markup=b.as_markup()
    )
    await cb.answer()

@dp.callback_query(F.data.startswith("bd_"))
async def booking_day(cb: CallbackQuery):
    _, si, di = cb.data.split("_")
    b = InlineKeyboardBuilder()
    for i,t in enumerate(TIMES): b.button(text=t, callback_data=f"bt_{si}_{di}_{i}")
    b.button(text="‹ Назад", callback_data=f"bs_{si}")
    b.adjust(3)
    await cb.message.edit_text(
        f"✅ <b>{SERVICES[int(si)]}</b>\n📅 {DAYS[int(di)]}\n\nВыберите время:",
        reply_markup=b.as_markup()
    )
    await cb.answer()

@dp.callback_query(F.data.startswith("bt_"))
async def booking_time(cb: CallbackQuery):
    _, si, di, ti = cb.data.split("_")
    await cb.message.edit_text(
        f"🎉 <b>Запись подтверждена!</b>\n\n"
        f"📋 {SERVICES[int(si)]}\n📅 {DAYS[int(di)]}\n⏰ {TIMES[int(ti)]}\n\n"
        f"<i>В реальном боте клиент получает:\n"
        f"• Подтверждение в Telegram\n• Напоминание за 24 часа\n• Напоминание за 1 час\n"
        f"• Возможность перенести или отменить</i>\n\n"
        f"💡 Такой бот стоит <b>от $99</b> и окупается с первого же пропущенного клиента.",
        reply_markup=kb_order()
    )
    await cb.answer()

# ── ДЕМО: Каталог ───────────────────────────────────────────────
CATALOG = {
    "🤖 Боты под ключ":[
        ("Бот-визитка","$99","Меню, информация, приём заявок"),
        ("Бот записи","$149","Расписание, напоминания, отмены"),
        ("Бот поддержки","$129","FAQ, передача оператору, 24/7"),
    ],
    "🛍 Магазины":[
        ("Интернет-магазин","$299","Каталог, корзина, оплата"),
        ("Магазин с доставкой","$399","Каталог + трекинг"),
        ("Подписочный сервис","$349","Автоплатежи, выдача доступа"),
    ],
    "⚙️ Автоматизация":[
        ("Воронка продаж","$249","Прогрев + продажа автоматически"),
        ("CRM-интеграция","$199","amoCRM / Bitrix / Sheets"),
        ("Mini App","$499","Веб-приложение в Telegram"),
    ],
}
CATS = list(CATALOG.keys())

@dp.callback_query(F.data == "demo_catalog")
async def demo_catalog(cb: CallbackQuery):
    track(cb.from_user.id, action=True)
    b = InlineKeyboardBuilder()
    for i,c in enumerate(CATS): b.button(text=c, callback_data=f"cat_{i}")
    b.button(text="‹ В меню", callback_data="menu")
    b.adjust(1)
    await cb.message.edit_text(
        "🛍 <b>ДЕМО: Каталог и магазин</b>\n\n"
        "Полноценный магазин в Telegram — категории, карточки, корзина и оплата.\n\n"
        "Выберите категорию:", reply_markup=b.as_markup()
    )
    await cb.answer()

@dp.callback_query(F.data.startswith("cat_"))
async def show_cat(cb: CallbackQuery):
    idx = int(cb.data[4:])
    items = CATALOG[CATS[idx]]
    b = InlineKeyboardBuilder()
    for i,(name,price,_) in enumerate(items):
        b.button(text=f"{name} — {price}", callback_data=f"itm_{idx}_{i}")
    b.button(text="‹ Назад", callback_data="demo_catalog")
    b.adjust(1)
    await cb.message.edit_text(f"<b>{CATS[idx]}</b>\n\nВыберите позицию:", reply_markup=b.as_markup())
    await cb.answer()

@dp.callback_query(F.data.startswith("itm_"))
async def show_item(cb: CallbackQuery):
    _, ci, ii = cb.data.split("_")
    name, price, desc = CATALOG[CATS[int(ci)]][int(ii)]
    await cb.message.edit_text(
        f"<b>{name}</b>\n\n📝 {desc}\n💰 Цена: <b>{price}</b>\n\n"
        f"<i>В реальном магазине здесь кнопки оплаты, корзина и выбор количества.</i>",
        reply_markup=kb_order()
    )
    await cb.answer()

# ── ДЕМО: FAQ ───────────────────────────────────────────────────
FAQ = {
    "Сколько стоит разработка?":
        "• Старт (визитка, заявки) — от <b>$99</b>\n"
        "• Бизнес (каталог, запись, FAQ) — от <b>$299</b>\n"
        "• Премиум (магазин, интеграции) — от <b>$699</b>",
    "Сколько времени займёт?":
        "• Простой бот — <b>2–3 дня</b>\n"
        "• Средний — <b>4–7 дней</b>\n"
        "• Сложный — <b>10–20 дней</b>",
    "Получу ли я исходный код?":
        "Да, <b>всегда</b>. Код передаётся вам после запуска. "
        "Никаких удержаний.",
    "Нужен ли сервер/хостинг?":
        "<b>Нет — хостинг включён в стоимость.</b> "
        "Мы размещаем бота и следим за его работой.",
    "Есть ли гарантия?":
        "<b>30 дней гарантии</b> после запуска. "
        "Если работает не по ТЗ — исправим бесплатно.",
    "Как оплатить?":
        "Схема: <b>50% предоплата → разработка → 50% после сдачи.</b>\n"
        "Карта, перевод, крипта. Для юрлиц — счёт и договор.",
}
FAQ_KEYS = list(FAQ.keys())

@dp.callback_query(F.data == "demo_faq")
async def demo_faq(cb: CallbackQuery):
    track(cb.from_user.id, action=True)
    b = InlineKeyboardBuilder()
    for i,q in enumerate(FAQ_KEYS): b.button(text=q, callback_data=f"fq_{i}")
    b.button(text="‹ В меню", callback_data="menu")
    b.adjust(1)
    await cb.message.edit_text(
        "❓ <b>ДЕМО: Бот поддержки / FAQ</b>\n\n"
        "Отвечает мгновенно на типовые вопросы. "
        "Сложные — передаёт живому оператору.\n\nНажмите на вопрос:",
        reply_markup=b.as_markup()
    )
    await cb.answer()

@dp.callback_query(F.data.startswith("fq_"))
async def show_faq(cb: CallbackQuery):
    idx = int(cb.data[3:])
    b = InlineKeyboardBuilder()
    b.button(text="‹ К вопросам", callback_data="demo_faq")
    b.button(text="✅ Заказать такой бот", url=f"https://t.me/{CONTACT_TG}")
    b.adjust(1)
    await cb.message.edit_text(
        f"❓ <b>{FAQ_KEYS[idx]}</b>\n\n{FAQ[FAQ_KEYS[idx]]}",
        reply_markup=b.as_markup()
    )
    await cb.answer()

# ── ДЕМО: Воронка ───────────────────────────────────────────────
@dp.callback_query(F.data == "demo_funnel")
async def demo_funnel(cb: CallbackQuery):
    track(cb.from_user.id, action=True)
    b = InlineKeyboardBuilder()
    b.button(text="🎁 Получить бесплатный чек-лист", callback_data="f1")
    b.button(text="‹ В меню", callback_data="menu")
    b.adjust(1)
    await cb.message.edit_text(
        "📣 <b>ДЕМО: Автоворонка продаж</b>\n\n"
        "Серия сообщений которая прогревает клиента и ведёт к покупке "
        "без вашего участия. Попробуйте как клиент 👇",
        reply_markup=b.as_markup()
    )
    await cb.answer()

@dp.callback_query(F.data == "f1")
async def f1(cb: CallbackQuery):
    b = InlineKeyboardBuilder()
    b.button(text="💡 Узнать как это работает", callback_data="f2")
    b.button(text="‹ В меню", callback_data="menu"); b.adjust(1)
    await cb.message.edit_text(
        "🎁 <b>Ваш чек-лист: 5 вещей которые теряет бизнес без бота</b>\n\n"
        "1. Клиенты которые написали ночью и не дождались ответа\n"
        "2. 2–4 часа в день на одинаковые вопросы\n"
        "3. Записи которые срываются без напоминания\n"
        "4. Заявки которые теряются в чатах\n"
        "5. Продажи пока вы были заняты\n\n"
        "<i>В реальной воронке следующее письмо пришло бы через 30 минут.</i>",
        reply_markup=b.as_markup()
    )
    await cb.answer()

@dp.callback_query(F.data == "f2")
async def f2(cb: CallbackQuery):
    b = InlineKeyboardBuilder()
    b.button(text="💰 Посмотреть цену", callback_data="f3")
    b.button(text="‹ В меню", callback_data="menu"); b.adjust(1)
    await cb.message.edit_text(
        "💡 <b>Что если это исправить за 3 дня?</b>\n\n"
        "Telegram-бот под ключ:\n"
        "✓ Отвечает клиентам 24/7\n"
        "✓ Записывает и напоминает автоматически\n"
        "✓ Собирает заявки пока вы спите\n"
        "✓ Интегрируется с вашими системами\n\n"
        "<i>В реальной воронке это письмо пришло бы через 2 часа.</i>",
        reply_markup=b.as_markup()
    )
    await cb.answer()

@dp.callback_query(F.data == "f3")
async def f3(cb: CallbackQuery):
    await cb.message.edit_text(
        "🎯 <b>Бот «Старт» — от $99</b>\n\n"
        "✓ Бесплатная консультация и ТЗ\n"
        "✓ Разработка под ключ\n"
        "✓ Запуск на хостинге\n"
        "✓ Исходный код — ваш\n"
        "✓ 30 дней поддержки\n\n"
        "Оплата 50/50. Срок — от 3 дней.",
        reply_markup=kb_order()
    )
    await cb.answer()

# ── ROI Калькулятор ─────────────────────────────────────────────
BIZTYPES = [
    ("beauty","Красота и здоровье",3,18),
    ("shop","Торговля",4,20),
    ("food","Общепит",3,15),
    ("edu","Образование",4,25),
    ("b2b","B2B / Услуги",3,28),
    ("other","Другой бизнес",3,20),
]
SCALES = [("1","🙋 Работаю один",1.0),("2","👥 2–5 человек",1.4),
          ("3","🏬 5–20 человек",2.0),("4","🏢 Более 20",3.0)]

@dp.callback_query(F.data == "roi_start")
async def roi_start(cb: CallbackQuery):
    track(cb.from_user.id, action=True)
    b = InlineKeyboardBuilder()
    for key,name,_,_ in BIZTYPES: b.button(text=name, callback_data=f"rb_{key}")
    b.button(text="‹ В меню", callback_data="menu"); b.adjust(2)
    await cb.message.edit_text(
        "📊 <b>Калькулятор ROI</b>\n\nПосчитаем сколько вы теряете без автоматизации.\n\nКакой у вас бизнес?",
        reply_markup=b.as_markup()
    )
    await cb.answer()

@dp.callback_query(F.data.startswith("rb_"))
async def roi_biz(cb: CallbackQuery):
    key = cb.data[3:]
    b = InlineKeyboardBuilder()
    for sid,label,_ in SCALES: b.button(text=label, callback_data=f"rs_{key}_{sid}")
    b.button(text="‹ Назад", callback_data="roi_start"); b.adjust(2)
    name = next(n for k,n,_,_ in BIZTYPES if k==key)
    await cb.message.edit_text(f"✅ <b>{name}</b>\n\nРазмер команды?", reply_markup=b.as_markup())
    await cb.answer()

@dp.callback_query(F.data.startswith("rs_"))
async def roi_result(cb: CallbackQuery):
    parts = cb.data.split("_")
    key, sid = parts[1], parts[2]
    biz = next((b for b in BIZTYPES if b[0]==key), BIZTYPES[-1])
    scale = next((s for s in SCALES if s[0]==sid), SCALES[0])
    _, name, base_h, rate = biz
    mult = scale[2]
    hours = round(base_h * mult * 22)
    money = hours * rate
    roi99  = max(2, round(99  / (money/30)))
    roi299 = max(2, round(299 / (money/30)))
    b = InlineKeyboardBuilder()
    b.button(text="💬 Обсудить автоматизацию", url=f"https://t.me/{CONTACT_TG}")
    b.button(text="‹ В меню", callback_data="menu"); b.adjust(1)
    await cb.message.edit_text(
        f"📊 <b>{name}</b>\n\n"
        f"⏰ Теряете в месяц: <b>{hours} часов</b> на рутину\n"
        f"💸 В деньгах: <b>${money:,}</b>\n\n"
        f"🤖 Бот «Старт» ($99) — окупится за <b>{roi99} дней</b>\n"
        f"🚀 Бот «Бизнес» ($299) — окупится за <b>{roi299} дней</b>\n\n"
        f"Хотите точный расчёт под ваш бизнес?",
        reply_markup=b.as_markup()
    )
    await cb.answer()

# ── Цены ────────────────────────────────────────────────────────
@dp.callback_query(F.data == "pricing")
async def pricing(cb: CallbackQuery):
    b = InlineKeyboardBuilder()
    b.button(text="💬 Обсудить проект", url=f"https://t.me/{CONTACT_TG}")
    b.button(text="‹ В меню", callback_data="menu"); b.adjust(1)
    await cb.message.edit_text(
        "💰 <b>Тарифы BotForge</b>\n\n"
        "🟢 <b>Старт — от $99</b> · 2–3 дня\n"
        "Визитка, заявки, FAQ. Хостинг + код.\n\n"
        "🔵 <b>Бизнес — от $299</b> · 5–10 дней\n"
        "Каталог, запись, интеграции, рассылки.\n\n"
        "🟣 <b>Премиум — от $699</b> · 10–20 дней\n"
        "Магазин с оплатой, Mini App, воронка.\n\n"
        "Оплата <b>50/50</b>. Гарантия <b>30 дней</b>.",
        reply_markup=b.as_markup()
    )
    await cb.answer()

# ── Админ ────────────────────────────────────────────────────────
@dp.message(Command("stats"))
async def stats(message: Message):
    if message.from_user.id != ADMIN_ID: return
    total   = db.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    today   = db.execute("SELECT COUNT(*) FROM users WHERE last_seen>?",(time.time()-86400,)).fetchone()[0]
    actions = db.execute("SELECT COALESCE(SUM(actions),0) FROM users").fetchone()[0]
    await message.answer(f"📊 Пользователей: {total} | Сегодня: {today} | Действий: {actions}")

@dp.message(Command("broadcast"))
async def broadcast(message: Message):
    if message.from_user.id != ADMIN_ID: return
    text = message.text.replace("/broadcast","").strip()
    if not text: await message.answer("Использование: /broadcast текст"); return
    uids = [r[0] for r in db.execute("SELECT uid FROM users").fetchall()]
    sent = 0
    for uid in uids:
        try: await message.bot.send_message(uid, text); sent += 1; await asyncio.sleep(.05)
        except: pass
    await message.answer(f"✅ Отправлено {sent}/{len(uids)}")

# ── Запуск webhook ───────────────────────────────────────────────
async def on_startup(bot: Bot):
    await bot.set_webhook(WEBHOOK_URL)
    logging.info(f"Webhook: {WEBHOOK_URL}")

async def on_shutdown(bot: Bot):
    await bot.delete_webhook()

def main():
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    app = web.Application()
    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path=WEBHOOK_PATH)
    setup_application(app, dp, bot=bot)
    web.run_app(app, host="0.0.0.0", port=PORT)

if __name__ == "__main__":
    main()
