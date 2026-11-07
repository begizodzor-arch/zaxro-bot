# -*- coding: utf-8 -*-
import asyncio
import json
import logging
import os
import re
import sys
from datetime import datetime

# Windows konsolida emojilar to'g'ri chiqishi uchun
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, F, types
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
    Message,
    FSInputFile,
    ReplyKeyboardRemove,
)

import database
from shop_info import SHOP_INFO, TEXTS
from ai_consultant import AIConsultant
import keyboards as kb

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("ZaxroParfumeBot")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

BOT_TOKEN    = os.getenv("BOT_TOKEN", "").strip()
GEMINI_KEY   = os.getenv("GEMINI_API_KEY", "").strip()
ADMIN_USER   = os.getenv("ADMIN_USERNAME", "@BaxtiyorovBehzod1").strip()
ADMIN_ID     = int(os.getenv("ADMIN_ID", "6158301754").strip())
ADMIN_PHONE  = os.getenv("ADMIN_PHONE", "+998 99 484 19 81").strip()
CARD_NUMBER  = os.getenv("CARD_NUMBER", "6262 5707 1622 6610").strip()
CARD_OWNER   = os.getenv("CARD_OWNER", "Baxtiyorov Behzodbek").strip()
GROUP_LINK   = os.getenv("GROUP_LINK", "https://t.me/zaxro_parfume").strip()

CATALOG_PATH = os.path.join(BASE_DIR, "products.json")
IMAGES_DIR   = os.path.join(BASE_DIR, "images")
os.makedirs(IMAGES_DIR, exist_ok=True)

# Baza va mahsulotlarni initsializatsiya qilish
database.init_db()

consultant = AIConsultant(
    catalog_path=CATALOG_PATH,
    gemini_api_key=GEMINI_KEY or None,
    admin_phone=ADMIN_PHONE,
    admin_username=ADMIN_USER,
    channel_link=GROUP_LINK
)

storage = MemoryStorage()
dp = Dispatcher(storage=storage)


# ─── FSM HOLATLARI ───────────────────────────────────────────────

class OrderStates(StatesGroup):
    choosing_payment = State()
    waiting_receipt  = State()
    waiting_phone    = State()


class CheckoutStates(StatesGroup):
    waiting_name     = State()
    waiting_phone    = State()
    waiting_address  = State()
    waiting_payment  = State()
    waiting_receipt  = State()
    entering_promo   = State()


class PromoStates(StatesGroup):
    entering_promo   = State()


class AdminAddProductStates(StatesGroup):
    waiting_name        = State()
    waiting_brand       = State()
    waiting_gender      = State()
    waiting_volume      = State()
    waiting_price       = State()
    waiting_photo       = State()
    waiting_top_notes   = State()
    waiting_heart_notes = State()
    waiting_base_notes  = State()
    waiting_durability  = State()
    waiting_description = State()


class AdminEditPriceStates(StatesGroup):
    waiting_price = State()


class AdminAddPromoStates(StatesGroup):
    waiting_text  = State()


class AdminAddCodeStates(StatesGroup):
    waiting_code     = State()
    waiting_discount = State()


class AdminBroadcastStates(StatesGroup):
    waiting_content  = State()


class AdminBlockUserStates(StatesGroup):
    waiting_user_id  = State()


class AdminReplyTicketStates(StatesGroup):
    waiting_reply    = State()


# ─── YORDAMCHI FUNKSIYALAR ────────────────────────────────────────

def _fmt_time() -> str:
    return datetime.now().strftime("%d.%m.%Y %H:%M")


def _user_link(user: types.User) -> str:
    if user.username:
        return f"@{user.username}"
    return f"[{user.full_name}](tg://user?id={user.id})"


def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID


def format_product_caption(p: dict, lang: str = "uz") -> str:
    stock_status = ("✅ Mavjud" if lang == "uz" else "✅ В наличии") if p.get("in_stock", 1) else ("❌ Tugagan" if lang == "uz" else "❌ Нет в наличии")
    price_fmt = f"{p.get('price', 0):,} so'm".replace(",", " ")
    
    brand_line = f"🏷️ <b>{'Brend' if lang == 'uz' else 'Бренд'}:</b> {p.get('brand')}\n" if p.get('brand') else ""
    gender_map_uz = {"erkak": "👨 Erkaklar uchun", "ayol": "👩 Ayollar uchun", "uniseks": "👫 Uniseks"}
    gender_map_ru = {"erkak": "👨 Мужской", "ayol": "👩 Женский", "uniseks": "👫 Унисекс"}
    g_map = gender_map_ru if lang == "ru" else gender_map_uz
    gender_val = g_map.get(str(p.get("gender", "")).lower(), p.get("gender", "Uniseks"))
    
    vol_title = "Hajmi" if lang == "uz" else "Объем"
    price_title = "Narxi" if lang == "uz" else "Цена"
    stock_title = "Holati" if lang == "uz" else "Статус"
    
    text = (
        f"🌸 <b>{p.get('name')}</b>\n"
        f"{brand_line}"
        f"👤 <b>{'Jinsi' if lang == 'uz' else 'Пол'}:</b> {gender_val}\n"
    )
    if p.get("volume"):
        text += f"🧪 <b>{vol_title}:</b> {p['volume']}\n"
    text += (
        f"💰 <b>{price_title}:</b> <b>{price_fmt}</b>\n"
        f"📦 <b>{stock_title}:</b> {stock_status}\n"
    )
    
    notes_exist = any([p.get('top_notes'), p.get('heart_notes'), p.get('base_notes')])
    if notes_exist:
        notes_title = "Hid notalari" if lang == "uz" else "Ноты аромата"
        top_title = "Yuqori (Top)" if lang == "uz" else "Верхние"
        heart_title = "O'rta (Yurak)" if lang == "uz" else "Ноты сердца"
        base_title = "Baza (Shleyf)" if lang == "uz" else "Базовые"
        dur_title = "Turg'unligi" if lang == "uz" else "Стойкость"
        
        text += f"\n🌺 <b>{notes_title}:</b>\n"
        if p.get("top_notes"):
            text += f" • <b>{top_title}:</b> {p['top_notes']}\n"
        if p.get("heart_notes"):
            text += f" • <b>{heart_title}:</b> {p['heart_notes']}\n"
        if p.get("base_notes"):
            text += f" • <b>{base_title}:</b> {p['base_notes']}\n"
            
    if p.get("durability"):
        dur_lbl = "Turg'unligi" if lang == "uz" else "Стойкость"
        text += f"⏳ <b>{dur_lbl}:</b> {p['durability']}\n"
        
    if p.get("description"):
        text += f"\n📝 <i>{p.get('description')}</i>"
        
    return text


async def send_product_card(target, product: dict, user_id: int, lang: str = "uz"):
    caption = format_product_caption(product, lang=lang)
    markup = kb.get_product_detail_keyboard(product, user_id=user_id, lang=lang)
    
    img = product.get("image")
    sent = False
    target_msg = target.message if isinstance(target, CallbackQuery) else target
    
    if img:
        img_path = os.path.join(IMAGES_DIR, img) if not img.startswith("http") else img
        if img.startswith("http"):
            try:
                await target_msg.answer_photo(photo=img, caption=caption[:1024], reply_markup=markup, parse_mode=ParseMode.HTML)
                sent = True
            except Exception as e:
                logger.warning(f"URL photo error: {e}")
        elif os.path.exists(img_path):
            try:
                await target_msg.answer_photo(photo=FSInputFile(img_path), caption=caption[:1024], reply_markup=markup, parse_mode=ParseMode.HTML)
                sent = True
            except Exception as e:
                logger.warning(f"File photo error: {e}")

    if not sent:
        await target_msg.answer(caption, reply_markup=markup, parse_mode=ParseMode.HTML)


async def show_card_payment_info(target, order_code: str, total_amount: int, items_text: str = "", lang: str = "uz"):
    amount_fmt = f"{total_amount:,} so'm".replace(",", " ")
    items_block = f"📦 <b>{'Mahsulotlar' if lang == 'uz' else 'Товары'}:</b>\n{items_text}\n" if items_text else ""
    
    if lang == "ru":
        text = (
            "╔════════════════════════════╗\n"
            "       💳  <b>ОНЛАЙН ОПЛАТА</b>\n"
            "╚════════════════════════════╝\n\n"
            f"🔢 <b>Номер заказа:</b> <code>#{order_code}</code>\n"
            f"{items_block}"
            f"💰 <b>Сумма к оплате:</b> <b>{amount_fmt}</b>\n\n"
            "📌 <b>Номер карты:</b>\n"
            f"<code>{CARD_NUMBER}</code> <i>(нажмите чтобы скопировать)</i>\n\n"
            f"👤 <b>Владелец карты:</b> <b>{CARD_OWNER}</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "✅ После оплаты, пожалуйста, отправьте\n"
            "<b>скриншот или фото чека</b> сюда!\n"
            "Администратор проверит чек и сразу подтвердит заказ. 🌸"
        )
    else:
        text = (
            "╔════════════════════════════╗\n"
            "       💳  <b>ONLAYN TO'LOV</b>\n"
            "╚════════════════════════════╝\n\n"
            f"🔢 <b>Buyurtma raqami:</b> <code>#{order_code}</code>\n"
            f"{items_block}"
            f"💰 <b>To'lov summasi:</b> <b>{amount_fmt}</b>\n\n"
            "📌 <b>Karta raqami:</b>\n"
            f"<code>{CARD_NUMBER}</code> <i>(bosib nusxalang)</i>\n\n"
            f"👤 <b>Karta egasi:</b> <b>{CARD_OWNER}</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "✅ To'lovni amalga oshirgach,\n"
            "<b>to'lov chekining rasmini (skrinshotini)</b> shu yerga yuboring!\n"
            "Administrator chekni tekshirib, buyurtmangizni darhol tasdiqlaydi. 🌸"
        )
        
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📞 " + ("Administratorga ulash" if lang == "uz" else "Связаться с администратором"), callback_data=f"pay_operator_order:{order_code}")],
        [InlineKeyboardButton(text="❌ " + ("Bekor qilish" if lang == "uz" else "Отмена"), callback_data="pay_cancel")]
    ])
    
    if isinstance(target, CallbackQuery):
        await target.message.answer(text, reply_markup=markup, parse_mode=ParseMode.HTML)
    else:
        await target.answer(text, reply_markup=markup, parse_mode=ParseMode.HTML)


# ─── ASOSIY BUYRUQLAR (/start, /help, /admin) ───────────────────

@dp.message(CommandStart())
async def handle_start(message: Message, state: FSMContext):
    await state.clear()
    user = message.from_user
    
    if database.is_user_blocked(user.id):
        await message.answer("Siz botdan foydalanishdan bloklangansiz.")
        return
        
    database.register_user(user.id, user.full_name, user.username)
    lang = database.get_user_language(user.id)
    user_is_adm = is_admin(user.id)
    
    name = user.first_name or ("Mijoz" if lang == "uz" else "Клиент")
    
    if lang == "ru":
        welcome = (
            f"🌸 <b>Здравствуйте, {name}!</b>\n\n"
            f"Добро пожаловать в официальный бот магазина <b>«{SHOP_INFO['name']}»</b>!\n\n"
            "У нас вы найдете качественную парфюмерию и ароматы (1:1 копия).\n"
            "Для удобства используйте кнопки меню ниже: 👇"
        )
    else:
        welcome = (
            f"🌸 <b>Assalomu alaykum, {name}!</b>\n\n"
            f"<b>«{SHOP_INFO['name']}»</b> do'konining rasmiy botiga xush kelibsiz!\n\n"
            "Bizda sifatli parfyumeriya va atirlar (1:1 nusxa) taqdim etiladi.\n"
            "Quyidagi qulay menyu tugmalaridan birini tanlang: 👇"
        )
        
    await message.answer(
        welcome,
        reply_markup=kb.get_main_reply_keyboard(user.id, is_admin=user_is_adm, lang=lang),
        parse_mode=ParseMode.HTML
    )


@dp.message(Command("help"))
async def handle_help(message: Message):
    lang = database.get_user_language(message.from_user.id)
    if lang == "ru":
        text = (
            f"ℹ️ <b>Помощь по боту «{SHOP_INFO['name']}»:</b>\n\n"
            "🔹 <b>Каталог:</b> Просмотр и заказ товаров.\n"
            "🔹 <b>Корзина:</b> Оформление нескольких товаров в один заказ.\n"
            "🔹 <b>Оплата:</b> Оплата на карту и отправка чека.\n"
            "🔹 <b>Связь:</b> Ответы на вопросы напрямую от администратора.\n\n"
            f"📱 Телефон: {SHOP_INFO['phone']}\n"
            f"👤 Администратор: {SHOP_INFO['admin_username']}\n"
            f"📢 Канал: {SHOP_INFO['channel_link']}"
        )
    else:
        text = (
            f"ℹ️ <b>«{SHOP_INFO['name']}» botidan foydalanish:</b>\n\n"
            "🔹 <b>Katalog:</b> Mahsulotlarni ko'rish va buyurtma berish.\n"
            "🔹 <b>Savatcha:</b> Bir nechta tovarlarni bitta buyurtmaga birlashtirish.\n"
            "🔹 <b>To'lov:</b> Karta orqali to'lash va chek yuborish.\n"
            "🔹 <b>Aloqa:</b> Savollaringizga administratorimiz bevosita javob beradi.\n\n"
            f"📱 Telefon: {SHOP_INFO['phone']}\n"
            f"👤 Administrator: {SHOP_INFO['admin_username']}\n"
            f"📢 Telegram kanal: {SHOP_INFO['channel_link']}"
        )
    await message.answer(text, parse_mode=ParseMode.HTML)


@dp.message(Command("admin"))
async def handle_admin_command(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("Kechirasiz, ushbu buyruq faqat administrator uchun.")
        return
    await state.clear()
    await message.answer("⚙️ <b>Administrator Boshqaruv Paneli:</b>", reply_markup=kb.get_admin_panel_keyboard(), parse_mode=ParseMode.HTML)


# ─── TIL TANLASH (UZ / RU) ──────────────────────────────────────

@dp.message(F.text.in_(["🌐 Tilni o'zgartirish", "🌐 Сменить язык"]))
async def handle_change_language(message: Message):
    await message.answer("Iltimos, tilni tanlang / Пожалуйста, выберите язык:", reply_markup=kb.get_language_keyboard())


@dp.callback_query(F.data.startswith("set_lang:"))
async def handle_set_lang(call: CallbackQuery):
    lang = call.data.split(":")[1]
    database.set_user_language(call.from_user.id, lang)
    user_is_adm = is_admin(call.from_user.id)
    
    if lang == "ru":
        msg = "✅ Язык успешно изменен на Русский!"
    else:
        msg = "✅ Til muvaffaqiyatli O'zbek tiliga o'zgartirildi!"
        
    await call.message.delete()
    await call.message.answer(
        msg,
        reply_markup=kb.get_main_reply_keyboard(call.from_user.id, is_admin=user_is_adm, lang=lang)
    )
    await call.answer()


# ─── 1. KATALOG BO'LIMI ──────────────────────────────────────────

@dp.message(F.text.in_(["🌸 Katalog", "🌸 Каталог"]))
async def handle_catalog_button(message: Message):
    lang = database.get_user_language(message.from_user.id)
    all_products = database.get_all_products()
    
    # KATALOG HOZIRCHA BO'SH BO'LSA
    if not all_products:
        await message.answer(
            TEXTS[lang]["empty_catalog"],
            reply_markup=kb.get_empty_catalog_keyboard(lang),
            parse_mode=ParseMode.HTML
        )
        return
        
    # Katalog to'ldirilgan bo'lsa
    title = "🛍️ <b>«Zaxro Parfume» Katalogi:</b>" if lang == "uz" else "🛍️ <b>Каталог «Zaxro Parfume»:</b>"
    await message.answer(title, reply_markup=kb.get_catalog_menu_keyboard(lang), parse_mode=ParseMode.HTML)


@dp.callback_query(F.data == "catalog_home")
async def cb_catalog_home(call: CallbackQuery):
    lang = database.get_user_language(call.from_user.id)
    all_products = database.get_all_products()
    if not all_products:
        await call.message.edit_text(
            TEXTS[lang]["empty_catalog"],
            reply_markup=kb.get_empty_catalog_keyboard(lang),
            parse_mode=ParseMode.HTML
        )
        await call.answer()
        return
        
    title = "🛍️ <b>«Zaxro Parfume» Katalogi:</b>" if lang == "uz" else "🛍️ <b>Каталог «Zaxro Parfume»:</b>"
    try:
        await call.message.edit_text(title, reply_markup=kb.get_catalog_menu_keyboard(lang), parse_mode=ParseMode.HTML)
    except Exception:
        await call.message.answer(title, reply_markup=kb.get_catalog_menu_keyboard(lang), parse_mode=ParseMode.HTML)
    await call.answer()


@dp.callback_query(F.data == "filter_all")
async def cb_filter_all(call: CallbackQuery):
    lang = database.get_user_language(call.from_user.id)
    products = database.get_all_products()
    if not products:
        await call.answer(TEXTS[lang]["empty_catalog"], show_alert=True)
        return
    txt = f"✨ <b>{'Barcha mahsulotlar' if lang == 'uz' else 'Все товары'} ({len(products)}):</b>"
    await call.message.answer(txt, reply_markup=kb.get_products_list_keyboard(products, lang=lang), parse_mode=ParseMode.HTML)
    await call.answer()


@dp.callback_query(F.data == "filter_brand_menu")
async def cb_filter_brand_menu(call: CallbackQuery):
    lang = database.get_user_language(call.from_user.id)
    brands = database.get_distinct_brands()
    if not brands:
        await call.answer("Hozircha brendlar mavjud emas.", show_alert=True)
        return
    txt = "🏷️ <b>Brendni tanlang:</b>" if lang == "uz" else "🏷️ <b>Выберите бренд:</b>"
    await call.message.answer(txt, reply_markup=kb.get_brands_keyboard(lang=lang), parse_mode=ParseMode.HTML)
    await call.answer()


@dp.callback_query(F.data.startswith("f_brand:"))
async def cb_filter_brand_sel(call: CallbackQuery):
    lang = database.get_user_language(call.from_user.id)
    brand = call.data.split(":", 1)[1]
    products = database.filter_products(brand=brand)
    if not products:
        await call.answer("Ushbu brend bo'yicha mahsulot topilmadi.", show_alert=True)
        return
    txt = f"🏷️ <b>{brand} ({len(products)}):</b>"
    await call.message.answer(txt, reply_markup=kb.get_products_list_keyboard(products, lang=lang), parse_mode=ParseMode.HTML)
    await call.answer()


@dp.callback_query(F.data == "filter_gender_menu")
async def cb_filter_gender_menu(call: CallbackQuery):
    lang = database.get_user_language(call.from_user.id)
    txt = "👤 <b>Jins bo'yicha tanlang:</b>" if lang == "uz" else "👤 <b>Выберите по полу:</b>"
    await call.message.answer(txt, reply_markup=kb.get_gender_keyboard(lang=lang), parse_mode=ParseMode.HTML)
    await call.answer()


@dp.callback_query(F.data.startswith("f_gender:"))
async def cb_filter_gender_sel(call: CallbackQuery):
    lang = database.get_user_language(call.from_user.id)
    gender = call.data.split(":")[1]
    products = database.filter_products(gender=gender)
    if not products:
        await call.answer("Mahsulotlar topilmadi.", show_alert=True)
        return
    txt = f"👤 <b>Tanlangan toifadagi mahsulotlar ({len(products)}):</b>"
    await call.message.answer(txt, reply_markup=kb.get_products_list_keyboard(products, lang=lang), parse_mode=ParseMode.HTML)
    await call.answer()


@dp.callback_query(F.data == "filter_price_menu")
async def cb_filter_price_menu(call: CallbackQuery):
    lang = database.get_user_language(call.from_user.id)
    txt = "💰 <b>Narx oralig'ini tanlang:</b>" if lang == "uz" else "💰 <b>Выберите диапазон цен:</b>"
    await call.message.answer(txt, reply_markup=kb.get_price_filter_keyboard(lang=lang), parse_mode=ParseMode.HTML)
    await call.answer()


@dp.callback_query(F.data.startswith("f_price:"))
async def cb_filter_price_sel(call: CallbackQuery):
    lang = database.get_user_language(call.from_user.id)
    parts = call.data.split(":")
    min_p, max_p = int(parts[1]), int(parts[2])
    products = database.filter_products(min_price=min_p, max_price=max_p)
    if not products:
        await call.answer("Bu narxda mahsulot topilmadi.", show_alert=True)
        return
    txt = f"💰 <b>Narx bo'yicha saralangan mahsulotlar ({len(products)}):</b>"
    await call.message.answer(txt, reply_markup=kb.get_products_list_keyboard(products, lang=lang), parse_mode=ParseMode.HTML)
    await call.answer()


@dp.callback_query(F.data.startswith("prod:"))
async def cb_product_detail(call: CallbackQuery):
    lang = database.get_user_language(call.from_user.id)
    p_id = int(call.data.split(":")[1])
    product = database.get_product(p_id)
    if not product:
        await call.answer("Mahsulot topilmadi!", show_alert=True)
        return
    await send_product_card(call, product, user_id=call.from_user.id, lang=lang)
    await call.answer()


@dp.callback_query(F.data == "back_main")
async def cb_back_main(call: CallbackQuery, state: FSMContext):
    await state.clear()
    lang = database.get_user_language(call.from_user.id)
    user_is_adm = is_admin(call.from_user.id)
    txt = "🌸 <b>Bosh menyu:</b>" if lang == "uz" else "🌸 <b>Главное меню:</b>"
    try:
        await call.message.delete()
    except Exception:
        pass
    await call.message.answer(txt, reply_markup=kb.get_main_reply_keyboard(call.from_user.id, is_admin=user_is_adm, lang=lang), parse_mode=ParseMode.HTML)
    await call.answer()


# ─── 2. AKSIYA VA CHEGIRMALAR ───────────────────────────────────

@dp.message(F.text.in_(["🎁 Aksiya va Chegirmalar", "🎁 Акции и скидки"]))
async def handle_promos_button(message: Message):
    lang = database.get_user_language(message.from_user.id)
    promos = database.get_active_promotions()
    
    if not promos:
        await message.answer(TEXTS[lang]["empty_promos"], reply_markup=kb.get_promos_keyboard(lang), parse_mode=ParseMode.HTML)
        return
        
    for p in promos:
        t = f"🎁 <b>{p.get('title') or 'Aksiya'}</b>\n\n{p['text']}"
        await message.answer(t, parse_mode=ParseMode.HTML)
        
    await message.answer("🏷️ Promokod kiritish uchun pastdagi tugmani bosing:", reply_markup=kb.get_promos_keyboard(lang))


@dp.callback_query(F.data == "enter_promo_code")
async def cb_enter_promo_code(call: CallbackQuery, state: FSMContext):
    lang = database.get_user_language(call.from_user.id)
    await state.set_state(PromoStates.entering_promo)
    txt = "🏷️ Iltimos, <b>promokodni</b> kiriting:" if lang == "uz" else "🏷️ Пожалуйста, введите <b>промокод</b>:"
    await call.message.answer(txt, parse_mode=ParseMode.HTML)
    await call.answer()


@dp.message(PromoStates.entering_promo, F.text)
async def process_promo_code(message: Message, state: FSMContext):
    lang = database.get_user_language(message.from_user.id)
    code_val = message.text.strip().upper()
    promo = database.get_promocode(code_val)
    await state.clear()
    
    if not promo:
        msg = f"❌ «{code_val}» nomli promokod topilmadi yoki muddati o'tgan." if lang == "uz" else f"❌ Промокод «{code_val}» не найден или недействителен."
        await message.answer(msg)
        return
        
    disc = f"{promo['discount_percent']}%" if promo['discount_percent'] else f"{promo['discount_amount']:,} so'm"
    msg = f"✅ <b>Promokod qabul qilindi!</b>\nChegirma: <b>{disc}</b>\nUshbu promokodni buyurtma rasmiylashtirishda qo'llashingiz mumkin." if lang == "uz" else f"✅ <b>Промокод активен!</b>\nСкидка: <b>{disc}</b>"
    await message.answer(msg, parse_mode=ParseMode.HTML)


# ─── SAVATCHA (CART) FUNKSIYALARI ────────────────────────────────

async def show_cart_message(target, user_id: int):
    lang = database.get_user_language(user_id)
    items, total = database.get_cart_items(user_id)
    
    if not items:
        if lang == "ru":
            text = "🛒 <b>Ваша корзина пуста.</b>\n\nВыберите товары из каталога и добавьте их в корзину! 🌸"
        else:
            text = "🛒 <b>Sizning savatchangiz bo'sh.</b>\n\nKatalogdan mahsulotlarni tanlab, savatchaga qo'shishingiz mumkin! 🌸"
        markup = kb.get_cart_keyboard([], lang=lang)
    else:
        tot_fmt = f"{total:,} so'm".replace(",", " ")
        if lang == "ru":
            text = "🛒 <b>ВАША КОРЗИНА:</b>\n━━━━━━━━━━━━━━━━━━━━━━\n\n"
            for idx, it in enumerate(items, 1):
                sub_fmt = f"{it['subtotal']:,} сум".replace(",", " ")
                text += f"<b>{idx}. {it['name']}</b>\n   • {it['quantity']} шт x {it['price']:,} = <b>{sub_fmt}</b>\n\n"
            text += f"━━━━━━━━━━━━━━━━━━━━━━\n💰 <b>ИТОГО К ОПЛАТЕ:</b> <b>{tot_fmt}</b>"
        else:
            text = "🛒 <b>SIZNING SAVATCHANGIZ:</b>\n━━━━━━━━━━━━━━━━━━━━━━\n\n"
            for idx, it in enumerate(items, 1):
                sub_fmt = f"{it['subtotal']:,} so'm".replace(",", " ")
                text += f"<b>{idx}. {it['name']}</b>\n   • {it['quantity']} dona x {it['price']:,} = <b>{sub_fmt}</b>\n\n"
            text += f"━━━━━━━━━━━━━━━━━━━━━━\n💰 <b>JAMI TO'LOV:</b> <b>{tot_fmt}</b>"
        markup = kb.get_cart_keyboard(items, lang=lang)

    if isinstance(target, CallbackQuery):
        try:
            await target.message.edit_text(text, reply_markup=markup, parse_mode=ParseMode.HTML)
        except Exception:
            await target.message.answer(text, reply_markup=markup, parse_mode=ParseMode.HTML)
    else:
        await target.answer(text, reply_markup=markup, parse_mode=ParseMode.HTML)


@dp.message(F.text.startswith("🛒 Savatcha") | F.text.startswith("🛒 Корзина"))
async def handle_cart_button(message: Message):
    await show_cart_message(message, message.from_user.id)


@dp.callback_query(F.data == "view_cart")
async def cb_view_cart(call: CallbackQuery):
    await show_cart_message(call, call.from_user.id)
    await call.answer()


@dp.callback_query(F.data.startswith("cart_add:"))
async def cb_cart_add(call: CallbackQuery):
    lang = database.get_user_language(call.from_user.id)
    p_id = int(call.data.split(":")[1])
    product = database.get_product(p_id)
    if not product:
        await call.answer("Mahsulot topilmadi!", show_alert=True)
        return
        
    new_count = database.add_to_cart(call.from_user.id, p_id, 1)
    msg = f"✅ «{product['name']}» savatchaga qo'shildi!" if lang == "uz" else f"✅ «{product['name']}» добавлен в корзину!"
    await call.answer(msg, show_alert=False)
    
    try:
        markup = kb.get_product_detail_keyboard(product, user_id=call.from_user.id, lang=lang)
        await call.message.edit_reply_markup(reply_markup=markup)
    except Exception:
        pass


@dp.callback_query(F.data.startswith("cart_inc:"))
async def cb_cart_inc(call: CallbackQuery):
    p_id = int(call.data.split(":")[1])
    database.add_to_cart(call.from_user.id, p_id, 1)
    await show_cart_message(call, call.from_user.id)
    await call.answer()


@dp.callback_query(F.data.startswith("cart_dec:"))
async def cb_cart_dec(call: CallbackQuery):
    p_id = int(call.data.split(":")[1])
    items, _ = database.get_cart_items(call.from_user.id)
    for it in items:
        if it["id"] == p_id:
            database.update_cart_quantity(call.from_user.id, p_id, it["quantity"] - 1)
            break
    await show_cart_message(call, call.from_user.id)
    await call.answer()


@dp.callback_query(F.data.startswith("cart_del:"))
async def cb_cart_del(call: CallbackQuery):
    p_id = int(call.data.split(":")[1])
    database.remove_from_cart(call.from_user.id, p_id)
    await show_cart_message(call, call.from_user.id)
    await call.answer()


@dp.callback_query(F.data == "cart_clear")
async def cb_cart_clear(call: CallbackQuery):
    database.clear_cart(call.from_user.id)
    await show_cart_message(call, call.from_user.id)
    await call.answer()


@dp.callback_query(F.data == "noop")
async def cb_noop(call: CallbackQuery):
    await call.answer()


# ─── 3. BUYURTMA RASMIYLASHTIRISH VA CHECKOUT ───────────────────

@dp.callback_query(F.data == "checkout_start")
async def cb_checkout_start(call: CallbackQuery, state: FSMContext):
    lang = database.get_user_language(call.from_user.id)
    items, total = database.get_cart_items(call.from_user.id)
    if not items:
        await call.answer("Savatchangiz bo'sh!", show_alert=True)
        return
        
    await state.clear()
    await state.set_state(CheckoutStates.waiting_name)
    user_name = call.from_user.first_name or "Mijoz"
    
    txt = (
        "🛍️ <b>Buyurtmani rasmiylashtirish (1/3)</b>\n\n"
        "Iltimos, qabul qiluvchining <b>ism-sharifini</b> yozing yoki pastdagi tugmani bosing:"
    ) if lang == "uz" else (
        "🛍️ <b>Оформление заказа (1/3)</b>\n\n"
        "Пожалуйста, введите <b>имя получателя</b> или нажмите кнопку ниже:"
    )
    await call.message.answer(txt, reply_markup=kb.get_confirm_name_keyboard(user_name, lang=lang), parse_mode=ParseMode.HTML)
    await call.answer()


@dp.message(CheckoutStates.waiting_name, F.text)
async def checkout_name_rec(message: Message, state: FSMContext):
    lang = database.get_user_language(message.from_user.id)
    text_val = message.text.strip()
    if text_val in ["❌ Bekor qilish", "❌ Отмена"]:
        await state.clear()
        user_is_adm = is_admin(message.from_user.id)
        await message.answer("Buyurtma bekor qilindi.", reply_markup=kb.get_main_reply_keyboard(message.from_user.id, is_admin=user_is_adm, lang=lang))
        return
        
    clean_name = text_val.replace("👤", "").strip()
    await state.update_data(customer_name=clean_name)
    await state.set_state(CheckoutStates.waiting_phone)
    
    txt = (
        f"Rahmat, <b>{clean_name}</b>!\n\n"
        "📱 <b>Buyurtmani rasmiylashtirish (2/3)</b>\n\n"
        "Bog'lanish uchun <b>telefon raqamingizni</b> yuboring:\n"
        "<i>(Quyidagi tugmani bosing yoki raqamni yozing)</i>"
    ) if lang == "uz" else (
        f"Спасибо, <b>{clean_name}</b>!\n\n"
        "📱 <b>Оформление заказа (2/3)</b>\n\n"
        "Отправьте ваш <b>номер телефона</b> для связи:"
    )
    await message.answer(txt, reply_markup=kb.get_phone_request_keyboard(lang=lang), parse_mode=ParseMode.HTML)


@dp.message(CheckoutStates.waiting_phone, F.contact)
async def checkout_phone_contact(message: Message, state: FSMContext):
    phone = message.contact.phone_number
    if not phone.startswith("+"): phone = "+" + phone
    await process_phone_step(message, state, phone)


@dp.message(CheckoutStates.waiting_phone, F.text)
async def checkout_phone_text(message: Message, state: FSMContext):
    lang = database.get_user_language(message.from_user.id)
    if message.text.strip() in ["❌ Bekor qilish", "❌ Отмена"]:
        await state.clear()
        user_is_adm = is_admin(message.from_user.id)
        await message.answer("Buyurtma bekor qilindi.", reply_markup=kb.get_main_reply_keyboard(message.from_user.id, is_admin=user_is_adm, lang=lang))
        return
    phone = message.text.strip()
    await process_phone_step(message, state, phone)


async def process_phone_step(message: Message, state: FSMContext, phone: str):
    lang = database.get_user_language(message.from_user.id)
    await state.update_data(customer_phone=phone)
    database.update_user_phone(message.from_user.id, phone)
    await state.set_state(CheckoutStates.waiting_address)
    
    txt = (
        "📍 <b>Buyurtmani rasmiylashtirish (3/3)</b>\n\n"
        "Yetkazib berish <b>manzilingizni</b> yozing yoki lokatsiyangizni yuboring:"
    ) if lang == "uz" else (
        "📍 <b>Оформление заказа (3/3)</b>\n\n"
        "Введите <b>адрес доставки</b> или отправьте локацию:"
    )
    await message.answer(txt, reply_markup=kb.get_location_request_keyboard(lang=lang), parse_mode=ParseMode.HTML)


@dp.message(CheckoutStates.waiting_address, F.location)
async def checkout_location_rec(message: Message, state: FSMContext):
    loc = message.location
    address_str = f"Telegram Lokatsiya: https://maps.google.com/?q={loc.latitude},{loc.longitude}"
    await finalize_checkout(message, state, address_str)


@dp.message(CheckoutStates.waiting_address, F.text)
async def checkout_address_text(message: Message, state: FSMContext):
    lang = database.get_user_language(message.from_user.id)
    if message.text.strip() in ["❌ Bekor qilish", "❌ Отмена"]:
        await state.clear()
        user_is_adm = is_admin(message.from_user.id)
        await message.answer("Buyurtma bekor qilindi.", reply_markup=kb.get_main_reply_keyboard(message.from_user.id, is_admin=user_is_adm, lang=lang))
        return
    address_str = message.text.strip()
    await finalize_checkout(message, state, address_str)


async def finalize_checkout(message: Message, state: FSMContext, address: str):
    lang = database.get_user_language(message.from_user.id)
    data = await state.get_data()
    customer_name = data.get("customer_name", message.from_user.full_name)
    customer_phone = data.get("customer_phone", "Ko'rsatilmadi")
    
    items, total = database.get_cart_items(message.from_user.id)
    if not items:
        await state.clear()
        user_is_adm = is_admin(message.from_user.id)
        await message.answer("Savatchangiz bo'shab qolgan!", reply_markup=kb.get_main_reply_keyboard(message.from_user.id, is_admin=user_is_adm, lang=lang))
        return
        
    # Bazada buyurtma yaratish (noyob kod bilan)
    order_code = database.create_order(
        user_id=message.from_user.id,
        customer_name=customer_name,
        customer_phone=customer_phone,
        customer_address=address,
        items=items,
        total_amount=total,
        payment_method="karta"
    )
    database.clear_cart(message.from_user.id)
    
    await state.update_data(
        order_code=order_code,
        customer_address=address,
        total_amount=total,
        items=items
    )
    await state.set_state(CheckoutStates.waiting_payment)
    
    tot_fmt = f"{total:,} so'm".replace(",", " ")
    items_summary = ""
    for idx, it in enumerate(items, 1):
        sub_fmt = f"{it['subtotal']:,} so'm".replace(",", " ")
        items_summary += f"  {idx}. {it['name']} ({it['quantity']} dona) — {sub_fmt}\n"
        
    summary_text = (
        "📋 <b>BUYURTMA MA'LUMOTLARI:</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔢 <b>Buyurtma raqami:</b> <code>#{order_code}</code>\n"
        f"👤 <b>Qabul qiluvchi:</b> {customer_name}\n"
        f"📱 <b>Telefon:</b> {customer_phone}\n"
        f"📍 <b>Manzil:</b> {address}\n\n"
        f"📦 <b>Mahsulotlar:</b>\n{items_summary}\n"
        f"💰 <b>JAMI TO'LOV:</b> <b>{tot_fmt}</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Iltimos, to'lov usulini tanlang: 👇"
    )
    await message.answer(summary_text, reply_markup=kb.get_payment_choice_keyboard(order_code, lang=lang), parse_mode=ParseMode.HTML)


# ─── TO'LOV USULLARI VA PROMOKOD QO'LLASH ─────────────────────────

@dp.callback_query(F.data.startswith("order_promo:"))
async def cb_order_promo(call: CallbackQuery, state: FSMContext):
    lang = database.get_user_language(call.from_user.id)
    order_code = call.data.split(":")[1]
    await state.update_data(order_code=order_code)
    await state.set_state(CheckoutStates.entering_promo)
    txt = "🏷️ Iltimos, promokod kiriting:" if lang == "uz" else "🏷️ Введите промокод:"
    await call.message.answer(txt)
    await call.answer()


@dp.message(CheckoutStates.entering_promo, F.text)
async def process_checkout_promo(message: Message, state: FSMContext):
    lang = database.get_user_language(message.from_user.id)
    data = await state.get_data()
    order_code = data.get("order_code")
    order = database.get_order_by_code(order_code)
    
    if not order:
        await state.clear()
        await message.answer("Buyurtma topilmadi.")
        return
        
    code_val = message.text.strip().upper()
    promo = database.get_promocode(code_val)
    
    if not promo:
        await message.answer(f"❌ «{code_val}» nomli promokod topilmadi. To'lov usulini tanlang:", reply_markup=kb.get_payment_choice_keyboard(order_code, lang=lang))
        return
        
    current_tot = order["total_amount"]
    discount = 0
    if promo["discount_percent"] > 0:
        discount = int(current_tot * promo["discount_percent"] / 100)
    elif promo["discount_amount"] > 0:
        discount = promo["discount_amount"]
        
    new_tot = max(0, current_tot - discount)
    with database.get_connection() as conn:
        conn.cursor().execute("UPDATE orders SET total_amount = ? WHERE order_code = ?", (new_tot, order_code))
        conn.commit()
        
    await state.update_data(total_amount=new_tot)
    await message.answer(
        f"✅ <b>Promokod qo'llandi!</b>\nChegirma: <b>{discount:,} so'm</b>\nYangi summa: <b>{new_tot:,} so'm</b>\n\nTo'lov usulini tanlang:",
        reply_markup=kb.get_payment_choice_keyboard(order_code, lang=lang),
        parse_mode=ParseMode.HTML
    )


@dp.callback_query(F.data.startswith("pay_card_order:"))
async def cb_pay_card_for_order(call: CallbackQuery, state: FSMContext):
    lang = database.get_user_language(call.from_user.id)
    order_code = call.data.split(":")[1]
    order = database.get_order_by_code(order_code)
    if not order:
        await call.answer("Buyurtma topilmadi!", show_alert=True)
        return
        
    await state.update_data(order_code=order_code, total_amount=order["total_amount"])
    await state.set_state(CheckoutStates.waiting_receipt)
    
    items_list = json.loads(order["items_json"]) if isinstance(order["items_json"], str) else order["items_json"]
    items_str = ""
    for it in items_list:
        items_str += f" • {it['name']} ({it['quantity']} dona)\n"
        
    await show_card_payment_info(call, order_code, order["total_amount"], items_str, lang=lang)
    await call.answer()


@dp.callback_query(F.data.startswith("pay_operator_order:"))
async def cb_pay_operator_for_order(call: CallbackQuery, state: FSMContext):
    lang = database.get_user_language(call.from_user.id)
    order_code = call.data.split(":")[1]
    order = database.get_order_by_code(order_code)
    await state.clear()
    
    if not order:
        await call.answer("Buyurtma topilmadi!", show_alert=True)
        return
        
    database.update_order_status(order_code, "qabul qilindi")
    user_is_adm = is_admin(call.from_user.id)
    
    text = (
        "✅ <b>Buyurtmangiz qabul qilindi!</b>\n\n"
        f"🔢 Buyurtma kodi: <code>#{order_code}</code>\n"
        f"Administratorimiz tez orada <b>{order['customer_phone']}</b> raqamiga bog'lanadi! 🌸"
    ) if lang == "uz" else (
        "✅ <b>Ваш заказ принят!</b>\n\n"
        f"🔢 Номер заказа: <code>#{order_code}</code>\n"
        f"Администратор свяжется с вами по номеру <b>{order['customer_phone']}</b>! 🌸"
    )
    await call.message.answer(text, reply_markup=kb.get_main_reply_keyboard(call.from_user.id, is_admin=user_is_adm, lang=lang), parse_mode=ParseMode.HTML)
    await call.answer()
    
    # Adminga yuborish
    items_list = json.loads(order["items_json"]) if isinstance(order["items_json"], str) else order["items_json"]
    items_str = ""
    for it in items_list:
        items_str += f" • {it['name']} ({it['quantity']} dona) — {it.get('price', 0):,} so'm\n"
        
    admin_text = (
        f"📲 <b>Yangi buyurtma (Administratorga ulangan)!</b>\n\n"
        f"🔢 Buyurtma: <code>#{order_code}</code>\n"
        f"👤 Mijoz: {_user_link(call.from_user)} ({order['customer_name']})\n"
        f"🆔 ID: <code>{call.from_user.id}</code>\n"
        f"📱 Telefon: <code>{order['customer_phone']}</code>\n"
        f"📍 Manzil: {order['customer_address']}\n\n"
        f"📦 <b>Mahsulotlar:</b>\n{items_str}\n"
        f"💰 <b>Jami summa:</b> {order['total_amount']:,} so'm\n"
        f"⏰ Vaqt: {_fmt_time()}\n\n"
        "<i>Mijoz bilan bog'laning!</i>"
    )
    try:
        await call.bot.send_message(ADMIN_ID, admin_text, parse_mode=ParseMode.HTML)
    except Exception as e:
        logger.error(f"Adminga xabar xatolik: {e}")


# ─── MAVJUD TEZKOR BUYURTMA (ORDER_<ID>) ─────────────────────────

@dp.callback_query(F.data.startswith("order_"))
async def cb_quick_order_start(call: CallbackQuery, state: FSMContext):
    p_id = int(call.data.replace("order_", ""))
    product = database.get_product(p_id)
    if not product:
        await call.answer("Mahsulot topilmadi!", show_alert=True)
        return
        
    price_fmt = f"{product.get('price', 0):,} so'm".replace(",", " ")
    await state.clear()
    
    order_items = [{
        "id": product["id"],
        "name": product["name"],
        "price": product["price"],
        "quantity": 1,
        "subtotal": product["price"]
    }]
    order_code = database.create_order(
        user_id=call.from_user.id,
        customer_name=call.from_user.full_name,
        customer_phone="Aniqlanmoqda",
        customer_address="Aniqlanmoqda",
        items=order_items,
        total_amount=product["price"],
        payment_method="karta"
    )
    
    await state.update_data(
        product_id=p_id,
        product_name=product["name"],
        product_price=price_fmt,
        order_code=order_code,
        total_amount=product["price"]
    )
    await state.set_state(OrderStates.choosing_payment)
    
    text = (
        f"🛍️ <b>Tezkor buyurtma: {product.get('name')}</b>\n"
        f"🔢 Buyurtma kodi: <code>#{order_code}</code>\n"
        f"💰 <b>Narxi:</b> {price_fmt}\n\n"
        "To'lov va buyurtma usulini tanlang: 👇"
    )
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Karta orqali to'lash", callback_data="pay_card")],
        [InlineKeyboardButton(text="📞 Administratorga ulash", callback_data="pay_operator")],
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="pay_cancel")]
    ])
    await call.message.answer(text, reply_markup=markup, parse_mode=ParseMode.HTML)
    await call.answer()


@dp.callback_query(OrderStates.choosing_payment, F.data == "pay_card")
async def handle_quick_pay_card(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    order_code = data.get("order_code", "ZP-000")
    total_amount = data.get("total_amount", 0)
    name = data.get("product_name", "")
    
    await state.set_state(OrderStates.waiting_receipt)
    await show_card_payment_info(call, order_code, total_amount, f" • {name} (1 dona)")
    await call.answer()


@dp.callback_query(F.data == "pay_operator")
async def handle_quick_pay_operator(call: CallbackQuery, state: FSMContext):
    lang = database.get_user_language(call.from_user.id)
    await state.set_state(OrderStates.waiting_phone)
    text = (
        "📞 <b>Administrator bilan bog'lanish:</b>\n\n"
        "Telefon raqamingizni yuboring, administratorimiz siz bilan bog'lanadi! 👇"
    )
    await call.message.answer(text, reply_markup=kb.get_phone_request_keyboard(lang=lang), parse_mode=ParseMode.HTML)
    await call.answer()


@dp.callback_query(F.data == "pay_cancel")
async def handle_pay_cancel(call: CallbackQuery, state: FSMContext):
    await state.clear()
    lang = database.get_user_language(call.from_user.id)
    user_is_adm = is_admin(call.from_user.id)
    await call.message.answer(
        "❌ Buyurtma bekor qilindi.",
        reply_markup=kb.get_main_reply_keyboard(call.from_user.id, is_admin=user_is_adm, lang=lang)
    )
    await call.answer()


@dp.message(OrderStates.waiting_phone, F.contact)
async def handle_quick_contact(message: Message, state: FSMContext, bot: Bot):
    phone = message.contact.phone_number
    await process_quick_phone(message, state, bot, phone)


@dp.message(OrderStates.waiting_phone, F.text)
async def handle_quick_phone_text(message: Message, state: FSMContext, bot: Bot):
    lang = database.get_user_language(message.from_user.id)
    if message.text.strip() in ["❌ Bekor qilish", "❌ Отмена"]:
        await state.clear()
        user_is_adm = is_admin(message.from_user.id)
        await message.answer("Buyurtma bekor qilindi.", reply_markup=kb.get_main_reply_keyboard(message.from_user.id, is_admin=user_is_adm, lang=lang))
        return
    phone = message.text.strip()
    await process_quick_phone(message, state, bot, phone)


async def process_quick_phone(message: Message, state: FSMContext, bot: Bot, phone: str):
    lang = database.get_user_language(message.from_user.id)
    data = await state.get_data()
    order_code = data.get("order_code", "ZP-000")
    name = data.get("product_name", "noma'lum")
    price = data.get("product_price", "")
    user = message.from_user
    
    database.update_order_status(order_code, "qabul qilindi")
    database.update_user_phone(user.id, phone)
    await state.clear()
    user_is_adm = is_admin(user.id)
    
    await message.answer(
        f"✅ <b>Rahmat!</b> Raqamingiz qabul qilindi. Administratorimiz tez orada siz bilan bog'lanadi! 📞",
        reply_markup=kb.get_main_reply_keyboard(user.id, is_admin=user_is_adm, lang=lang),
        parse_mode=ParseMode.HTML
    )
    
    admin_text = (
        f"📲 <b>Yangi tezkor buyurtma!</b>\n\n"
        f"🔢 Buyurtma: <code>#{order_code}</code>\n"
        f"📦 Mahsulot: {name}\n"
        f"💰 Narxi: {price}\n"
        f"👤 Mijoz: {_user_link(user)}\n"
        f"🆔 ID: <code>{user.id}</code>\n"
        f"📱 Telefon: <code>{phone}</code>\n"
        f"⏰ Vaqt: {_fmt_time()}\n\n"
        "<i>Mijozga qo'ng'iroq qiling!</i>"
    )
    try:
        await bot.send_message(ADMIN_ID, admin_text, parse_mode=ParseMode.HTML)
    except Exception as e:
        logger.error(f"Adminga tezkor buyurtma xabari bormadi: {e}")


# ─── 4. CHEK TEKSHIRUVI (RECEIPT VERIFICATION) ────────────────────

@dp.message(F.photo)
async def handle_incoming_photo(message: Message, state: FSMContext, bot: Bot):
    cur_state = await state.get_state()
    user = message.from_user
    photo = message.photo[-1]
    lang = database.get_user_language(user.id)
    user_is_adm = is_admin(user.id)
    
    # Agar admin mahsulot qo'shayotgan bo'lsa
    if cur_state == AdminAddProductStates.waiting_photo.state:
        file = await bot.get_file(photo.file_id)
        filename = f"prod_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        dest = os.path.join(IMAGES_DIR, filename)
        await bot.download_file(file.file_path, dest)
        await state.update_data(image=filename)
        await state.set_state(AdminAddProductStates.waiting_top_notes)
        await message.answer("✅ Rasm qabul qilindi!\n\nYuqori (Top) hid notalarini kiriting (yoki /skip deb yozing):")
        return

    # Chek tekshiruvi holati
    data = await state.get_data()
    order_code = data.get("order_code")
    
    if not order_code:
        user_orders = database.get_user_orders(user.id, limit=1)
        if user_orders and user_orders[0]["status"] == "kutilmoqda":
            order_code = user_orders[0]["order_code"]
            order = user_orders[0]
        else:
            order = None
    else:
        order = database.get_order_by_code(order_code)

    if not order and not cur_state:
        await message.reply(
            "🧾 <b>To'lov cheki uchun avval buyurtma bering yoki savolingiz bo'lsa administratorga yozing.</b>",
            parse_mode=ParseMode.HTML
        )
        return

    if order_code:
        database.update_order_receipt(order_code, photo.file_id)

    await state.clear()
    
    msg_client = (
        "✅ <b>To'lov cheki qabul qilindi!</b>\n\n"
        f"🔢 Buyurtma kodi: <code>#{order_code}</code>\n\n"
        "Chekingiz administrator tomonidan tekshirilmoqda. Tez orada natijasini ma'lum qilamiz! 🌸"
    ) if lang == "uz" else (
        "✅ <b>Чек об оплате принят!</b>\n\n"
        f"🔢 Номер заказа: <code>#{order_code}</code>\n\n"
        "Ваш чек проверяется администратором. Скоро придет уведомление! 🌸"
    )
    await message.answer(msg_client, reply_markup=kb.get_main_reply_keyboard(user.id, is_admin=user_is_adm, lang=lang), parse_mode=ParseMode.HTML)

    # Adminga yuborish
    cust_name = order.get("customer_name") if order else user.full_name
    cust_phone = order.get("customer_phone") if order else "Ko'rsatilmadi"
    cust_addr = order.get("customer_address") if order else "Ko'rsatilmadi"
    tot_amt = order.get("total_amount") if order else data.get("total_amount", 0)
    
    items_text = ""
    if order and order.get("items_json"):
        try:
            it_list = json.loads(order["items_json"]) if isinstance(order["items_json"], str) else order["items_json"]
            for idx, it in enumerate(it_list, 1):
                items_text += f"  {idx}. {it.get('name')} ({it.get('quantity', 1)} dona)\n"
        except Exception:
            items_text = "  • Mahsulotlar ro'yxati biriktirilgan\n"
    elif data.get("product_name"):
        items_text = f"  • {data.get('product_name')} (1 dona)\n"

    admin_caption = (
        "🧾 <b>YANGI TO'LOV CHEKI KELDI!</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔢 <b>Buyurtma raqami:</b> <code>#{order_code}</code>\n"
        f"🆔 <b>Mijoz ID:</b> <code>{user.id}</code>\n"
        f"👤 <b>Mijoz:</b> {_user_link(user)} ({cust_name})\n"
        f"📱 <b>Telefon:</b> <code>{cust_phone}</code>\n"
        f"📍 <b>Manzil:</b> {cust_addr}\n\n"
        f"📦 <b>Mahsulotlar:</b>\n{items_text}"
        f"💰 <b>To'lov summasi:</b> <b>{tot_amt:,} so'm</b>\n"
        f"⏰ <b>Vaqt:</b> {_fmt_time()}\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "<i>To'lovni tekshirib tasdiqlang yoki rad eting:</i>"
    )
    try:
        await bot.send_photo(
            chat_id=ADMIN_ID,
            photo=photo.file_id,
            caption=admin_caption,
            reply_markup=kb.get_admin_verify_keyboard(order_code),
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        logger.error(f"Adminga chek fotosi bormadi: {e}")


# ─── ADMIN CHEKNI TASDIQLASH VA HOLATLARNI BOSHQARISH ─────────────

@dp.callback_query(F.data.startswith("v_app:"))
async def cb_admin_approve(call: CallbackQuery, bot: Bot):
    order_code = call.data.split(":")[1]
    order = database.update_order_status(order_code, "qabul qilindi")
    if not order:
        await call.answer("Buyurtma topilmadi!", show_alert=True)
        return
        
    try:
        new_caption = call.message.caption + f"\n\n✅ <b>BUYURTMA QABUL QILINDI!</b>\n<i>({_fmt_time()})</i>"
        await call.message.edit_caption(
            caption=new_caption,
            reply_markup=kb.get_order_status_manage_keyboard(order_code),
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        logger.warning(f"Admin xabarini tahrirlashda: {e}")
        
    await call.answer("✅ Buyurtma qabul qilindi deb belgilandi!")
    
    # Mijozga avtomatik xabar
    client_lang = database.get_user_language(order["user_id"])
    if client_lang == "ru":
        msg = (
            "🎉 <b>ВАШ ПЛАТЕЖ И ЗАКАЗ ПРИНЯТЫ!</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🔢 Номер заказа: <code>#{order_code}</code>\n"
            f"💰 Сумма: {order['total_amount']:,} сум\n\n"
            "Чек проверен, заказ принят в обработку! 🌸"
        )
    else:
        msg = (
            "🎉 <b>TO'LOVINGIZ VA BUYURTMANGIZ QABUL QILINDI!</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🔢 Buyurtma raqami: <code>#{order_code}</code>\n"
            f"💰 Summa: {order['total_amount']:,} so'm\n\n"
            "To'lov cheki tasdiqlandi, buyurtmangiz tayyorlanmoqda! 🌸"
        )
    try:
        await bot.send_message(chat_id=order["user_id"], text=msg, parse_mode=ParseMode.HTML)
    except Exception as e:
        logger.error(f"Mijozga xabar bormadi: {e}")


@dp.callback_query(F.data.startswith("v_rej:"))
async def cb_admin_reject(call: CallbackQuery, bot: Bot):
    order_code = call.data.split(":")[1]
    order = database.update_order_status(order_code, "rad_etildi")
    if not order:
        await call.answer("Buyurtma topilmadi!", show_alert=True)
        return
        
    try:
        new_caption = call.message.caption + f"\n\n❌ <b>BUYURTMA RAD ETILDI!</b>\n<i>({_fmt_time()})</i>"
        await call.message.edit_caption(caption=new_caption, reply_markup=None, parse_mode=ParseMode.HTML)
    except Exception as e:
        logger.warning(f"Admin xabarini tahrirlashda: {e}")
        
    await call.answer("❌ Buyurtma rad etildi.")
    
    client_lang = database.get_user_language(order["user_id"])
    msg = (
        "⚠️ <b>TO'LOV CHEKI TASDIQLANMADI</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔢 Buyurtma: <code>#{order_code}</code>\n\n"
        "Chekda noaniqlik aniqlandi. Iltimos, administrator bilan bog'laning: @BaxtiyorovBehzod1"
    ) if client_lang == "uz" else (
        "⚠️ <b>ПЛАТЕЖ НЕ ПОДТВЕРЖДЕН</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔢 Заказ: <code>#{order_code}</code>\n\n"
        "Пожалуйста, свяжитесь с администратором: @BaxtiyorovBehzod1"
    )
    try:
        await bot.send_message(chat_id=order["user_id"], text=msg, parse_mode=ParseMode.HTML)
    except Exception as e:
        logger.error(f"Mijozga rad xabari bormadi: {e}")


@dp.callback_query(F.data.startswith("set_st:"))
async def cb_admin_set_status(call: CallbackQuery, bot: Bot):
    """Admin holatni 'yolda' yoki 'yetkazildi' ga o'zgartirganda mijozga avtomatik xabar borishi"""
    parts = call.data.split(":")
    order_code = parts[1]
    new_status = parts[2]
    
    order = database.update_order_status(order_code, new_status)
    if not order:
        await call.answer("Buyurtma topilmadi!", show_alert=True)
        return
        
    client_lang = database.get_user_language(order["user_id"])
    
    if new_status == "yolda":
        await call.answer("🚚 Buyurtma 'Yo'lda' holatiga o'tkazildi!")
        client_msg = (
            "🚚 <b>Xushxabar! Buyurtmangiz yo'lga chiqdi!</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🔢 Buyurtma: <code>#{order_code}</code>\n"
            "Kuryer tez orada siz bilan bog'lanadi va yetkazib beradi! 🌸"
        ) if client_lang == "uz" else (
            "🚚 <b>Отличные новости! Ваш заказ в пути!</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🔢 Заказ: <code>#{order_code}</code>\n"
            "Курьер скоро свяжется с вами и доставит посылку! 🌸"
        )
    elif new_status == "yetkazildi":
        await call.answer("✅ Buyurtma 'Yetkazildi' deb belgilandi!")
        client_msg = (
            "🎉 <b>Buyurtmangiz muvaffaqiyatli yetkazildi!</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🔢 Buyurtma: <code>#{order_code}</code>\n\n"
            "«Zaxro Parfume»ni tanlaganingiz uchun tashakkur! Xaridingiz barakasini bersin! ✨"
        ) if client_lang == "uz" else (
            "🎉 <b>Ваш заказ успешно доставлен!</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🔢 Заказ: <code>#{order_code}</code>\n\n"
            "Спасибо за покупку в «Zaxro Parfume»! ✨"
        )
    else:
        await call.answer("Holat yangilandi.")
        client_msg = f"Buyurtmangiz holati: {new_status}"
        
    try:
        await bot.send_message(chat_id=order["user_id"], text=client_msg, parse_mode=ParseMode.HTML)
    except Exception as e:
        logger.error(f"Mijozga status xabari bormadi: {e}")


# ─── 5. MENING BUYURTMALARIM ────────────────────────────────────

@dp.message(F.text.in_(["📦 Mening buyurtmalarim", "📦 Мои заказы"]))
async def handle_my_orders(message: Message):
    lang = database.get_user_language(message.from_user.id)
    orders = database.get_user_orders(message.from_user.id, limit=5)
    
    if not orders:
        txt = "Sizda hali buyurtmalar mavjud emas." if lang == "uz" else "У вас пока нет заказов."
        await message.answer(txt)
        return
        
    status_icons = {
        "kutilmoqda": "🟡 Kutilmoqda (to'lov tekshirilmoqda)",
        "qabul qilindi": "🟢 Qabul qilindi",
        "yolda": "🚚 Yo'lda",
        "yetkazildi": "✅ Yetkazildi",
        "rad_etildi": "🔴 Rad etilgan"
    }
    
    res = "📦 <b>SIZNING BUYURTMALARINGIZ:</b>\n━━━━━━━━━━━━━━━━━━━━━━\n\n"
    for ord in orders:
        st_text = status_icons.get(ord["status"], ord["status"])
        tot_fmt = f"{ord['total_amount']:,} so'm".replace(",", " ")
        res += (
            f"🔢 <b>Buyurtma:</b> <code>#{ord['order_code']}</code>\n"
            f"📅 <b>Sana:</b> {ord['created_at'][:16]}\n"
            f"💰 <b>Summa:</b> {tot_fmt}\n"
            f"📊 <b>Holati:</b> {st_text}\n"
            "──────────────────────\n"
        )
    await message.answer(res, parse_mode=ParseMode.HTML)


# ─── 6. DO'KON MA'LUMOTI VA ALOQA ───────────────────────────────

@dp.message(F.text.in_(["⏰ Ish vaqti", "⏰ Время работы"]))
async def handle_working_hours_button(message: Message):
    lang = database.get_user_language(message.from_user.id)
    await message.answer(TEXTS[lang]["working_hours_info"], parse_mode=ParseMode.HTML)


@dp.message(F.text.in_(["📞 Aloqa", "📞 Связь"]))
async def handle_contacts_button(message: Message):
    lang = database.get_user_language(message.from_user.id)
    await message.answer(
        TEXTS[lang]["contacts_info"],
        reply_markup=kb.get_contacts_inline_keyboard(lang),
        parse_mode=ParseMode.HTML
    )


@dp.message(F.text.in_(["📍 Do'kon manzili", "📍 Локация магазина"]))
async def handle_location_button(message: Message):
    lang = database.get_user_language(message.from_user.id)
    await message.answer_location(
        latitude=SHOP_INFO["latitude"],
        longitude=SHOP_INFO["longitude"]
    )
    await message.answer(TEXTS[lang]["loc_caption"], parse_mode=ParseMode.HTML)


@dp.message(F.text.in_(["ℹ️ Do'kon ma'lumotlari", "ℹ️ О магазине"]))
async def handle_shop_info_button(message: Message):
    lang = database.get_user_language(message.from_user.id)
    title = "ℹ️ <b>«Zaxro Parfume» ma'lumotlar markazi:</b>" if lang == "uz" else "ℹ️ <b>Информация о магазине «Zaxro Parfume»:</b>"
    await message.answer(title, reply_markup=kb.get_shop_info_keyboard(lang), parse_mode=ParseMode.HTML)


@dp.callback_query(F.data == "info_location")
async def cb_info_location(call: CallbackQuery):
    lang = database.get_user_language(call.from_user.id)
    await call.message.answer_location(
        latitude=SHOP_INFO["latitude"],
        longitude=SHOP_INFO["longitude"]
    )
    await call.message.answer(TEXTS[lang]["loc_caption"], parse_mode=ParseMode.HTML)
    await call.answer()


@dp.callback_query(F.data == "info_hours")
async def cb_info_hours(call: CallbackQuery):
    lang = database.get_user_language(call.from_user.id)
    await call.message.answer(TEXTS[lang]["working_hours_info"], parse_mode=ParseMode.HTML)
    await call.answer()


@dp.callback_query(F.data == "info_contacts")
async def cb_info_contacts(call: CallbackQuery):
    lang = database.get_user_language(call.from_user.id)
    await call.message.answer(
        TEXTS[lang]["contacts_info"],
        reply_markup=kb.get_contacts_inline_keyboard(lang),
        parse_mode=ParseMode.HTML
    )
    await call.answer()


@dp.callback_query(F.data == "info_delivery")
async def cb_info_delivery(call: CallbackQuery):
    lang = database.get_user_language(call.from_user.id)
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📞 " + ("Administratorga ulash" if lang == "uz" else "Связаться с администратором"), url=f"https://t.me/{SHOP_INFO['admin_username'].replace('@','')}")]
    ])
    await call.message.answer(TEXTS[lang]["delivery_info"], reply_markup=markup, parse_mode=ParseMode.HTML)
    await call.answer()


@dp.callback_query(F.data == "info_quality")
async def cb_info_quality(call: CallbackQuery):
    lang = database.get_user_language(call.from_user.id)
    await call.message.answer(TEXTS[lang]["quality_info"], parse_mode=ParseMode.HTML)
    await call.answer()


# ─── 7. ADMIN PANEL (TO'LIQ FUNKSIYALAR) ─────────────────────────

@dp.message(F.text.in_(["⚙️ Admin Panel", "⚙️ Админ панель"]))
async def handle_admin_panel_button(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.clear()
    await message.answer("⚙️ <b>Administrator Boshqaruv Paneli:</b>", reply_markup=kb.get_admin_panel_keyboard(), parse_mode=ParseMode.HTML)


# --- 7.1 Mahsulot qo'shish ---
@dp.callback_query(F.data == "adm_prod_add")
async def cb_adm_prod_add(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id): return
    await state.set_state(AdminAddProductStates.waiting_name)
    await call.message.answer("📝 <b>Yangi mahsulot nomini kiriting:</b>\n(masalan: <i>Baccarat Rouge 540</i>)", parse_mode=ParseMode.HTML)
    await call.answer()


@dp.message(AdminAddProductStates.waiting_name, F.text)
async def adm_add_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await state.set_state(AdminAddProductStates.waiting_brand)
    await message.answer("🏷️ <b>Brend nomini kiriting:</b>\n(masalan: <i>Maison Francis Kurkdjian</i> yoki <i>Tom Ford</i>)", parse_mode=ParseMode.HTML)


@dp.message(AdminAddProductStates.waiting_brand, F.text)
async def adm_add_brand(message: Message, state: FSMContext):
    await state.update_data(brand=message.text.strip())
    await state.set_state(AdminAddProductStates.waiting_gender)
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👨 Erkak", callback_data="adm_g:erkak"), InlineKeyboardButton(text="👩 Ayol", callback_data="adm_g:ayol")],
        [InlineKeyboardButton(text="👫 Uniseks", callback_data="adm_g:uniseks")]
    ])
    await message.answer("👤 <b>Jinsini tanlang:</b>", reply_markup=markup, parse_mode=ParseMode.HTML)


@dp.callback_query(AdminAddProductStates.waiting_gender, F.data.startswith("adm_g:"))
async def adm_add_gender(call: CallbackQuery, state: FSMContext):
    g = call.data.split(":")[1]
    await state.update_data(gender=g)
    await state.set_state(AdminAddProductStates.waiting_volume)
    await call.message.answer("🧪 <b>Hajmini kiriting:</b> (masalan: <i>100 ml</i> yoki <i>50 ml</i>)", parse_mode=ParseMode.HTML)
    await call.answer()


@dp.message(AdminAddProductStates.waiting_volume, F.text)
async def adm_add_volume(message: Message, state: FSMContext):
    await state.update_data(volume=message.text.strip())
    await state.set_state(AdminAddProductStates.waiting_price)
    await message.answer("💰 <b>Narxini kiriting (faqat raqamda, so'm):</b>\n(masalan: <i>450000</i>)", parse_mode=ParseMode.HTML)


@dp.message(AdminAddProductStates.waiting_price, F.text)
async def adm_add_price(message: Message, state: FSMContext):
    try:
        price = int(re.sub(r"\D", "", message.text))
    except Exception:
        await message.answer("Iltimos, narxni faqat raqamlarda kiriting (masalan: 450000):")
        return
    await state.update_data(price=price)
    await state.set_state(AdminAddProductStates.waiting_photo)
    await message.answer("📸 <b>Mahsulot rasmini yuboring</b> (yoki rasm bo'lmasa /skip deb yozing):", parse_mode=ParseMode.HTML)


@dp.message(AdminAddProductStates.waiting_photo, Command("skip"))
async def adm_skip_photo(message: Message, state: FSMContext):
    await state.update_data(image="")
    await state.set_state(AdminAddProductStates.waiting_top_notes)
    await message.answer("🌺 <b>Yuqori (Top) notalarni kiriting</b> (yoki /skip deb yozing):", parse_mode=ParseMode.HTML)


@dp.message(AdminAddProductStates.waiting_top_notes, F.text)
async def adm_add_top_notes(message: Message, state: FSMContext):
    val = "" if message.text.startswith("/skip") else message.text.strip()
    await state.update_data(top_notes=val)
    await state.set_state(AdminAddProductStates.waiting_heart_notes)
    await message.answer("🌺 <b>O'rta (Yurak) notalarini kiriting</b> (yoki /skip):", parse_mode=ParseMode.HTML)


@dp.message(AdminAddProductStates.waiting_heart_notes, F.text)
async def adm_add_heart_notes(message: Message, state: FSMContext):
    val = "" if message.text.startswith("/skip") else message.text.strip()
    await state.update_data(heart_notes=val)
    await state.set_state(AdminAddProductStates.waiting_base_notes)
    await message.answer("🌺 <b>Bazaviy (Shleyf) notalarini kiriting</b> (yoki /skip):", parse_mode=ParseMode.HTML)


@dp.message(AdminAddProductStates.waiting_base_notes, F.text)
async def adm_add_base_notes(message: Message, state: FSMContext):
    val = "" if message.text.startswith("/skip") else message.text.strip()
    await state.update_data(base_notes=val)
    await state.set_state(AdminAddProductStates.waiting_durability)
    await message.answer("⏳ <b>Turg'unligini kiriting</b> (masalan: <i>18-24 soat</i> yoki /skip):", parse_mode=ParseMode.HTML)


@dp.message(AdminAddProductStates.waiting_durability, F.text)
async def adm_add_durability(message: Message, state: FSMContext):
    val = "" if message.text.startswith("/skip") else message.text.strip()
    await state.update_data(durability=val)
    await state.set_state(AdminAddProductStates.waiting_description)
    await message.answer("📝 <b>Mahsulot tavsifini kiriting</b> (yoki /skip):", parse_mode=ParseMode.HTML)


@dp.message(AdminAddProductStates.waiting_description, F.text)
async def adm_finalize_add_product(message: Message, state: FSMContext):
    val = "" if message.text.startswith("/skip") else message.text.strip()
    data = await state.get_data()
    await state.clear()
    
    new_id = database.add_product(
        name=data.get("name", ""),
        brand=data.get("brand", ""),
        gender=data.get("gender", "uniseks"),
        volume=data.get("volume", ""),
        price=data.get("price", 0),
        image=data.get("image", ""),
        top_notes=data.get("top_notes", ""),
        heart_notes=data.get("heart_notes", ""),
        base_notes=data.get("base_notes", ""),
        durability=data.get("durability", ""),
        description=val,
        in_stock=1
    )
    consultant.reload_products()
    await message.answer(
        f"🎉 <b>Mahsulot muvaffaqiyatli qo'shildi!</b>\n\n"
        f"ID: <code>{new_id}</code>\n"
        f"Nomi: <b>{data.get('name')}</b>\n"
        f"Narxi: <b>{data.get('price'):,} so'm</b>",
        reply_markup=kb.get_admin_panel_keyboard(),
        parse_mode=ParseMode.HTML
    )


# --- 7.2 Mahsulotlar ro'yxati va boshqaruvi ---
@dp.callback_query(F.data == "adm_prod_list")
async def cb_adm_prod_list(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    products = database.get_all_products()
    if not products:
        await call.message.answer("Hozircha bazada mahsulotlar yo'q.", reply_markup=kb.get_admin_panel_keyboard())
        await call.answer()
        return
        
    kb_list = []
    for p in products[:30]:
        st = "✅" if p.get("in_stock", 1) else "❌"
        kb_list.append([InlineKeyboardButton(text=f"{st} #{p['id']} {p['name']} ({p['price']:,})", callback_data=f"adm_manage_p:{p['id']}")])
    kb_list.append([InlineKeyboardButton(text="⬅️ Admin panelga qaytish", callback_data="admin_home")])
    
    await call.message.answer("📋 <b>Boshqarish uchun mahsulotni tanlang:</b>", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_list), parse_mode=ParseMode.HTML)
    await call.answer()


@dp.callback_query(F.data == "admin_home")
async def cb_admin_home(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id): return
    await state.clear()
    await call.message.edit_text("⚙️ <b>Administrator Boshqaruv Paneli:</b>", reply_markup=kb.get_admin_panel_keyboard(), parse_mode=ParseMode.HTML)
    await call.answer()


@dp.callback_query(F.data.startswith("adm_manage_p:"))
async def cb_adm_manage_p(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    p_id = int(call.data.split(":")[1])
    product = database.get_product(p_id)
    if not product:
        await call.answer("Mahsulot topilmadi!", show_alert=True)
        return
        
    caption = format_product_caption(product, lang="uz")
    markup = kb.get_admin_product_actions_keyboard(p_id, product.get("in_stock", 1))
    await call.message.answer(caption, reply_markup=markup, parse_mode=ParseMode.HTML)
    await call.answer()


@dp.callback_query(F.data.startswith("adm_p_stock:"))
async def cb_adm_p_stock(call: CallbackQuery):
    p_id = int(call.data.split(":")[1])
    product = database.get_product(p_id)
    if product:
        new_st = 0 if product.get("in_stock", 1) else 1
        database.update_product_stock(p_id, new_st)
        consultant.reload_products()
        st_txt = "Mavjud ✅" if new_st else "Tugagan ❌"
        await call.answer(f"Mahsulot holati: {st_txt}")
        await cb_adm_prod_list(call)


@dp.callback_query(F.data.startswith("adm_p_del:"))
async def cb_adm_p_del(call: CallbackQuery):
    p_id = int(call.data.split(":")[1])
    database.delete_product(p_id)
    consultant.reload_products()
    await call.answer("Mahsulot o'chirildi!")
    await cb_adm_prod_list(call)


@dp.callback_query(F.data.startswith("adm_p_price:"))
async def cb_adm_p_price(call: CallbackQuery, state: FSMContext):
    p_id = int(call.data.split(":")[1])
    await state.update_data(product_id=p_id)
    await state.set_state(AdminEditPriceStates.waiting_price)
    await call.message.answer(f"💰 Mahsulot #{p_id} uchun yangi narxni kiriting (so'mda):")
    await call.answer()


@dp.message(AdminEditPriceStates.waiting_price, F.text)
async def adm_save_new_price(message: Message, state: FSMContext):
    data = await state.get_data()
    p_id = data.get("product_id")
    try:
        new_p = int(re.sub(r"\D", "", message.text))
        database.update_product_price(p_id, new_p)
        consultant.reload_products()
        await state.clear()
        await message.answer(f"✅ Mahsulot #{p_id} narxi {new_p:,} so'mga yangilandi!", reply_markup=kb.get_admin_panel_keyboard())
    except Exception:
        await message.answer("Iltimos, narxni faqat raqam bilan yozing:")


# --- 7.3 Aksiya & Promokod qo'shish ---
@dp.callback_query(F.data == "adm_promo_add")
async def cb_adm_promo_add(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id): return
    await state.set_state(AdminAddPromoStates.waiting_text)
    await call.message.answer("🎁 <b>Yangi aksiya matnini kiriting:</b>", parse_mode=ParseMode.HTML)
    await call.answer()


@dp.message(AdminAddPromoStates.waiting_text, F.text)
async def adm_save_promo(message: Message, state: FSMContext):
    database.add_promotion(text=message.text.strip(), title="Maxsus Aksiya")
    await state.clear()
    await message.answer("✅ Aksiya muvaffaqiyatli saqlandi va faollashtirildi!", reply_markup=kb.get_admin_panel_keyboard())


@dp.callback_query(F.data == "adm_code_add")
async def cb_adm_code_add(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id): return
    await state.set_state(AdminAddCodeStates.waiting_code)
    await call.message.answer("🏷️ <b>Yangi promokod so'zini kiriting:</b>\n(masalan: <i>ZAXRO20</i>)", parse_mode=ParseMode.HTML)
    await call.answer()


@dp.message(AdminAddCodeStates.waiting_code, F.text)
async def adm_code_name(message: Message, state: FSMContext):
    await state.update_data(code=message.text.strip().upper())
    await state.set_state(AdminAddCodeStates.waiting_discount)
    await message.answer("💰 <b>Chegirma miqdorini kiriting:</b>\nFoizda bo'lsa: <i>15%</i> deb yozing\nSo'mda bo'lsa: <i>50000</i> deb yozing")


@dp.message(AdminAddCodeStates.waiting_discount, F.text)
async def adm_code_discount(message: Message, state: FSMContext):
    data = await state.get_data()
    code = data.get("code")
    txt = message.text.strip()
    perc, amt = 0, 0
    if "%" in txt:
        perc = int(re.sub(r"\D", "", txt))
    else:
        amt = int(re.sub(r"\D", "", txt))
    database.add_promocode(code, discount_percent=perc, discount_amount=amt)
    await state.clear()
    await message.answer(f"✅ Promokod <b>{code}</b> saqlandi!", reply_markup=kb.get_admin_panel_keyboard(), parse_mode=ParseMode.HTML)


# --- 7.4 Buyurtmalar ro'yxati ---
@dp.callback_query(F.data == "adm_orders_list")
async def cb_adm_orders_list(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    orders = database.get_all_orders(limit=10)
    if not orders:
        await call.message.answer("Hozircha buyurtmalar yo'q.", reply_markup=kb.get_admin_panel_keyboard())
        await call.answer()
        return
        
    text = "📑 <b>OXIRGI BUYURTMALAR:</b>\n━━━━━━━━━━━━━━━━━━━━━━\n\n"
    for o in orders:
        text += (
            f"🔢 <code>#{o['order_code']}</code> | {o['customer_name']} ({o['customer_phone']})\n"
            f"💰 Summa: <b>{o['total_amount']:,} so'm</b> | Holati: <i>{o['status']}</i>\n"
            f"Sana: {o['created_at'][:16]}\n"
            "──────────────────────\n"
        )
    await call.message.answer(text, reply_markup=kb.get_admin_panel_keyboard(), parse_mode=ParseMode.HTML)
    await call.answer()


# --- 7.5 Statistika ---
@dp.callback_query(F.data == "adm_stats")
async def cb_adm_stats(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    stats = database.get_statistics()
    text = (
        "📊 <b>«Zaxro Parfume» BOT STATISTIKASI:</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👥 <b>Jami mijozlar:</b> {stats['total_users']} nafar\n"
        f"🆕 <b>Bugungi yangi mijozlar:</b> {stats['today_users']} nafar\n\n"
        f"📦 <b>Katalogdagi mahsulotlar:</b> {stats['products_count']} ta\n\n"
        f"📑 <b>Jami buyurtmalar:</b> {stats['total_orders']} ta\n"
        f"💰 <b>Jami tushum:</b> {stats['total_revenue']:,} so'm\n\n"
        f"📅 <b>Bugungi buyurtmalar:</b> {stats['today_orders']} ta ({stats['today_revenue']:,} so'm)\n"
        f"🗓️ <b>Shu oydagi buyurtmalar:</b> {stats['month_orders']} ta ({stats['month_revenue']:,} so'm)\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )
    await call.message.answer(text, reply_markup=kb.get_admin_panel_keyboard(), parse_mode=ParseMode.HTML)
    await call.answer()


# --- 7.6 Ommaviy xabar (Broadcast) ---
@dp.callback_query(F.data == "adm_broadcast")
async def cb_adm_broadcast(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id): return
    await state.set_state(AdminBroadcastStates.waiting_content)
    await call.message.answer("📢 <b>Barcha mijozlarga yubormoqchi bo'lgan xabaringizni yozing:</b>\n(Bekor qilish uchun /cancel deb yozing)", parse_mode=ParseMode.HTML)
    await call.answer()


@dp.message(AdminBroadcastStates.waiting_content)
async def adm_do_broadcast(message: Message, state: FSMContext, bot: Bot):
    if message.text and message.text.startswith("/cancel"):
        await state.clear()
        await message.answer("Bekor qilindi.", reply_markup=kb.get_admin_panel_keyboard())
        return
        
    await state.clear()
    users = database.get_all_users()
    count = 0
    await message.answer(f"🚀 Xabar {len(users)} ta foydalanuvchiga yuborilmoqda...")
    
    for u in users:
        try:
            await message.send_copy(chat_id=u["user_id"])
            count += 1
            await asyncio.sleep(0.05)
        except Exception:
            pass
            
    await message.answer(f"✅ Xabar muvaffaqiyatli {count} ta foydalanuvchiga yetkazildi!", reply_markup=kb.get_admin_panel_keyboard())


# --- 7.7 Bloklash / Ochish ---
@dp.callback_query(F.data == "adm_block_user")
async def cb_adm_block_user(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id): return
    await state.set_state(AdminBlockUserStates.waiting_user_id)
    await call.message.answer("🚫 <b>Foydalanuvchi Telegram ID sini kiriting:</b>", parse_mode=ParseMode.HTML)
    await call.answer()


@dp.message(AdminBlockUserStates.waiting_user_id, F.text)
async def adm_process_block(message: Message, state: FSMContext):
    await state.clear()
    try:
        uid = int(message.text.strip())
        is_bl = database.is_user_blocked(uid)
        new_bl = not is_bl
        database.set_user_blocked(uid, new_bl)
        st_txt = "bloklandi 🚫" if new_bl else "blokdan chiqarildi ✅"
        await message.answer(f"Foydalanuvchi {uid} {st_txt}!", reply_markup=kb.get_admin_panel_keyboard())
    except Exception:
        await message.answer("ID noto'g'ri kiritildi.", reply_markup=kb.get_admin_panel_keyboard())


# --- 7.8 Mijoz savoliga Administrator javob yozishi ---
@dp.callback_query(F.data.startswith("ans_ticket:"))
async def cb_ans_ticket(call: CallbackQuery, state: FSMContext):
    t_id = int(call.data.split(":")[1])
    await state.update_data(ticket_id=t_id)
    await state.set_state(AdminReplyTicketStates.waiting_reply)
    await call.message.answer(f"✍️ <b>Ticket #{t_id} uchun javobingizni yozing:</b>", parse_mode=ParseMode.HTML)
    await call.answer()


@dp.message(AdminReplyTicketStates.waiting_reply, F.text)
async def adm_send_ticket_reply(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    t_id = data.get("ticket_id")
    await state.clear()
    
    ticket = database.answer_support_ticket(t_id, message.text.strip())
    if not ticket:
        await message.answer("Ticket topilmadi.")
        return
        
    client_text = (
        "🌸 <b>ADMINISTRATOR JAVOBI:</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"❓ <b>Sizning savolingiz:</b> <i>{ticket['question_text']}</i>\n\n"
        f"💬 <b>Javob:</b>\n{message.text.strip()}\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "Savollaringiz bo'lsa bemalol yozishingiz mumkin!"
    )
    try:
        await bot.send_message(chat_id=ticket["user_id"], text=client_text, parse_mode=ParseMode.HTML)
        await message.answer("✅ Javobingiz mijozga muvaffaqiyatli yetkazildi!", reply_markup=kb.get_admin_panel_keyboard())
    except Exception as e:
        await message.answer(f"Mijozga javob yuborishda xatolik: {e}")


# ─── MATNLI XABARLAR VA AI MASLAHATCHI ───────────────────────────

@dp.message(F.text)
async def handle_user_text(message: Message, bot: Bot, state: FSMContext):
    user = message.from_user
    if database.is_user_blocked(user.id):
        return
        
    database.register_user(user.id, user.full_name, user.username)
    lang = database.get_user_language(user.id)
    
    # State mavjud bo'lsa
    cur_state = await state.get_state()
    if cur_state in [OrderStates.waiting_receipt.state, CheckoutStates.waiting_receipt.state]:
        if not message.text.startswith("/"):
            await message.answer(
                "📸 Iltimos, <b>to'lov chekini rasm (skrinshot)</b> ko'rinishida yuboring.\n"
                "Chek rasmi bo'lmasa, to'lovni tasdiqlash imkoni bo'lmaydi.",
                parse_mode=ParseMode.HTML
            )
            return

    bot_info = await bot.get_me()
    bot_username = (bot_info.username or "").lower()
    is_group = message.chat.type in ("group", "supergroup")
    user_text = message.text.strip()

    should_respond = False
    if not is_group:
        should_respond = True
    elif message.reply_to_message and message.reply_to_message.from_user.id == bot_info.id:
        should_respond = True
    elif f"@{bot_username}" in user_text.lower():
        should_respond = True
        user_text = re.sub(rf"@{bot_username}", "", user_text, flags=re.IGNORECASE).strip()

    if not should_respond:
        return

    # Karta so'ralganda
    u_low = user_text.lower()
    karta_keywords = ["karta raqam", "karta raqami", "onlayn to'lov", "onlayn tolov", "karta orqali", "pul o'tkazm", "номер карты"]
    if any(kw in u_low for kw in karta_keywords):
        dummy_order = f"ZP-{user.id % 1000 + 1000}"
        await show_card_payment_info(message, dummy_order, 0, lang=lang)
        return

    # AI Maslahatchiga yuborish
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    reply_text = await consultant.get_response(user_text, chat_id=message.chat.id, lang=lang)

    # Agar AI savolni bilmasa va [ASK_ADMIN] qaytarsa
    if "[ASK_ADMIN]" in reply_text:
        reply_text = reply_text.replace("[ASK_ADMIN]", "").strip()
        t_id = database.create_support_ticket(user.id, user_text)
        
        # Adminga yuborish
        admin_alert = (
            "📩 <b>MIJOZDAN YANGI SAVOL KELDI!</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🆔 <b>Mijoz ID:</b> <code>{user.id}</code>\n"
            f"👤 <b>Mijoz:</b> {_user_link(user)}\n"
            f"❓ <b>Savol:</b>\n<i>{user_text}</i>\n"
            f"⏰ <b>Vaqt:</b> {_fmt_time()}\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "<i>Javob yozish uchun pastdagi tugmani bosing:</i>"
        )
        try:
            await bot.send_message(ADMIN_ID, admin_alert, reply_markup=kb.get_ticket_reply_keyboard(t_id), parse_mode=ParseMode.HTML)
        except Exception as e:
            logger.error(f"Adminga ticket bormadi: {e}")

    try:
        await message.reply(reply_text, parse_mode=ParseMode.HTML)
    except Exception:
        try:
            await message.reply(reply_text, parse_mode=ParseMode.MARKDOWN)
        except Exception:
            await message.reply(reply_text)


from aiohttp import web

# ─── RENDER CLOUD HOSTING UCHUN WEB SERVER ───────────────────────

async def start_web_server():
    port = int(os.getenv("PORT", 8080))
    app = web.Application()
    async def handle_ping(request):
        return web.Response(text="Zaxro Parfume Bot 24/7 is Active! 🌸")
    app.router.add_get("/", handle_ping)
    app.router.add_get("/health", handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info(f"Render Web Server started on port {port}")


async def keep_alive_ping():
    render_url = os.getenv("RENDER_EXTERNAL_URL")
    if not render_url:
        return
    await asyncio.sleep(60)
    while True:
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(render_url) as resp:
                    logger.info(f"Keep-alive ping status: {resp.status}")
        except Exception as e:
            logger.warning(f"Keep-alive ping error: {e}")
        await asyncio.sleep(600)


# ─── MAIN ─────────────────────────────────────────────────────────

async def main():
    if not BOT_TOKEN:
        print("XATOLIK: BOT_TOKEN topilmadi!")
        sys.exit(1)

    # Render.com port talab qilsa web serverni ishga tushirish
    if os.getenv("PORT"):
        await start_web_server()
        asyncio.create_task(keep_alive_ping())

    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    info = await bot.get_me()
    print("=" * 60)
    print(f"✅ Bot ishga tushdi: @{info.username}")
    print(f"🏪 Do'kon: {SHOP_INFO['name']}")
    print(f"⏰ Ish vaqti: {SHOP_INFO['working_hours']}")
    print(f"💳 Karta: {CARD_NUMBER} ({CARD_OWNER})")
    print(f"👤 Admin: {ADMIN_USER} (ID: {ADMIN_ID})")
    print(f"📦 Katalog: Bo'sh holatda (Admin kiritishiga tayyor)")
    print("=" * 60)

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("\nBot to'xtatildi.")
