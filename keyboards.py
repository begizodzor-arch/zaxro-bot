# -*- coding: utf-8 -*-
from typing import List, Optional
from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove
)
import database
from shop_info import SHOP_INFO


# ─── TIL TANLASH ────────────────────────────────────────────────

def get_language_keyboard() -> InlineKeyboardMarkup:
    kb = [
        [
            InlineKeyboardButton(text="🇺🇿 O'zbekcha", callback_data="set_lang:uz"),
            InlineKeyboardButton(text="🇷🇺 Русский", callback_data="set_lang:ru")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)


# ─── ASOSIY REPLY MENYU ─────────────────────────────────────────

def get_main_reply_keyboard(user_id: int = 0, is_admin: bool = False, lang: str = "uz") -> ReplyKeyboardMarkup:
    cart_count = database.get_cart_count(user_id) if user_id else 0
    
    if lang == "ru":
        cart_label = f"🛒 Корзина ({cart_count})" if cart_count > 0 else "🛒 Корзина"
        kb = [
            [KeyboardButton(text="🌸 Каталог"), KeyboardButton(text=cart_label)],
            [KeyboardButton(text="📦 Мои заказы"), KeyboardButton(text="🎁 Акции и скидки")],
            [KeyboardButton(text="⏰ Время работы"), KeyboardButton(text="📞 Связь")],
            [KeyboardButton(text="📍 Локация магазина"), KeyboardButton(text="🌐 Сменить язык")]
        ]
        if is_admin:
            kb.append([KeyboardButton(text="⚙️ Админ панель")])
    else:
        cart_label = f"🛒 Savatcha ({cart_count})" if cart_count > 0 else "🛒 Savatcha"
        kb = [
            [KeyboardButton(text="🌸 Katalog"), KeyboardButton(text=cart_label)],
            [KeyboardButton(text="📦 Mening buyurtmalarim"), KeyboardButton(text="🎁 Aksiya va Chegirmalar")],
            [KeyboardButton(text="⏰ Ish vaqti"), KeyboardButton(text="📞 Aloqa")],
            [KeyboardButton(text="📍 Do'kon manzili"), KeyboardButton(text="🌐 Tilni o'zgartirish")]
        ]
        if is_admin:
            kb.append([KeyboardButton(text="⚙️ Admin Panel")])

    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


def get_contacts_inline_keyboard(lang: str = "uz") -> InlineKeyboardMarkup:
    admin_btn = "👤 Administrator" if lang == "uz" else "👤 Администратор"
    channel_btn = "📢 Telegram kanal" if lang == "uz" else "📢 Telegram канал"
    insta_btn = "📸 Instagram"
    
    kb = [
        [InlineKeyboardButton(text=channel_btn, url=SHOP_INFO["channel_link"])],
        [InlineKeyboardButton(text=insta_btn, url=SHOP_INFO["instagram"])],
        [InlineKeyboardButton(text=admin_btn, url=f"https://t.me/{SHOP_INFO['admin_username'].replace('@','')}")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)


# ─── KATALOG VA BO'SH KATALOG ────────────────────────────────────

def get_empty_catalog_keyboard(lang: str = "uz") -> InlineKeyboardMarkup:
    btn_text = "📞 Administratorga bog'lanish" if lang == "uz" else "📞 Связаться с администратором"
    back_text = "⬅️ Bosh menyu" if lang == "uz" else "⬅️ Главное меню"
    kb = [
        [InlineKeyboardButton(text=btn_text, url=f"https://t.me/{SHOP_INFO['admin_username'].replace('@','')}")],
        [InlineKeyboardButton(text=back_text, callback_data="back_main")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)


def get_catalog_menu_keyboard(lang: str = "uz") -> InlineKeyboardMarkup:
    if lang == "ru":
        kb = [
            [InlineKeyboardButton(text="✨ Все товары", callback_data="filter_all")],
            [
                InlineKeyboardButton(text="🏷️ По брендам", callback_data="filter_brand_menu"),
                InlineKeyboardButton(text="👤 По полу", callback_data="filter_gender_menu")
            ],
            [InlineKeyboardButton(text="💰 По цене", callback_data="filter_price_menu")],
            [InlineKeyboardButton(text="⬅️ Главное меню", callback_data="back_main")]
        ]
    else:
        kb = [
            [InlineKeyboardButton(text="✨ Barcha atirlar", callback_data="filter_all")],
            [
                InlineKeyboardButton(text="🏷️ Brend bo'yicha", callback_data="filter_brand_menu"),
                InlineKeyboardButton(text="👤 Jins bo'yicha", callback_data="filter_gender_menu")
            ],
            [InlineKeyboardButton(text="💰 Narx bo'yicha", callback_data="filter_price_menu")],
            [InlineKeyboardButton(text="⬅️ Bosh menyu", callback_data="back_main")]
        ]
    return InlineKeyboardMarkup(inline_keyboard=kb)


def get_brands_keyboard(lang: str = "uz") -> InlineKeyboardMarkup:
    brands = database.get_distinct_brands()
    kb = []
    row = []
    for b in brands:
        row.append(InlineKeyboardButton(text=f"💎 {b}", callback_data=f"f_brand:{b[:25]}"))
        if len(row) == 2:
            kb.append(row)
            row = []
    if row:
        kb.append(row)
        
    all_text = "🌈 Barcha brendlar" if lang == "uz" else "🌈 Все бренды"
    back_text = "⬅️ Katalog menyusi" if lang == "uz" else "⬅️ Меню каталога"
    kb.append([InlineKeyboardButton(text=all_text, callback_data="filter_all")])
    kb.append([InlineKeyboardButton(text=back_text, callback_data="catalog_home")])
    return InlineKeyboardMarkup(inline_keyboard=kb)


def get_gender_keyboard(lang: str = "uz") -> InlineKeyboardMarkup:
    if lang == "ru":
        kb = [
            [
                InlineKeyboardButton(text="👨 Мужские", callback_data="f_gender:erkak"),
                InlineKeyboardButton(text="👩 Женские", callback_data="f_gender:ayol")
            ],
            [InlineKeyboardButton(text="👫 Унисекс", callback_data="f_gender:uniseks")],
            [
                InlineKeyboardButton(text="🌈 Все", callback_data="filter_all"),
                InlineKeyboardButton(text="⬅️ Назад", callback_data="catalog_home")
            ]
        ]
    else:
        kb = [
            [
                InlineKeyboardButton(text="👨 Erkaklar uchun", callback_data="f_gender:erkak"),
                InlineKeyboardButton(text="👩 Ayollar uchun", callback_data="f_gender:ayol")
            ],
            [InlineKeyboardButton(text="👫 Uniseks", callback_data="f_gender:uniseks")],
            [
                InlineKeyboardButton(text="🌈 Barchasi", callback_data="filter_all"),
                InlineKeyboardButton(text="⬅️ Orqaga", callback_data="catalog_home")
            ]
        ]
    return InlineKeyboardMarkup(inline_keyboard=kb)


def get_price_filter_keyboard(lang: str = "uz") -> InlineKeyboardMarkup:
    if lang == "ru":
        kb = [
            [InlineKeyboardButton(text="💵 До 300 000 сум", callback_data="f_price:0:300000")],
            [InlineKeyboardButton(text="💵 300 000 — 500 000 сум", callback_data="f_price:300000:500000")],
            [InlineKeyboardButton(text="💵 Свыше 500 000 сум", callback_data="f_price:500000:9999999")],
            [
                InlineKeyboardButton(text="🌈 Любая цена", callback_data="filter_all"),
                InlineKeyboardButton(text="⬅️ Назад", callback_data="catalog_home")
            ]
        ]
    else:
        kb = [
            [InlineKeyboardButton(text="💵 300 000 so'mgacha", callback_data="f_price:0:300000")],
            [InlineKeyboardButton(text="💵 300 000 — 500 000 so'm", callback_data="f_price:300000:500000")],
            [InlineKeyboardButton(text="💵 500 000 so'mdan yuqori", callback_data="f_price:500000:9999999")],
            [
                InlineKeyboardButton(text="🌈 Barcha narxlar", callback_data="filter_all"),
                InlineKeyboardButton(text="⬅️ Orqaga", callback_data="catalog_home")
            ]
        ]
    return InlineKeyboardMarkup(inline_keyboard=kb)


def get_products_list_keyboard(products: List[dict], lang: str = "uz") -> InlineKeyboardMarkup:
    kb = []
    for p in products:
        stock_mark = "✅" if p.get("in_stock", 1) else "❌"
        price_fmt = f"{p.get('price', 0):,} so'm".replace(",", " ")
        title = f"{stock_mark} {p.get('name')} — {price_fmt}"
        if len(title) > 55:
            title = title[:52] + "..."
        kb.append([InlineKeyboardButton(text=title, callback_data=f"prod:{p['id']}")])
        
    other_text = "🔍 Boshqa filtrlar" if lang == "uz" else "🔍 Другие фильтры"
    back_text = "⬅️ Bosh menyu" if lang == "uz" else "⬅️ Главное меню"
    kb.append([InlineKeyboardButton(text=other_text, callback_data="catalog_home")])
    kb.append([InlineKeyboardButton(text=back_text, callback_data="back_main")])
    return InlineKeyboardMarkup(inline_keyboard=kb)


def get_product_detail_keyboard(product: dict, user_id: int = 0, lang: str = "uz") -> InlineKeyboardMarkup:
    p_id = product["id"]
    in_stock = bool(product.get("in_stock", 1))
    
    kb = []
    if in_stock:
        add_text = "🛒 Savatchaga qo'shish" if lang == "uz" else "🛒 Добавить в корзину"
        order_text = "🛍️ Tezkor buyurtma berish" if lang == "uz" else "🛍️ Быстрый заказ"
        kb.append([InlineKeyboardButton(text=add_text, callback_data=f"cart_add:{p_id}")])
        kb.append([InlineKeyboardButton(text=order_text, callback_data=f"order_{p_id}")])
    else:
        req_text = "💬 Buyurtma asosida so'rash" if lang == "uz" else "💬 Спросить под заказ"
        kb.append([InlineKeyboardButton(text=req_text, url=f"https://t.me/{SHOP_INFO['admin_username'].replace('@','')}")])
        
    cart_count = database.get_cart_count(user_id) if user_id else 0
    if cart_count > 0:
        cart_view = f"🛒 Savatchaga o'tish ({cart_count})" if lang == "uz" else f"🛒 Перейти в корзину ({cart_count})"
        kb.append([InlineKeyboardButton(text=cart_view, callback_data="view_cart")])
        
    cat_back = "⬅️ Katalogga qaytish" if lang == "uz" else "⬅️ В каталог"
    home_back = "🏠 Bosh menyu" if lang == "uz" else "🏠 Главное меню"
    kb.append([
        InlineKeyboardButton(text=cat_back, callback_data="catalog_home"),
        InlineKeyboardButton(text=home_back, callback_data="back_main")
    ])
    return InlineKeyboardMarkup(inline_keyboard=kb)


# ─── SAVATCHA KLAVIATURASI ──────────────────────────────────────

def get_cart_keyboard(cart_items: List[dict], lang: str = "uz") -> InlineKeyboardMarkup:
    kb = []
    dona_text = "dona" if lang == "uz" else "шт"
    for item in cart_items:
        p_id = item["id"]
        p_name = item["name"][:18]
        qty = item["quantity"]
        kb.append([
            InlineKeyboardButton(text=f"❌ {p_name}", callback_data=f"cart_del:{p_id}"),
            InlineKeyboardButton(text="➖", callback_data=f"cart_dec:{p_id}"),
            InlineKeyboardButton(text=f"{qty} {dona_text}", callback_data="noop"),
            InlineKeyboardButton(text="➕", callback_data=f"cart_inc:{p_id}")
        ])
        
    if cart_items:
        checkout_txt = "🛍️ Buyurtma rasmiylashtirish" if lang == "uz" else "🛍️ Оформить заказ"
        clear_txt = "🗑️ Savatchani tozalash" if lang == "uz" else "🗑️ Очистить корзину"
        cat_txt = "🌸 Katalogga qaytish" if lang == "uz" else "🌸 В каталог"
        kb.append([InlineKeyboardButton(text=checkout_txt, callback_data="checkout_start")])
        kb.append([
            InlineKeyboardButton(text=clear_txt, callback_data="cart_clear"),
            InlineKeyboardButton(text=cat_txt, callback_data="catalog_home")
        ])
    else:
        cat_txt = "🌸 Katalogga o'tish" if lang == "uz" else "🌸 Перейти в каталог"
        kb.append([InlineKeyboardButton(text=cat_txt, callback_data="catalog_home")])
        
    back_txt = "⬅️ Bosh menyu" if lang == "uz" else "⬅️ Главное меню"
    kb.append([InlineKeyboardButton(text=back_txt, callback_data="back_main")])
    return InlineKeyboardMarkup(inline_keyboard=kb)


# ─── BUYURTMA RASMIYLASHTIRISH VA TO'LOV ─────────────────────────

def get_confirm_name_keyboard(user_name: str, lang: str = "uz") -> ReplyKeyboardMarkup:
    cancel_txt = "❌ Bekor qilish" if lang == "uz" else "❌ Отмена"
    kb = [
        [KeyboardButton(text=f"👤 {user_name}")],
        [KeyboardButton(text=cancel_txt)]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True, one_time_keyboard=True)


def get_phone_request_keyboard(lang: str = "uz") -> ReplyKeyboardMarkup:
    btn_txt = "📱 Telefon raqamimni yuborish" if lang == "uz" else "📱 Отправить мой номер"
    cancel_txt = "❌ Bekor qilish" if lang == "uz" else "❌ Отмена"
    kb = [
        [KeyboardButton(text=btn_txt, request_contact=True)],
        [KeyboardButton(text=cancel_txt)]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True, one_time_keyboard=True)


def get_location_request_keyboard(lang: str = "uz") -> ReplyKeyboardMarkup:
    btn_txt = "📍 Lokatsiyamni yuborish" if lang == "uz" else "📍 Отправить локацию"
    cancel_txt = "❌ Bekor qilish" if lang == "uz" else "❌ Отмена"
    kb = [
        [KeyboardButton(text=btn_txt, request_location=True)],
        [KeyboardButton(text=cancel_txt)]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True, one_time_keyboard=True)


def get_payment_choice_keyboard(order_code: str, lang: str = "uz") -> InlineKeyboardMarkup:
    card_txt = "💳 Karta orqali to'lash" if lang == "uz" else "💳 Оплата картой"
    oper_txt = "📞 Administratorga ulash" if lang == "uz" else "📞 Связаться с администратором"
    promo_txt = "🏷️ Promokod kiritish" if lang == "uz" else "🏷️ Ввести промокод"
    cancel_txt = "❌ Buyurtmani bekor qilish" if lang == "uz" else "❌ Отменить заказ"
    
    kb = [
        [InlineKeyboardButton(text=card_txt, callback_data=f"pay_card_order:{order_code}")],
        [InlineKeyboardButton(text=oper_txt, callback_data=f"pay_operator_order:{order_code}")],
        [InlineKeyboardButton(text=promo_txt, callback_data=f"order_promo:{order_code}")],
        [InlineKeyboardButton(text=cancel_txt, callback_data="pay_cancel")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)


# ─── CHEK TEKSHIRUVI VA ADMIN STATUS TUGMALARI ──────────────────

def get_admin_verify_keyboard(order_code: str) -> InlineKeyboardMarkup:
    kb = [
        [
            InlineKeyboardButton(text="✅ Tasdiqlash (Qabul qilindi)", callback_data=f"v_app:{order_code}"),
            InlineKeyboardButton(text="❌ Rad etish", callback_data=f"v_rej:{order_code}")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)


def get_order_status_manage_keyboard(order_code: str) -> InlineKeyboardMarkup:
    """Admin buyurtma holatini bosqichma-bosqich o'zgartirishi uchun"""
    kb = [
        [InlineKeyboardButton(text="🚚 Yo'lga chiqarish (Yo'lda)", callback_data=f"set_st:{order_code}:yolda")],
        [InlineKeyboardButton(text="✅ Yetkazildi deb belgilash", callback_data=f"set_st:{order_code}:yetkazildi")],
        [InlineKeyboardButton(text="❌ Rad etish", callback_data=f"set_st:{order_code}:rad_etildi")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)


# ─── DO'KON MA'LUMOTLARI VA ALOQA MENYUSI ───────────────────────

def get_shop_info_keyboard(lang: str = "uz") -> InlineKeyboardMarkup:
    if lang == "ru":
        kb = [
            [InlineKeyboardButton(text="📍 Локация магазина (Google Maps)", callback_data="info_location")],
            [
                InlineKeyboardButton(text="⏰ Время работы", callback_data="info_hours"),
                InlineKeyboardButton(text="📞 Связь и канал", callback_data="info_contacts")
            ],
            [
                InlineKeyboardButton(text="🚚 Условия доставки", callback_data="info_delivery"),
                InlineKeyboardButton(text="💎 Качество продукции", callback_data="info_quality")
            ],
            [InlineKeyboardButton(text="⬅️ Главное меню", callback_data="back_main")]
        ]
    else:
        kb = [
            [InlineKeyboardButton(text="📍 Do'kon manzili (Google Maps / Lokatsiya)", callback_data="info_location")],
            [
                InlineKeyboardButton(text="⏰ Ish vaqti", callback_data="info_hours"),
                InlineKeyboardButton(text="📞 Aloqa va kanal", callback_data="info_contacts")
            ],
            [
                InlineKeyboardButton(text="🚚 Yetkazib berish shartlari", callback_data="info_delivery"),
                InlineKeyboardButton(text="💎 Mahsulot sifati", callback_data="info_quality")
            ],
            [InlineKeyboardButton(text="⬅️ Bosh menyu", callback_data="back_main")]
        ]
    return InlineKeyboardMarkup(inline_keyboard=kb)


# ─── AKSIYA VA CHEGIRMALAR ──────────────────────────────────────

def get_promos_keyboard(lang: str = "uz") -> InlineKeyboardMarkup:
    admin_btn = "📞 Administratorga bog'lanish" if lang == "uz" else "📞 Связаться с администратором"
    back_btn = "⬅️ Bosh menyu" if lang == "uz" else "⬅️ Главное меню"
    kb = [
        [InlineKeyboardButton(text="🏷️ Promokod tekshirish", callback_data="enter_promo_code")],
        [InlineKeyboardButton(text=admin_btn, url=f"https://t.me/{SHOP_INFO['admin_username'].replace('@','')}")],
        [InlineKeyboardButton(text=back_btn, callback_data="back_main")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)


# ─── ADMIN PANEL KLAVIATURALARI ─────────────────────────────────

def get_admin_panel_keyboard() -> InlineKeyboardMarkup:
    kb = [
        [
            InlineKeyboardButton(text="📦 Mahsulot qo'shish", callback_data="adm_prod_add"),
            InlineKeyboardButton(text="📋 Mahsulotlar ro'yxati", callback_data="adm_prod_list")
        ],
        [
            InlineKeyboardButton(text="🎁 Aksiya qo'shish", callback_data="adm_promo_add"),
            InlineKeyboardButton(text="🏷️ Promokod qo'shish", callback_data="adm_code_add")
        ],
        [
            InlineKeyboardButton(text="📑 Buyurtmalar ro'yxati", callback_data="adm_orders_list"),
            InlineKeyboardButton(text="📊 Statistika", callback_data="adm_stats")
        ],
        [
            InlineKeyboardButton(text="📢 Ommaviy xabar (Broadcast)", callback_data="adm_broadcast"),
            InlineKeyboardButton(text="🚫 Bloklash / Ochish", callback_data="adm_block_user")
        ],
        [
            InlineKeyboardButton(text="⬅️ Bosh menyuga qaytish", callback_data="back_main")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)


def get_admin_product_actions_keyboard(product_id: int, in_stock: int) -> InlineKeyboardMarkup:
    stock_text = "❌ Tugadi deb belgilash" if in_stock else "✅ Mavjud deb belgilash"
    kb = [
        [
            InlineKeyboardButton(text="✏️ Narxini o'zgartirish", callback_data=f"adm_p_price:{product_id}"),
            InlineKeyboardButton(text=stock_text, callback_data=f"adm_p_stock:{product_id}")
        ],
        [
            InlineKeyboardButton(text="🗑️ Mahsulotni o'chirish", callback_data=f"adm_p_del:{product_id}")
        ],
        [
            InlineKeyboardButton(text="⬅️ Mahsulotlar ro'yxatiga qaytish", callback_data="adm_prod_list")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)


def get_ticket_reply_keyboard(ticket_id: int) -> InlineKeyboardMarkup:
    kb = [
        [InlineKeyboardButton(text="✍️ Javob berish", callback_data=f"ans_ticket:{ticket_id}")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)
