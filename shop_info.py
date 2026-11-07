# -*- coding: utf-8 -*-
"""
«Zaxro Parfume» do'koni rasmiy ma'lumotlari
"""

SHOP_INFO = {
    "name": "Zaxro Parfume",
    "working_hours": "09:00 dan 21:00 gacha",
    "phone": "+998 99 484 19 81",
    "channel_link": "https://t.me/zaxro_parfume",
    "instagram": "https://www.instagram.com/zaxro.parfume",
    "admin_username": "@BaxtiyorovBehzod1",
    "admin_id": 6158301754,
    "card_number": "6262 5707 1622 6610",
    "card_owner": "Baxtiyorov Behzodbek",
    "latitude": 41.244314,
    "longitude": 71.527516,
    "maps_url": "https://www.google.com/maps?q=41.244314,71.527516",
}

# Ko'p tilli do'kon ma'lumotlari
TEXTS = {
    "uz": {
        "delivery_info": (
            "🚚 <b>Yetkazib berish:</b>\n\n"
            "Yetkazib berish narxi va muddati manzilga qarab administrator bilan kelishiladi.\n\n"
            "Aniqroq ma'lumot olish uchun administratorimizga murojaat qilishingiz mumkin."
        ),
        "quality_info": (
            "💎 <b>Mahsulot sifati:</b>\n\n"
            "Do'konimizdagi mahsulotlarning ko'pchiligi <b>sifatli 1:1 nusxa (kopiya)</b> hisoblanadi.\n"
            "Biz mijozlarimizga doimo to'g'ri va halol ma'lumot beramiz! ✨"
        ),
        "working_hours_info": (
            f"⏰ <b>«{SHOP_INFO['name']}» do'koni ish vaqti:</b>\n\n"
            f"Har kuni <b>{SHOP_INFO['working_hours']}</b>\n"
            "Dam olish kunlarisiz xizmatingizdamiz! 🌸"
        ),
        "contacts_info": (
            "📞 <b>ALOQA VA IJTIMOIY TARMOQLAR:</b>\n\n"
            f"🏪 <b>Do'kon nomi:</b> {SHOP_INFO['name']}\n"
            f"⏰ <b>Ish vaqti:</b> {SHOP_INFO['working_hours']}\n"
            f"📱 <b>Telefon:</b> {SHOP_INFO['phone']}\n"
            f"📢 <b>Telegram kanal:</b> {SHOP_INFO['channel_link']}\n"
            f"📸 <b>Instagram:</b> {SHOP_INFO['instagram']}\n"
            f"👤 <b>Administrator:</b> {SHOP_INFO['admin_username']}\n\n"
            "<i>Ijtimoiy tarmoqlarimizga ulanish uchun quyidagi tugmalarni bosing: 👇</i>"
        ),
        "empty_catalog": (
            "📦 <b>Katalog tez orada to'ldiriladi.</b>\n\n"
            "Savolingiz bo'lsa yozing yoki administratorga ulanamiz! 🌸"
        ),
        "empty_promos": (
            "🎁 <b>Hozircha aksiyalar yo'q, yangi aksiyalar bo'lsa xabar beramiz!</b> 🌸"
        ),
        "connect_admin_btn": "📞 Administratorga bog'lanish",
        "loc_caption": (
            f"📍 <b>«{SHOP_INFO['name']}» do'koni lokatsiyasi</b>\n"
            f"⏰ Ish vaqti: {SHOP_INFO['working_hours']}\n"
            f"🗺️ <a href=\"{SHOP_INFO['maps_url']}\">Google Maps orqali ochish</a>"
        )
    },
    "ru": {
        "delivery_info": (
            "🚚 <b>Доставка:</b>\n\n"
            "Стоимость и сроки доставки согласовываются с администратором в зависимости от адреса.\n\n"
            "Для точной информации вы можете связаться с нашим администратором."
        ),
        "quality_info": (
            "💎 <b>Качество продукции:</b>\n\n"
            "Большинство товаров в нашем магазине — это <b>качественные копии 1:1</b>.\n"
            "Мы всегда предоставляем честную информацию нашим клиентам! ✨"
        ),
        "working_hours_info": (
            f"⏰ <b>Время работы магазина «{SHOP_INFO['name']}»:</b>\n\n"
            f"Ежедневно с <b>{SHOP_INFO['working_hours']}</b>\n"
            "Работаем без выходных! 🌸"
        ),
        "contacts_info": (
            "📞 <b>КОНТАКТЫ И СОЦИАЛЬНЫЕ СЕТИ:</b>\n\n"
            f"🏪 <b>Магазин:</b> {SHOP_INFO['name']}\n"
            f"⏰ <b>Время работы:</b> {SHOP_INFO['working_hours']}\n"
            f"📱 <b>Телефон:</b> {SHOP_INFO['phone']}\n"
            f"📢 <b>Telegram канал:</b> {SHOP_INFO['channel_link']}\n"
            f"📸 <b>Instagram:</b> {SHOP_INFO['instagram']}\n"
            f"👤 <b>Администратор:</b> {SHOP_INFO['admin_username']}\n\n"
            "<i>Для перехода нажмите на кнопки ниже: 👇</i>"
        ),
        "empty_catalog": (
            "📦 <b>Каталог скоро будет заполнен.</b>\n\n"
            "Если у вас есть вопросы, напишите или мы свяжем вас с администратором! 🌸"
        ),
        "empty_promos": (
            "🎁 <b>На данный момент акций нет, мы сообщим, как только появятся новые!</b> 🌸"
        ),
        "connect_admin_btn": "📞 Связаться с администратором",
        "loc_caption": (
            f"📍 <b>Локация магазина «{SHOP_INFO['name']}»</b>\n"
            f"⏰ Время работы: {SHOP_INFO['working_hours']}\n"
            f"🗺️ <a href=\"{SHOP_INFO['maps_url']}\">Открыть в Google Maps</a>"
        )
    }
}
