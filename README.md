# @VinexUzBot — Telegram xizmatlar boti

To'liq ishlab chiqarishga tayyor bot: **Stars, Premium, NFT, Gift, postga stars
(paid reaction), raqam olish (Server 1 + Server 2), referal, balans, murojaat,
buyurtmalar va to'liq Admin panel.**

- **Til:** Python 3.11
- **Bot:** aiogram 3 (async)
- **Baza:** MySQL (aiomysql)
- **Hisoblar / to'lov aniqlash / reaction / gift:** Telethon 1.44
- **Fragment API:** fragment-api.net (v1 `buyStarsWithoutKYC` / `buyPremiumWithoutKYC`, v2 ham qo'llab-quvvatlanadi)
- **Server 1 raqamlar:** spider-service.com
- **Server 2 raqamlar:** admin qo'shgan sessiyali hisoblar

---

## 1. O'rnatish

```bash
cd /home/user/bot

# 1) Virtual muhit
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2) .env faylini sozlash (.env allaqachon tayyor — tekshiring)
cp .env.example .env
nano .env
```

### .env parametrlari

| O'zgaruvchi | Tavsif |
|---|---|
| `BOT_TOKEN` | BotFather'dan olingan token |
| `ADMIN_IDS` | Adminlar (vergul bilan) |
| `TG_API_ID` / `TG_API_HASH` | my.telegram.org — Telethon uchun |
| `DB_HOST/PORT/USER/PASSWORD/NAME` | MySQL ma'lumotlari |

### MySQL

```sql
CREATE DATABASE uzvendor_bot CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

*Baza birinchi ishga tushirishda avtomatik yaratiladi hamda barcha jadvallar
hamda standart sozlamalar o'zi qo'shiladi.*

### Ishga tushirish

```bash
source .venv/bin/activate
python3 main.py
```

---

## 2. Birinchi sozlash (Admin panel)

Botda `6155982488` (yoki `ADMIN_IDS`dagi) user `/start` → **Admin Panel** ochadi.

### 2.1 Fragment API (Stars/Premium)

1. fragment.com da TON wallet ulangan, KYC'dan o'tgan hisob kerak.
2. `Tosh seed` (24 so'z) oling — `Admin → Sozlamalar → Fragment API → ✏️ seed`.
   Bot o'zi **base64** qilib yuboradi.
3. Ixtiyoriy KYC: `fragment_cookies` (base64) kiriting.
4. V2 ishlatmoqchi bo'lsangiz: `/v2/auth` orqali auth_key oling va `✏️ auth_key` ga kiriting,
   keyin **Rejim: V2** tugmasini bosing.

> Narxlar `Admin → Xizmatlar → Stars/Premium...` da sozlanadi.

### 2.2 To'lov kartalari va to'lov aniqlash

1. `Admin → Moliya → Kartalar → Karta qo'shish` (UZCARD/HUMO raqami + egasi).
2. `Admin → Hisoblar → UZCARD to'lov / HUMO to'lov → Hisob qo'shish`.

   Hisob qo'shish: telefon raqam → Telegram'dan kelgan login kod → (2FA bo'lsa parol) → nom.
   Sessiya fayli avtomatik saqlanadi (`sessions/` papkada).

3. `Admin → Xizmatlar → Payment watcher` — yoqilgan bo'lishi kerak.

Watcher har bir hisob bilan `CardXabarBot` (UZCARD) / `HumocardBot` (HUMO) xabarlarini
o'qiydi: `➕ 50 000 UZS` ko'rinishidagi xabarlar kutilayotgan depozit bilan
(**)summa** + ixtiyoriy **oxirgi 4 raqam**) solishtirilib, mos kelsa balans avtomatik
to'ldiriladi va foydalanuvchiga xabar boradi. Bir xil xabar ikki marta hisoblanmaydi.

Agar avtomatik aniqlash ishlamasa, `Admin → Moliya → Depozitlar` da qo'lda
tasdiqlash mumkin.

### 2.3 Gift

1. `Admin → Hisoblar → Gift → Hisob qo'shish` (gift yuboradigan hisob, stars balansi bo'lishi kerak).
2. `Admin → Xizmatlar → Gift sozlamalari`:
   - **Gift ID** — yuboriladigan star-gift ID (Telegram'da gift sifatida mavjud bo'lishi kerak)
   - Narx va nom.

Gift `payments.GetPaymentForm + SendStarsForm` orqali hisob stars balansidan yuboriladi.

### 2.4 Postga stars (paid reaction)

1. `Admin → Hisoblar → Reaksiya → Hisob qo'shish`.
2. Reaksiya hisobi post joylashgan kanal a'zosi bo'lishi kerak (yopiq kanal bo'lsa — albatta).
3. `messages.SendPaidReaction` orqali star transfer qilinadi (Telethon 1.44).

Post havolasi: `https://t.me/kanal/123` yoki yopiq kanal uchun `https://t.me/c/ID/123`.

### 2.5 Raqam olish — Server 1 (Spider)

1. `@S_PIDERRBot` → API Key → Show Key — kalitni oling.
2. `Admin → Sozlamalar → Spider API → API key` ga kiriting.
3. `Admin → Raqamlar → Server 1 → Davlatlarni yangilash` (davlatlar keladi).
4. Har bir davlat narxini kiriting uting (bosing → narx yozish).
5. Yoqish/o'chirish ham shu yerdan.

Foydalanuvchi: Raqam → Server 1 → davlat → sotib olish → raqamni oladi,
"Kodni olish" tugmasi bilan SMS kodni cheksiz (xizmat ruxsatigacha) olishi mumkin.

> Spider javob formatlari (`status/number/hash_code`) turli versiyalarda farq qilishi
> mumkin — `bot/utils/spider.py` ichida `_pick()` ko'p variantlarni o'qiydi;
> boshqa format bo'lsa shu funksiyaga kalit qo'shilsa kifoya.

### 2.6 Raqam olish — Server 2 (hisoblar)

1. `Admin → Raqamlar → Server 2 → Raqam qo'shish`:
   telefon → parol (2FA, ixtiyoriy) → narx → davlat (UZ) → izoh.
2. Raqamni tanlang → **Sessiya faylini yuklash** (dokument sifatida `.session`).
   Yoki hisobni bot orqali kirib sessiya yaratish uchun:
   `Admin → Hisoblar` → turini tanlang, ammo Server 2 raqamlari uchun
   `.session` faylni yuklash qulayroq.
3. Sotuvda bo'lgan raqamlarni foydalanuvchi ko'radi; sotib olgach, bot raqam + parol +
   sessiya faylini yuboradi.

`Admin → Raqamlar → Server 2` da barcha stat: sotilgan/sotuvda, xaridor, buyurtma raqami.

### 2.7 NFT

Fragment'da NFT (username/anonym raqam) xaridi alohida jarayon bo'lgani uchun:
foydalanuvchi buyurtma bajaradi (balansdan yechiladi) → `Admin → Buyurtmalar` da
NFT buyurtma → **Bajarildi (natija yozish)** → natija foydalanuvchiga avtomatik yuboriladi.
Bekor qilsangiz — pul avtomatik qaytariladi.

### 2.8 Referal va boshqa sozlamalar

- `Admin → Xizmatlar → Referal`: foiz (xaridning `%` i refererga tushadi).
- `Admin → Sozlamalar`: salomlashuv, FAQ, kanal, e'lon, emojilar, Fragment/Spider.
- `Admin → Hisobot`: bugun / 7 kun / oy / hammasi — xizmatlar kesimida va top xaridorlar.
- `Admin → Reklama`: barcha foydalanuvchilarga xabar.
- `Admin → Murojaatlar`: javob berish (foydalanuvchiga yuboriladi).

### 2.9 Custom emojilar

Tugma matnlarida Unicode emojilar ishlatiladi (Bot API tugmalarda custom emoji
entitiyesini qo'llab-quvvatlamaydi). **Xabar matnlarida** esa haqiqiy custom emoji
ishlatish mumkin:

`Admin → Sozlamalar → Emojilar` → masalan `star` → haqiqiy custom emoji **document_id**
ni kiriting (premium akkauntdan emojini yuborib ID olinadi, yoki @CustomEmojiBot).
Kalitlar: `star, premium, nft, gift, fire, phone, money, wallet, ref, support,
admin, orders, back, check, cross, warn, info, card, bank, server, code, gear,
history, bolt` (yalpi ro'yxat `bot/emoji.py`).

---

## 3. Struktura

```
main.py                  — ishga tushirish (bot + watcher)
config.py                — .env sozlamalari
db.py                    — MySQL pool + sxema + so'rovlar
sessions/                — Telethon sessiya fayllari (gitignore)
bot/
  emoji.py               — custom emoji dvigateli
  keyboards.py           — foydalanuvchi klaviaturalari
  texts.py               — pullar/vaqt/username yordamchilari
  states.py              — FSM holatlar
  middlewares.py         — ro'yxatga olish + ban
  services/
    wallet.py            — balans/trx/referal (transaksiyalar)
    orders.py            — barcha xizmat buyurtmalari
  utils/
    fragment.py          — fragment-api.net (v1 + v2)
    spider.py            — spider-service.com
    tg_client.py         — Telethon sesiya menejeri
    tg_actions.py        — paid reaction + star gift
    watcher.py           — CardXabarBot/HumocardBot to'lov aniqlash
  handlers/
    base.py services.py numbers.py wallet.py orders.py support.py
    admin/               — to'liq admin panel (9 bo'lim)
tests/smoke_test.py      — DB'siz biznes-logika testlari
```

## 4. Xizmat sifatida ishga tushirish (systemd)

```ini
# /etc/systemd/system/uzvendor-bot.service
[Unit]
Description=VinexUzBot
After=network.target mysql.service

[Service]
User=root
WorkingDirectory=/home/user/bot
ExecStart=/home/user/bot/.venv/bin/python main.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
systemctl daemon-reload
systemctl enable --now uzvendor-bot
systemctl status uzvendor-bot
journalctl -u uzvendor-bot -f
```

## 5. Muhim eslatmalar

- **Fragment API kalit/seed kiritsangiz — ular DB `settings` jadvalida saqlanadi;**
  `.env`ga ham yozib qo'yishingiz mumkin (admin panel qiymati ustun).
- `API ID/HASH` foydalanuvchi bergan (`23031437` / `5e9d16...`) — faqat ularga
  tegishli hisoblar uchun ishlaydi, boshqa hisob qo'shishda muammo bo'lsa,
  my.telegram.org dan o'zingiznikini oling.
- Server 2 sessiya faylini yuborish — faqat fayl mavjud bo'lsa; aks holda
  faqat raqam+parol beriladi.
- To'lov watcher hisob **CardXabarBot/HumocardBot ga yozilgan bo'lishi shart** — aks holda
  xabarlar kelmaydi (botga start berish kifoya).
- Barcha narxlar, matnlar va tugmalar panel orqali o'zgartiriladi — kodga tegish shart emas.
