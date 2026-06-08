# -*- coding: utf-8 -*-
import asyncio, logging, os, sqlite3, time
from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

BOT_TOKEN   = os.environ["BOT_TOKEN"]
ADMIN_ID    = int(os.environ.get("ADMIN_ID", "0"))
RENDER_URL  = os.environ.get("RENDER_URL", "").rstrip("/")
PORT        = int(os.environ.get("PORT", "8080"))
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL  = f"{RENDER_URL}{WEBHOOK_PATH}"
SITE_URL    = "https://strong-sawine-5c2e92.netlify.app"
CONTACT_TG  = "botforgeadmin"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# ── БД ──
db = sqlite3.connect("demo.db", check_same_thread=False)
db.execute("CREATE TABLE IF NOT EXISTS users(uid INTEGER PRIMARY KEY, username TEXT, name TEXT, joined_at REAL, last_seen REAL, actions INTEGER DEFAULT 0)")
db.commit()

def track(uid, uname="", fname="", action=False):
    now = time.time()
    if db.execute("SELECT 1 FROM users WHERE uid=?",(uid,)).fetchone():
        db.execute("UPDATE users SET last_seen=?,actions=actions+? WHERE uid=?",(now,1 if action else 0,uid))
    else:
        db.execute("INSERT INTO users VALUES(?,?,?,?,?,0)",(uid,uname,fname,now,now))
    db.commit()

# ── КЛАВИАТУРЫ ──
def kb_main():
    b = InlineKeyboardBuilder()
    b.button(text="🤖 Что умеют наши боты?",       callback_data="cap")
    b.button(text="📅 ДЕМО: Запись клиентов",       callback_data="booking")
    b.button(text="🛍 ДЕМО: Каталог и магазин",     callback_data="catalog")
    b.button(text="❓ ДЕМО: Поддержка / FAQ",       callback_data="faq")
    b.button(text="📣 ДЕМО: Автоворонка продаж",    callback_data="funnel")
    b.button(text="📊 Посчитать ROI для бизнеса",  callback_data="roi")
    b.button(text="💰 Цены и тарифы",              callback_data="prices")
    b.button(text="🎯 Пройти аудит на сайте →",    url=f"{SITE_URL}/#audit")
    b.button(text="💬 Написать нам",               url=f"https://t.me/{CONTACT_TG}")
    b.adjust(1); return b.as_markup()

def kb_back():
    b = InlineKeyboardBuilder()
    b.button(text="‹ В главное меню",           callback_data="menu")
    b.button(text="💬 Заказать такой бот",      url=f"https://t.me/{CONTACT_TG}")
    b.adjust(1); return b.as_markup()

def kb_order():
    b = InlineKeyboardBuilder()
    b.button(text="✅ Хочу такой бот →",        url=f"https://t.me/{CONTACT_TG}")
    b.button(text="‹ В меню",                   callback_data="menu")
    b.adjust(1); return b.as_markup()

# ── СТАРТ ──
@dp.message(CommandStart())
async def cmd_start(message: Message):
    uid, uname, fname = message.from_user.id, message.from_user.username or "", message.from_user.full_name or ""
    is_new = not db.execute("SELECT 1 FROM users WHERE uid=?",(uid,)).fetchone()
    track(uid, uname, fname)
    if is_new and uid != ADMIN_ID:
        try: await bot.send_message(ADMIN_ID, f"👤 Новый: @{uname} · {fname}")
        except: pass
    await message.answer(
        "👋 <b>Привет! Это демо-бот BotForge.</b>\n\n"
        "Попробуйте разные типы Telegram-ботов которые мы делаем для бизнеса — прямо сейчас.\n\n"
        "Выбирайте 👇", reply_markup=kb_main()
    )

@dp.callback_query(F.data == "menu")
async def cb_menu(cb: CallbackQuery):
    await cb.answer()
    await cb.message.edit_text(
        "👋 <b>Демо-бот BotForge</b>\n\nВыбирайте что хотите посмотреть 👇",
        reply_markup=kb_main()
    )

# ── ВОЗМОЖНОСТИ ──
@dp.callback_query(F.data == "cap")
async def cb_cap(cb: CallbackQuery):
    await cb.answer()
    track(cb.from_user.id, action=True)
    await cb.message.edit_text(
        "🤖 <b>Что умеют боты которые мы делаем:</b>\n\n"
        "📅 <b>Запись и бронирование</b>\nКлиент выбирает услугу → день → время. Бот напоминает. Отмен на 40% меньше.\n\n"
        "🛍 <b>Каталог и магазин</b>\nКатегории, карточки, корзина, оплата прямо в Telegram.\n\n"
        "❓ <b>Поддержка 24/7</b>\nОтвечает на 80% вопросов автоматически.\n\n"
        "📣 <b>Автоворонка</b>\nСерия писем прогревает клиента и ведёт к покупке без вашего участия.\n\n"
        "📋 <b>Приём заявок</b>\nФорма → Telegram и Google Таблица. Ни одна не потеряется.\n\n"
        "🔗 <b>Интеграции</b>\namoCRM, Bitrix24, Google Sheets, 1С, Stripe.\n\n"
        "📱 <b>Mini App</b>\nПолноценное веб-приложение внутри Telegram.",
        reply_markup=kb_back()
    )

# ── ЗАПИСЬ ──
SRV = ["✂️ Стрижка — $25","💅 Маникюр — $30","🧖 Уход за лицом — $45","💇 Окрашивание — $80"]
DAY = ["Понедельник","Вторник","Среда","Четверг","Пятница"]
TIM = ["10:00","11:30","13:00","14:30","16:00","17:30"]

@dp.callback_query(F.data == "booking")
async def cb_booking(cb: CallbackQuery):
    await cb.answer()
    track(cb.from_user.id, action=True)
    b = InlineKeyboardBuilder()
    for i,s in enumerate(SRV): b.button(text=s, callback_data=f"srv{i}")
    b.button(text="‹ В меню", callback_data="menu"); b.adjust(1)
    await cb.message.edit_text(
        "📅 <b>ДЕМО: Бот записи на услуги</b>\n\nРаботает 24/7 — клиент записывается сам, вы получаете уведомление. Выберите услугу:",
        reply_markup=b.as_markup()
    )

@dp.callback_query(F.data.startswith("srv"))
async def cb_srv(cb: CallbackQuery):
    await cb.answer()
    i = int(cb.data[3:])
    b = InlineKeyboardBuilder()
    for j,d in enumerate(DAY): b.button(text=d, callback_data=f"day{i}{j}")
    b.button(text="‹ Назад", callback_data="booking"); b.adjust(1)
    await cb.message.edit_text(f"✅ <b>{SRV[i]}</b>\n\nВыберите день:", reply_markup=b.as_markup())

@dp.callback_query(F.data.startswith("day"))
async def cb_day(cb: CallbackQuery):
    await cb.answer()
    si, di = int(cb.data[3]), int(cb.data[4])
    b = InlineKeyboardBuilder()
    for k,t in enumerate(TIM): b.button(text=t, callback_data=f"tim{si}{di}{k}")
    b.button(text="‹ Назад", callback_data=f"srv{si}"); b.adjust(3)
    await cb.message.edit_text(f"✅ <b>{SRV[si]}</b>\n📅 {DAY[di]}\n\nВыберите время:", reply_markup=b.as_markup())

@dp.callback_query(F.data.startswith("tim"))
async def cb_tim(cb: CallbackQuery):
    await cb.answer()
    si, di, ti = int(cb.data[3]), int(cb.data[4]), int(cb.data[5])
    await cb.message.edit_text(
        f"🎉 <b>Запись подтверждена!</b>\n\n{SRV[si]}\n📅 {DAY[di]}\n⏰ {TIM[ti]}\n\n"
        f"<i>В реальном боте клиент получает подтверждение, напоминание за 24 часа и за 1 час.</i>\n\n"
        f"💡 Такой бот — <b>от $99</b>. Окупается с первого же пропущенного клиента.",
        reply_markup=kb_order()
    )

# ── КАТАЛОГ ──
CATS = ["🤖 Боты под ключ","🛍 Магазины","⚙️ Автоматизация"]
ITEMS = [
    [("Бот-визитка","$99","Меню, информация, заявки"),("Бот записи","$149","Расписание, напоминания"),("Бот поддержки","$129","FAQ, оператор, 24/7")],
    [("Интернет-магазин","$299","Каталог, корзина, оплата"),("Магазин с доставкой","$399","+ трекинг"),("Подписки","$349","Автоплатежи, доступ")],
    [("Воронка продаж","$249","Прогрев + продажа"),("CRM-интеграция","$199","amoCRM/Bitrix/Sheets"),("Mini App","$499","Веб-приложение в Telegram")],
]

@dp.callback_query(F.data == "catalog")
async def cb_catalog(cb: CallbackQuery):
    await cb.answer()
    track(cb.from_user.id, action=True)
    b = InlineKeyboardBuilder()
    for i,c in enumerate(CATS): b.button(text=c, callback_data=f"cat{i}")
    b.button(text="‹ В меню", callback_data="menu"); b.adjust(1)
    await cb.message.edit_text("🛍 <b>ДЕМО: Каталог</b>\n\nПолноценный магазин в Telegram. Выберите категорию:", reply_markup=b.as_markup())

@dp.callback_query(F.data.startswith("cat"))
async def cb_cat(cb: CallbackQuery):
    await cb.answer()
    ci = int(cb.data[3])
    b = InlineKeyboardBuilder()
    for ii,(name,price,_) in enumerate(ITEMS[ci]): b.button(text=f"{name} — {price}", callback_data=f"itm{ci}{ii}")
    b.button(text="‹ Назад", callback_data="catalog"); b.adjust(1)
    await cb.message.edit_text(f"<b>{CATS[ci]}</b>\n\nВыберите позицию:", reply_markup=b.as_markup())

@dp.callback_query(F.data.startswith("itm"))
async def cb_itm(cb: CallbackQuery):
    await cb.answer()
    ci, ii = int(cb.data[3]), int(cb.data[4])
    name, price, desc = ITEMS[ci][ii]
    await cb.message.edit_text(
        f"<b>{name}</b>\n\n📝 {desc}\n💰 <b>{price}</b>\n\n<i>В реальном магазине — кнопка оплаты, корзина, выбор количества.</i>",
        reply_markup=kb_order()
    )

# ── FAQ ──
QA = [
    ("Сколько стоит разработка?", "• Старт — от <b>$99</b>\n• Бизнес — от <b>$299</b>\n• Премиум — от <b>$699</b>"),
    ("Сколько времени займёт?", "• Простой — <b>2–3 дня</b>\n• Средний — <b>4–7 дней</b>\n• Сложный — <b>10–20 дней</b>"),
    ("Получу ли я исходный код?", "Да, <b>всегда</b>. Код передаётся вам после запуска."),
    ("Нужен ли сервер/хостинг?", "<b>Нет — хостинг включён</b> в стоимость. Мы размещаем и следим."),
    ("Есть ли гарантия?", "<b>30 дней гарантии</b> после запуска. Не по ТЗ — исправим бесплатно."),
    ("Как оплатить?", "Схема: <b>50% предоплата → разработка → 50% после сдачи.</b>"),
]

@dp.callback_query(F.data == "faq")
async def cb_faq(cb: CallbackQuery):
    await cb.answer()
    track(cb.from_user.id, action=True)
    b = InlineKeyboardBuilder()
    for i,(q,_) in enumerate(QA): b.button(text=q, callback_data=f"qa{i}")
    b.button(text="‹ В меню", callback_data="menu"); b.adjust(1)
    await cb.message.edit_text("❓ <b>ДЕМО: Поддержка / FAQ</b>\n\nНажмите на вопрос:", reply_markup=b.as_markup())

@dp.callback_query(F.data.startswith("qa"))
async def cb_qa(cb: CallbackQuery):
    await cb.answer()
    i = int(cb.data[2:])
    q, a = QA[i]
    b = InlineKeyboardBuilder()
    b.button(text="‹ К вопросам", callback_data="faq")
    b.button(text="✅ Заказать бот", url=f"https://t.me/{CONTACT_TG}"); b.adjust(1)
    await cb.message.edit_text(f"❓ <b>{q}</b>\n\n{a}", reply_markup=b.as_markup())

# ── ВОРОНКА ──
@dp.callback_query(F.data == "funnel")
async def cb_funnel(cb: CallbackQuery):
    await cb.answer()
    track(cb.from_user.id, action=True)
    b = InlineKeyboardBuilder()
    b.button(text="🎁 Получить бесплатный чек-лист", callback_data="fn1")
    b.button(text="‹ В меню", callback_data="menu"); b.adjust(1)
    await cb.message.edit_text(
        "📣 <b>ДЕМО: Автоворонка продаж</b>\n\nСерия писем которая прогревает клиента и ведёт к покупке без вашего участия. Попробуйте 👇",
        reply_markup=b.as_markup()
    )

@dp.callback_query(F.data == "fn1")
async def cb_fn1(cb: CallbackQuery):
    await cb.answer()
    b = InlineKeyboardBuilder()
    b.button(text="💡 Как это исправить?", callback_data="fn2")
    b.button(text="‹ В меню", callback_data="menu"); b.adjust(1)
    await cb.message.edit_text(
        "🎁 <b>5 вещей которые теряет бизнес без бота:</b>\n\n"
        "1. Клиенты которые написали ночью и не дождались\n"
        "2. 2–4 часа в день на одинаковые вопросы\n"
        "3. Записи которые срываются без напоминания\n"
        "4. Заявки которые теряются в чатах\n"
        "5. Продажи пока вы были заняты\n\n"
        "<i>В реальной воронке следующее письмо пришло бы через 30 минут.</i>",
        reply_markup=b.as_markup()
    )

@dp.callback_query(F.data == "fn2")
async def cb_fn2(cb: CallbackQuery):
    await cb.answer()
    b = InlineKeyboardBuilder()
    b.button(text="💰 Посмотреть цену", callback_data="fn3")
    b.button(text="‹ В меню", callback_data="menu"); b.adjust(1)
    await cb.message.edit_text(
        "💡 <b>Что если исправить это за 3 дня?</b>\n\n"
        "Telegram-бот под ключ:\n"
        "✓ Отвечает 24/7\n✓ Записывает и напоминает\n✓ Собирает заявки пока вы спите\n\n"
        "<i>В реальной воронке — через 2 часа.</i>",
        reply_markup=b.as_markup()
    )

@dp.callback_query(F.data == "fn3")
async def cb_fn3(cb: CallbackQuery):
    await cb.answer()
    await cb.message.edit_text(
        "🎯 <b>Бот «Старт» — от $99</b>\n\n"
        "✓ Консультация и ТЗ бесплатно\n✓ Разработка под ключ\n"
        "✓ Запуск на хостинге\n✓ Исходный код — ваш\n✓ 30 дней поддержки\n\n"
        "Оплата 50/50. Срок — от 3 дней.",
        reply_markup=kb_order()
    )

# ── ROI ──
BIZ = [("bt0","💇 Красота/здоровье",3,18),("bt1","🛍 Торговля",4,20),
       ("bt2","🍽 Общепит",3,15),("bt3","📚 Образование",4,25),
       ("bt4","🏢 B2B/Услуги",3,28),("bt5","✨ Другое",3,20)]
SCL = [("s0","🙋 Работаю один",1.0),("s1","👥 2–5 человек",1.4),
       ("s2","🏬 5–20 человек",2.0),("s3","🏢 Более 20",3.0)]

@dp.callback_query(F.data == "roi")
async def cb_roi(cb: CallbackQuery):
    await cb.answer()
    track(cb.from_user.id, action=True)
    b = InlineKeyboardBuilder()
    for k,name,_,_ in BIZ: b.button(text=name, callback_data=f"rb{k}")
    b.button(text="‹ В меню", callback_data="menu"); b.adjust(2)
    await cb.message.edit_text("📊 <b>Калькулятор ROI</b>\n\nКакой у вас бизнес?", reply_markup=b.as_markup())

@dp.callback_query(F.data.startswith("rb"))
async def cb_rb(cb: CallbackQuery):
    await cb.answer()
    key = cb.data[2:]
    biz = next(x for x in BIZ if x[0]==key)
    b = InlineKeyboardBuilder()
    for sk,label,_ in SCL: b.button(text=label, callback_data=f"rs{key}_{sk}")
    b.button(text="‹ Назад", callback_data="roi"); b.adjust(2)
    await cb.message.edit_text(f"✅ <b>{biz[1]}</b>\n\nРазмер команды?", reply_markup=b.as_markup())

@dp.callback_query(F.data.startswith("rs"))
async def cb_rs(cb: CallbackQuery):
    await cb.answer()
    parts = cb.data[2:].split("_")
    key, sk = parts[0], parts[1]
    biz  = next(x for x in BIZ if x[0]==key)
    scl  = next(x for x in SCL if x[0]==sk)
    h    = round(biz[2] * scl[2] * 22)
    m    = h * biz[3]
    r99  = max(2, round(99  / (m/30)))
    r299 = max(2, round(299 / (m/30)))
    b = InlineKeyboardBuilder()
    b.button(text="💬 Обсудить автоматизацию", url=f"https://t.me/{CONTACT_TG}")
    b.button(text="‹ В меню", callback_data="menu"); b.adjust(1)
    await cb.message.edit_text(
        f"📊 <b>{biz[1]}</b>\n\n"
        f"⏰ Теряете в месяц: <b>{h} часов</b>\n"
        f"💸 В деньгах: <b>${m:,}</b>\n\n"
        f"🤖 Бот «Старт» ($99) — окупится за <b>{r99} дней</b>\n"
        f"🚀 Бот «Бизнес» ($299) — окупится за <b>{r299} дней</b>",
        reply_markup=b.as_markup()
    )

# ── ЦЕНЫ ──
@dp.callback_query(F.data == "prices")
async def cb_prices(cb: CallbackQuery):
    await cb.answer()
    b = InlineKeyboardBuilder()
    b.button(text="💬 Обсудить проект", url=f"https://t.me/{CONTACT_TG}")
    b.button(text="‹ В меню", callback_data="menu"); b.adjust(1)
    await cb.message.edit_text(
        "💰 <b>Тарифы BotForge</b>\n\n"
        "🟢 <b>Старт — от $99</b> · 2–3 дня\nВизитка, заявки, FAQ.\n\n"
        "🔵 <b>Бизнес — от $299</b> · 5–10 дней\nКаталог, запись, интеграции.\n\n"
        "🟣 <b>Премиум — от $699</b> · 10–20 дней\nМагазин, Mini App, воронка.\n\n"
        "Оплата <b>50/50</b>. Гарантия <b>30 дней</b>.",
        reply_markup=b.as_markup()
    )

# ── АДМИН ──
@dp.message(Command("stats"))
async def cmd_stats(message: Message):
    if message.from_user.id != ADMIN_ID: return
    total   = db.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    today   = db.execute("SELECT COUNT(*) FROM users WHERE last_seen>?",(time.time()-86400,)).fetchone()[0]
    actions = db.execute("SELECT COALESCE(SUM(actions),0) FROM users").fetchone()[0]
    await message.answer(f"📊 Всего: {total} | Сегодня: {today} | Действий: {actions}")

@dp.message(Command("broadcast"))
async def cmd_broadcast(message: Message):
    if message.from_user.id != ADMIN_ID: return
    text = message.text.replace("/broadcast","").strip()
    if not text: await message.answer("Использование: /broadcast текст"); return
    uids = [r[0] for r in db.execute("SELECT uid FROM users").fetchall()]
    sent = 0
    for uid in uids:
        try: await bot.send_message(uid, text); sent += 1; await asyncio.sleep(.05)
        except: pass
    await message.answer(f"✅ {sent}/{len(uids)}")

# ── WEBHOOK ──
async def on_startup(_bot: Bot):
    await _bot.set_webhook(WEBHOOK_URL)
    logging.info(f"Webhook: {WEBHOOK_URL}")

async def on_shutdown(_bot: Bot):
    await _bot.delete_webhook()

def main():
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    app = web.Application()
    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path=WEBHOOK_PATH)
    setup_application(app, dp, bot=bot)
    web.run_app(app, host="0.0.0.0", port=PORT)

if __name__ == "__main__":
    main()
