# -*- coding: utf-8 -*-
import asyncio
import json
import logging
import os
from typing import Optional, Dict, List
from shop_info import SHOP_INFO

logger = logging.getLogger("AIConsultant")

USE_MODERN_GENAI = False
try:
    from google import genai
    from google.genai import types as genai_types
    USE_MODERN_GENAI = True
except ImportError:
    pass


class AIConsultant:
    def __init__(
        self,
        catalog_path: str,
        gemini_api_key: Optional[str] = None,
        admin_phone: str = "+998 99 484 19 81",
        admin_username: str = "@BaxtiyorovBehzod1",
        channel_link: str = "https://t.me/zaxro_parfume"
    ):
        self.catalog_path = catalog_path
        self.gemini_api_key = gemini_api_key
        self.admin_phone = admin_phone
        self.admin_username = admin_username
        self.channel_link = channel_link
        self.products = self._load_products()
        self.client = None
        self.chat_history: Dict[int, List[dict]] = {}

        if self.gemini_api_key and USE_MODERN_GENAI:
            try:
                self.client = genai.Client(api_key=self.gemini_api_key)
                logger.info("Google GenAI client muvaffaqiyatli ishga tushirildi.")
            except Exception as e:
                logger.error(f"GenAI Client ishga tushirishda xatolik: {e}")

    def _load_products(self) -> list:
        try:
            if os.path.exists(self.catalog_path):
                with open(self.catalog_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            return []
        except Exception as e:
            logger.error(f"Katalog yuklashda xatolik: {e}")
            return []

    def reload_products(self):
        self.products = self._load_products()

    def _build_system_instruction(self, lang: str = "uz") -> str:
        products_summary = []
        for p in self.products:
            name = p.get('name')
            brand = p.get('brand', '')
            price = f"{p.get('price', 0):,} so'm".replace(",", " ")
            gender = p.get('gender', 'uniseks')
            stock = "Mavjud" if p.get('in_stock', 1) else "Tugagan"
            volume = p.get('volume', '')
            durability = p.get('durability', '')
            top = p.get('top_notes', '')
            heart = p.get('heart_notes', '')
            base = p.get('base_notes', '')
            desc = p.get('description', '')

            details = [f"Brend: {brand}", f"Jins: {gender}", f"Holat: {stock}"]
            if volume: details.append(f"Hajm: {volume}")
            if durability: details.append(f"Turg'unlik: {durability}")
            if top: details.append(f"Yuqori: {top}")
            if heart: details.append(f"O'rta: {heart}")
            if base: details.append(f"Baza: {base}")
            if desc: details.append(desc)

            info = f"- [ID: {p.get('id')}] {name} ({brand}) | Narxi: {price} | " + " | ".join(details)
            products_summary.append(info)

        catalog_text = "\n".join(products_summary) if products_summary else "Hozirda katalog bo'sh. Administrator tomonidan yangi tovarlar kiritilmoqda."

        return f"""
Siz «Zaxro Parfume» do'konining samimiy, xushmuomala, halol va tushunuvchi aqlli maslahatchisisiz.
Mijoz qaysi tilda yozsa (o'zbek yoki rus), shu tilda samimiy, qisqa va aniq javob bering.

DO'KON MA'LUMOTLARI:
- Do'kon nomi: {SHOP_INFO['name']}
- Ish vaqti: {SHOP_INFO['working_hours']}
- Telefon: {self.admin_phone}
- Telegram kanal: {self.channel_link}
- Administrator: {self.admin_username}
- Lokatsiya koordinatalari: {SHOP_INFO['latitude']}, {SHOP_INFO['longitude']}
- Google Maps: {SHOP_INFO['maps_url']}

KATALOGDAGI MAHSULOTLAR:
{catalog_text}

QAT'IY QOIDALAR (BU QOIDALARNI HECH QACHON BUZMANG):
1. MAHSULOT SIFATI HAQIDA:
   - Do'kondagi mahsulotlarning ko'pchiligi 1 ga 1 nusxa (kopiya).
   - HECH QACHON "original" deb yozmang va mijozga "original" deb va'da bermang!
   - Agar mijoz sifat haqida, originalmi deb so'rasa, halol va ochiq javob bering: "Do'konimizdagi mahsulotlar sifatli 1:1 nusxa (kopiya) hisoblanadi."
2. YETKAZIB BERISH:
   - Narx yoki muddatni o'zingizdan to'qimang!
   - Mijoz yetkazib berish (narxi, muddati) haqida so'rasa: "Yetkazib berish narxi va muddati manzilga qarab administrator bilan kelishiladi." deb javob bering.
3. ALMASHTIRISH VA QAYTARISH:
   - Almashtirish va qaytarish shartlari haqida so'ralsa: "Bu masala bo'yicha administratorimiz bilan bog'lanishingizni tavsiya qilamiz: {self.admin_username}" deb ayting.
4. KATALOG BO'SH BO'LSA:
   - Agar katalogda mahsulotlar bo'lmasa yoki mijoz katalog haqida so'rasa: "Katalog tez orada to'ldiriladi. Savolingiz bo'lsa yozing yoki administratorga ulanamiz: {self.admin_username}" deb ayting.
5. BILMAGAN SAVOLLAR:
   - Bilmagan narsangizni aslo o'ylab topmang!
   - Agar aniq javobni bilmasangiz, muloyimlik bilan: "Bu savolga administratorimiz javob beradi. Savolingiz administratorga yetkazildi, tez orada javob beramiz 🌸" deb ayting va javobingiz oxiriga [ASK_ADMIN] belgisini qo'ying!
6. BUYURTMA VA KARTA:
   - Mijoz buyurtma berishni istasa, "Marhamat, buyurtmani rasmiylashtirish uchun quyidagi tugmalardan foydalaning yoki administratorga murojaat qiling" deng va [ORDER] qo'shing.
   - Karta so'ralsa [PAY_CARD] qo'shing.
"""

    def _fallback_search(self, query: str, lang: str = "uz") -> str:
        q = query.lower()

        # Sifat / original haqida
        if any(w in q for w in ["original", "orijinal", "nusxa", "kopiya", "copy", "poddelka", "haqiqiy", "sifat"]):
            if lang == "ru":
                return (
                    "💎 <b>Качество продукции:</b>\n\n"
                    "Большинство товаров в нашем магазине — это <b>качественные копии 1:1</b>.\n"
                    "Мы всегда открыты и честны с нашими клиентами! ✨"
                )
            return (
                "💎 <b>Mahsulot sifati:</b>\n\n"
                "Do'konimizdagi mahsulotlarning ko'pchiligi <b>sifatli 1:1 nusxa (kopiya)</b> hisoblanadi.\n"
                "Biz mijozlarimizga doimo to'g'ri va halol ma'lumot beramiz! ✨"
            )

        # Yetkazib berish
        if any(w in q for w in ["yetkaz", "dostavka", "dostawka", "pochta", "kuryer", "qancha kunda", "narxi qancha"]):
            if lang == "ru":
                return (
                    "🚚 <b>Доставка:</b>\n\n"
                    "Стоимость и сроки доставки согласовываются с администратором в зависимости от адреса.\n\n"
                    f"Связаться: {self.admin_username}"
                )
            return (
                "🚚 <b>Yetkazib berish:</b>\n\n"
                "Yetkazib berish narxi va muddati manzilga qarab administrator bilan kelishiladi.\n\n"
                f"Bog'lanish: {self.admin_username}"
            )

        # Qaytarish va almashtirish
        if any(w in q for w in ["qaytar", "almashtir", "vozvrat", "obmen"]):
            if lang == "ru":
                return f"По вопросам обмена и возврата, пожалуйста, обратитесь к нашему администратору: {self.admin_username}"
            return f"Almashtirish va qaytarish bo'yicha administratorimizga murojaat qilishingizni so'raymiz: {self.admin_username}"

        # Manzil / Ish vaqti
        if any(w in q for w in ["manzil", "adres", "qayerda", "lokatsiya", "ish vaqti", "gde", "vremya", "grafik"]):
            if lang == "ru":
                return (
                    f"🏪 <b>{SHOP_INFO['name']}</b>\n"
                    f"⏰ Время работы: {SHOP_INFO['working_hours']}\n"
                    f"📱 Телефон: {self.admin_phone}\n"
                    f"🗺️ Google Maps: {SHOP_INFO['maps_url']}"
                )
            return (
                f"🏪 <b>{SHOP_INFO['name']}</b>\n"
                f"⏰ Ish vaqti: {SHOP_INFO['working_hours']}\n"
                f"📱 Telefon: {self.admin_phone}\n"
                f"🗺️ Google Maps: {SHOP_INFO['maps_url']}"
            )

        # Aksiya haqida
        if any(w in q for w in ["aksiya", "chegirma", "skidka", "aksiyalar", "promokod"]):
            if lang == "ru":
                return "🎁 На данный момент акций нет, мы сообщим, как только появятся новые! 🌸"
            return "🎁 Hozircha aksiyalar yo'q, yangi aksiyalar bo'lsa xabar beramiz! 🌸"

        # Katalog haqida
        if not self.products:
            if lang == "ru":
                return f"📦 Каталог скоро будет заполнен. Если у вас есть вопросы, напишите или мы свяжем вас с администратором: {self.admin_username} 🌸"
            return f"📦 Katalog tez orada to'ldiriladi. Savolingiz bo'lsa yozing yoki administratorga ulanamiz: {self.admin_username} 🌸"

        # Mahsulot qidirish
        matched = []
        for p in self.products:
            p_name = p.get("name", "").lower()
            p_brand = p.get("brand", "").lower()
            words = [w for w in q.split() if len(w) > 2]
            if any(w in p_name or w in p_brand for w in words):
                matched.append(p)

        if matched:
            resp = "🌸 <b>«Zaxro Parfume» mahsulotlari:</b>\n\n"
            for p in matched[:3]:
                price = f"{p.get('price', 0):,} so'm".replace(",", " ")
                stock = "✅ Mavjud" if p.get("in_stock", 1) else "❌ Tugagan"
                resp += f"✨ <b>{p.get('name')}</b> ({p.get('brand', '')})\n"
                resp += f"💰 Narxi: <b>{price}</b> | {stock}\n\n"
            return resp

        # Bilmagan savol bo'lsa adminga yo'naltirish
        if lang == "ru":
            return f"Bu savolga administratorimiz javob beradi. Savolingiz qabul qilindi 🌸\n[ASK_ADMIN]"
        return f"Bu savolga administratorimiz javob beradi. Savolingiz qabul qilindi 🌸\n[ASK_ADMIN]"

    async def get_response(self, user_text: str, chat_id: int = 0, lang: str = "uz") -> str:
        if not self.gemini_api_key or not self.client:
            return self._fallback_search(user_text, lang)

        if chat_id not in self.chat_history:
            self.chat_history[chat_id] = []

        history = self.chat_history[chat_id]
        prompt_with_history = ""
        is_first_message = len(history) == 0

        if not is_first_message:
            prompt_with_history += "Oldingi suhbat:\n"
            for turn in history[-4:]:
                role_label = "Mijoz" if turn["role"] == "user" else "Maslahatchi"
                prompt_with_history += f"{role_label}: {turn['text']}\n"
            prompt_with_history += f"\nHozirgi yangi savol:\nMijoz: {user_text}\nMaslahatchi javobi:"
        else:
            prompt_with_history += f"Mijoz: {user_text}\nMaslahatchi javobi:"

        for model_cand in ["gemini-3.1-flash-lite", "gemini-3.5-flash-lite"]:
            try:
                response = await asyncio.wait_for(
                    self.client.aio.models.generate_content(
                        model=model_cand,
                        contents=prompt_with_history,
                        config=genai_types.GenerateContentConfig(
                            system_instruction=self._build_system_instruction(lang=lang),
                            temperature=0.5
                        )
                    ),
                    timeout=8.0
                )
                if response and response.text:
                    bot_reply = response.text.strip()
                    history.append({"role": "user", "text": user_text})
                    history.append({"role": "model", "text": bot_reply})
                    if len(history) > 8:
                        self.chat_history[chat_id] = history[-8:]
                    return bot_reply
            except Exception as e:
                logger.warning(f"GenAI xatoligi ({model_cand}): {e}")
                continue

        return self._fallback_search(user_text, lang)
