# HamyonAPI — Pitch Deck (HTML slaydlar)

`hamyon-api.uz` uchun to'liq investor/startup pitch taqdimoti: **20 ta slayd**, bitta HTML fayl,
soft-UI (neumorphik) uslubda, to'q ko'k + och ko'k palitra.

## Ochish

```bash
cd pitch
python3 -m http.server 8000 --bind 0.0.0.0     # http://localhost:8000
```

yoki shunchaki `pitch/index.html` faylni brauzerda oching (hech qanday build kerak emas).

## Boshqaruv

| Tugma | Vazifa |
|---|---|
| `→` / `Space` / `PageDown` | keyingi slayd |
| `←` / `Backspace` | oldingi slayd |
| `Home` / `End` | birinchi / oxirgi slayd |
| `F` | butun ekran (fullscreen) |
| `P` | chop etish oynasi → **PDF** (`Save as PDF`, landscape, A4) |
| svayp / g'ildirak | sensorli ekran va trackpad uchun |

Har bir slayd `#slayd-N` havolasiga ega — aniq slaydni ulshish mumkin
(`http://localhost:8000/#slayd-10`).

## Slaydlar tartibi

1. Muqova (cover + asosiy raqamlar)
2. **Muammo** — to'lovni qo'lda qabul qilish, 4 og'riq nuqtasi
3. **Yechim** — bitta API, kuzatuv bizda, webhook orqali natija
4. Qanday ishlaydi — 4 qadam + real kod va API javobi
5. Imkoniyatlar — 8 ta qobiq funksiyasi
6. Premium statistika — 5 000 so'mlik add-on tahlili
7. Xavfsizlik — read-only model, imzo, idempotentlik, antifraud
8. Bozor — O'zbekiston raqamli iqtisodiyoti (6 ta tasdiqli ko'rsatkich)
9. **TAM / SAM / SOM** — SVG konsentrik diagramma + ikki yo'llik hisob-kitob
10. Raqobat — 6 ta yechim bilan solishtirish jadvali
11. **Narxlar** — bepul sinov · 15 000 so'm/oy · 5 000 so'm premium statistika
12. Traction — nima allaqachon ishlayapti + 90 kunlik maqsadlar
13. Unit ekonomika — ARPU, CAC, LTV, LTV/CAC 17,7×, breakeven 2 050 mijoz
14. Moliyaviy prognoz — 12 chorak MRR diagrammasi + 3 ssenariy
15. GTM — kanallar, konversiya funnelsi, 12 oylik KPI
16. Roadmap — 2026 Q1 → 2027 Q1+
17. Risklar va ularni boshqarish (tartibga solish, platformaga bog'liqlik, churn…)
18. **Jamoa** — Hamitjonov Ruslan, Founder · CEO
19. Investitsiya so'rovi — 600 mln so'm, mablag' taqsimoti donut diagrammasi
20. Yopilish + aloqa

## Texnik jihatlar

- **Fayllar:** `index.html` (bitta fayl, ~98 KB) + `assets/*.jpg` (9 ta rasm, jami ~700 KB).
- **Responsiv:** 1600×900 dizayn kanvosi `transform: scale()` bilan ekranga moslashadi.
- **Auto-fit:** JS har bir slaydning tabiiy balandligini o'lchaydi va 900 px dan oshib ketsa,
  slaydni avtomatik kichraytiradi — matn hech qachon kesilmaydi.
- **Raqamlar:** bozor ko'rsatkichlari KPMG, Statista Digital Commerce, ECDB va ochiq soha
  hisobotlaridan olingan; bozor sig'imi (55 000 segment, ARPU, prognoz) — taqdimot uchun
  bizning bahomiz. Hisob-kitoblar 1 $ ≈ 12 800 so'm kursida.
- **Chop etish:** `@media print` har bir slaydni alohida sahifaga chiqaradi — PDF olish oson.

## O'zgartirish

Butun uslub `:root` o'zgaruvchilarida:

```css
--navy-900:#050f22;  /* to'q ko'k fon   */
--sky:#7cc0ff;       /* och ko'k aksent */
--shadow-out: …      /* soft UI soyalar */
```

Matn va raqamlar `index.html` ichida oddiy HTML — slayd qo'shish uchun
`<section class="slide" data-title="Nomi"> … </section>` blokini ko'paytiring,
Navigatsiya (nuqtalar, hisoblagich, progress) avtomatik yangilanadi.
