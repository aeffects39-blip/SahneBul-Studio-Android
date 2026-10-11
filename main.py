# -*- coding: utf-8 -*-
"""SahneBul İndirici (mobil) — cam + gradyan temalı Flet arayüzü.

Tüm arayüz render() içinde durumdan (state) yeniden kurulur; kırılgan özellikler
ayarla() ile tek tek atanır, böylece Flet sürümleri arasındaki küçük farklar uygulamayı çökertmez.
"""
import os
import threading
import time
import traceback

import flet as ft

import core

# ------------------------------------------------------------------ Temalar (masaüstü sürümünden)
TEMALAR = [
    dict(ad="Gece Mavisi", bg="#060a16", bg2="#0c1536", txt="#e8ecf8", mut="#8a93b2", glow="#22d3ee",
         grad=("#3b82f6", "#06b6d4", "#a855f7"), ptxt="#ffffff"),
    dict(ad="Okyanus", bg="#041018", bg2="#06304a", txt="#e6f6fb", mut="#7fa6b8", glow="#2dd4bf",
         grad=("#06b6d4", "#2dd4bf", "#3b82f6"), ptxt="#ffffff"),
    dict(ad="Ametist", bg="#0c0716", bg2="#241046", txt="#f1eafc", mut="#a595c8", glow="#e879f9",
         grad=("#7c3aed", "#c026d3", "#f472b6"), ptxt="#ffffff"),
    dict(ad="Gün Batımı", bg="#150a0c", bg2="#33132a", txt="#fdeee8", mut="#c49a9a", glow="#fb923c",
         grad=("#f97316", "#f43f5e", "#a855f7"), ptxt="#ffffff"),
    dict(ad="Zümrüt", bg="#04110d", bg2="#0a2f24", txt="#e8faf1", mut="#85b5a0", glow="#34d399",
         grad=("#059669", "#14b8a6", "#38bdf8"), ptxt="#ffffff"),
    dict(ad="Obsidyen Altın", bg="#0a0908", bg2="#241a08", txt="#f7f1e3", mut="#a89c82", glow="#fbbf24",
         grad=("#a16207", "#d9a017", "#facc15"), ptxt="#1a1205"),
]
HATA = "#ff453a"


# ------------------------------------------------------------------ Küçük yardımcılar
def a(hx, al):
    """#rrggbb + 0..1 saydamlık -> #aarrggbb"""
    return "#%02x%s" % (max(0, min(255, int(al * 255))), hx.lstrip("#"))


def ayarla(c, **kw):
    """Özellikleri tek tek ata; desteklenmeyen biri olursa atla (uygulama çökmesin)."""
    for k, v in kw.items():
        try:
            setattr(c, k, v)
        except Exception:
            pass
    return c


def kenar(w, renk):
    try:
        return ft.Border.all(w, renk)
    except Exception:
        return ft.border.all(w, renk)


def gradyan(renkler):
    try:
        return ft.LinearGradient(begin=ft.Alignment(-1, 0), end=ft.Alignment(1, 0), colors=list(renkler))
    except Exception:
        return None


def arka_gradyan(c1, c2):
    try:
        return ft.LinearGradient(begin=ft.Alignment(-1, -1), end=ft.Alignment(1, 1), colors=[c1, c2])
    except Exception:
        return None


def golge(renk, blur=22):
    try:
        return [ft.BoxShadow(spread_radius=0, blur_radius=blur, color=renk)]
    except Exception:
        return None


def ortala():
    try:
        return ft.Alignment(0, 0)
    except Exception:
        return None


def txt(metin, boyut=12, kalin=False, renk=None, **kw):
    t = ft.Text(str(metin))
    ayarla(t, size=boyut, color=renk)
    if kalin:
        ayarla(t, weight=ft.FontWeight.BOLD)
    return ayarla(t, **kw)


def kutu(icerik=None, **kw):
    c = ft.Container()
    if icerik is not None:
        c.content = icerik
    return ayarla(c, **kw)


def satir(kontroller, **kw):
    return ayarla(ft.Row(controls=list(kontroller)), **kw)


def sutun(kontroller, **kw):
    return ayarla(ft.Column(controls=list(kontroller)), **kw)


def hata_metni(ex):
    return core.temiz(ex) or "Bilinmeyen hata"


# ------------------------------------------------------------------ Uygulama
def main(page: ft.Page):
    page.title = "SahneBul İndirici"
    try:
        page.theme_mode = ft.ThemeMode.DARK
    except Exception:
        pass
    ayarla(page, padding=0)

    st = dict(tema=0, bilgi=None, tur="video", secim=0, analiz=False, mesgul=False, hata="",
              durum="Hazır", yuzde=0.0, son_up=0.0, yol=core.indirme_klasoru())
    iptal = threading.Event()

    # kalıcı kontroller (değerleri yeniden çizimde korunur)
    link = ft.TextField(label="Video linki", hint_text="https://…")
    link.expand = True
    bar = ft.ProgressBar(value=0)
    durum_txt = ft.Text("Hazır")
    kok = ft.Container()
    ayarla(kok, expand=True, padding=16)

    def T():
        return TEMALAR[st["tema"] % len(TEMALAR)]

    def guncelle():
        try:
            page.update()
        except Exception:
            pass

    # ---- bileşenler
    def cam(icerik, pad=16, r=20):
        t = T()
        return kutu(icerik, padding=pad, border_radius=r, bgcolor=a(t["txt"], 0.06),
                    border=kenar(1, a(t["txt"], 0.12)))

    def pri_btn(metin, fn, pasif=False, h=52, boyut=14):
        t = T()
        return kutu(txt(metin, boyut, True, t["ptxt"]), alignment=ortala(), height=h, border_radius=14,
                    gradient=gradyan(t["grad"]), on_click=None if pasif else fn,
                    opacity=0.45 if pasif else 1.0, shadow=None if pasif else golge(a(t["glow"], 0.35)))

    def sec_btn(metin, fn, h=40, boyut=12, renk=None):
        t = T()
        return kutu(txt(metin, boyut, True, renk or t["txt"]), alignment=ortala(), height=h, border_radius=12,
                    bgcolor=a(t["txt"], 0.08), border=kenar(1, a(renk or t["txt"], 0.18)), on_click=fn)

    def chip(metin, renk):
        return kutu(txt(metin, 9, True, renk), padding=5, border_radius=6, bgcolor=a(renk, 0.16))

    # ---- mantık
    def liste():
        b = st["bilgi"]
        return [k for k in b["kaliteler"] if k["tur"] == st["tur"]] if b else []

    def ilk_acik():
        return 0

    def tema_degistir(e=None):
        st["tema"] = (st["tema"] + 1) % len(TEMALAR)
        render()

    def tur_ata(tur):
        st.update(tur=tur)
        st["secim"] = ilk_acik()
        render()

    def kalite_sec(i):
        st.update(secim=i, hata="")
        render()

    def analiz_et(e=None):
        url = (link.value or "").strip()
        if st["analiz"] or st["mesgul"]:
            return
        if not url.lower().startswith(("http://", "https://")):
            st["hata"] = "Geçerli bir http(s) linki gir."
            return render()
        st.update(analiz=True, hata="", durum="Video bilgisi alınıyor…")
        render()

        def is_():
            try:
                b = core.analiz(url)
                st.update(bilgi=b, tur="video", yuzde=0.0, durum="Hazır — kaliteyi seç ve indir")
                st["secim"] = ilk_acik()
            except Exception as ex:
                st.update(durum="Hata", hata="Analiz başarısız: " + hata_metni(ex))
            st["analiz"] = False
            render()
        threading.Thread(target=is_, daemon=True).start()

    def ilerleme(yuzde, metin):
        simdi = time.time()
        if yuzde < 100 and simdi - st["son_up"] < 0.2:      # çok sık yenileme
            return
        st["son_up"] = simdi
        st["yuzde"] = yuzde
        bar.value = yuzde / 100
        durum_txt.value = metin
        guncelle()

    def indir(e=None):
        if st["mesgul"] or st["analiz"] or not st["bilgi"]:
            return
        ls = liste()
        if not ls:
            st["hata"] = "Bu seçim için indirilebilir format bulunamadı."
            return render()
        k = ls[min(st["secim"], len(ls) - 1)]
        iptal.clear()
        st.update(mesgul=True, hata="", yuzde=0.0, durum="İndirme başlatılıyor…")
        render()

        def is_():
            try:
                yol = core.indir(st["bilgi"]["url"], k, st["yol"], ilerleme, iptal)
                ad = (yol or "").replace("\\", "/").split("/")[-1]
                st.update(durum="Tamamlandı ✓  " + ad, yuzde=100.0)
            except core.Iptal:
                st.update(durum="İptal edildi", yuzde=0.0)
            except Exception as ex:
                st.update(durum="Hata", hata=hata_metni(ex), yuzde=0.0)
            st["mesgul"] = False
            render()
        threading.Thread(target=is_, daemon=True).start()

    # ---- kayıt yeri seçimi (Flet sürümüne göre iki farklı FilePicker API'si)
    fp = {"o": None}

    def yol_ata(p):
        try:
            os.makedirs(p, exist_ok=True)
            deneme = os.path.join(p, ".yazma_testi")
            with open(deneme, "w") as f:
                f.write("x")
            os.remove(deneme)
        except Exception as ex:
            st["hata"] = "Bu klasöre yazılamıyor: " + hata_metni(ex)
            return render()
        st.update(yol=p, hata="")
        render()

    def yol_varsayilan(e=None):
        yol_ata(core.indirme_klasoru())

    def fp_eski_sonuc(e):
        if getattr(e, "path", None):
            yol_ata(e.path)

    def fp_hazirla():
        if fp["o"] is None:
            f = ft.FilePicker()
            if hasattr(page, "services"):          # yeni Flet
                page.services.append(f)
            else:                                  # eski Flet
                page.overlay.append(f)
                f.on_result = fp_eski_sonuc
            fp["o"] = f
            guncelle()
        return fp["o"]

    async def fp_yeni_sec():
        try:
            p = await fp_hazirla().get_directory_path()
            if p:
                yol_ata(p)
        except Exception as ex:
            st["hata"] = "Klasör seçilemedi: " + hata_metni(ex)
            render()

    def klasor_sec(e=None):
        if st["mesgul"]:
            return
        try:
            f = fp_hazirla()
            if hasattr(page, "services"):
                page.run_task(fp_yeni_sec)
            else:
                f.get_directory_path()
        except Exception as ex:
            st["hata"] = "Klasör seçilemedi: " + hata_metni(ex)
            render()

    def iptal_et(e=None):
        iptal.set()
        st["durum"] = "İptal ediliyor…"
        durum_txt.value = st["durum"]
        guncelle()

    # ---- bölümler
    def bolum_ust():
        t = T()
        return satir([
            sutun([txt("SahneBul İndirici", 22, True, t["txt"]),
                   txt("Linki yapıştır · kaliteyi seç · indir", 11, False, t["mut"])], spacing=2),
            kutu(txt("◐  " + t["ad"], 11, True, t["mut"]), padding=9, border_radius=16,
                 bgcolor=a(t["glow"], 0.12), border=kenar(1, a(t["glow"], 0.4)), on_click=tema_degistir),
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.START)

    def bolum_link():
        yukleniyor = st["analiz"]
        btn = pri_btn("Analiz…" if yukleniyor else "Analiz Et", analiz_et, pasif=yukleniyor or st["mesgul"],
                      h=56, boyut=13)
        btn.width = 118
        return cam(satir([link, btn], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER), pad=12)

    def bolum_bilgi():
        t, b = T(), st["bilgi"]
        parca = [p for p in (b["kanal"], b["sure"]) if p]
        ogeler = []
        if b.get("resim"):
            im = ft.Image(src=b["resim"])
            fit = getattr(ft, "BoxFit", None) or getattr(ft, "ImageFit", None)
            ayarla(im, height=200, border_radius=14, fit=getattr(fit, "CONTAIN", None))
            ogeler.append(kutu(im, alignment=ortala(), border_radius=14, bgcolor=a("#000000", 0.25)))
        ogeler.append(txt(b["baslik"], 15, True, t["txt"], max_lines=3,
                          overflow=getattr(ft, "TextOverflow", None) and ft.TextOverflow.ELLIPSIS))
        if parca:
            ogeler.append(txt("   ·   ".join(parca), 11, False, t["mut"]))
        return cam(sutun(ogeler, spacing=10), pad=14)

    def segment(adlar, aktif, fn):
        t = T()
        ogeler = []
        for i, ad in enumerate(adlar):
            sec = i == aktif
            ogeler.append(kutu(txt(ad, 12, True, t["ptxt"] if sec else t["mut"]), alignment=ortala(), height=38,
                               border_radius=10, expand=True, gradient=gradyan(t["grad"]) if sec else None,
                               on_click=lambda e, i=i: fn(i)))
        return kutu(satir(ogeler, spacing=0), padding=3, border_radius=12, bgcolor=a(t["txt"], 0.06),
                    border=kenar(1, a(t["txt"], 0.1)))

    def kalite_karti(i, k, w):
        t = T()
        sec = i == st["secim"]
        etiket = f"{k['h']}P" if k["h"] else "M4A"
        renk = t["glow"]
        govde = sutun([
            satir([txt(k["ad"], 13, True, t["txt"], expand=True), chip(etiket, renk)],
                  vertical_alignment=ft.CrossAxisAlignment.CENTER),
            satir([txt("MP4" if k["tur"] == "video" else "M4A", 10, False, t["mut"]),
                   txt(k["boyut"] or "—", 10, True, t["glow"])], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        ], spacing=12)
        return kutu(govde, width=w, padding=14, border_radius=14,
                    bgcolor=a(t["glow"], 0.12) if sec else a(t["txt"], 0.05),
                    border=kenar(2 if sec else 1, t["glow"] if sec else a(t["txt"], 0.12)),
                    shadow=golge(a(t["glow"], 0.35), 18) if sec else None,
                    on_click=lambda e, i=i: kalite_sec(i))

    def bolum_format():
        t = T()
        pw = getattr(page, "width", None) or 360
        w = max(130, min(300, (pw - 32 - 32 - 10) / 2))
        kartlar = [kalite_karti(i, k, w) for i, k in enumerate(liste())]
        izgara = ayarla(ft.Row(controls=kartlar), wrap=True, spacing=10, run_spacing=10)
        return cam(sutun([
            txt("Kalite & Format", 14, True, t["txt"]),
            segment(["Video (MP4)", "Ses (M4A)"], 0 if st["tur"] == "video" else 1,
                    lambda i: tur_ata("video" if i == 0 else "ses")),
            izgara,
        ] + ([] if st["bilgi"].get("ffmpeg") else
             [txt("Not: ffmpeg olmadığı için yalnızca ses+görüntü birleşik formatlar iner.", 10, False, t["mut"])]),
            spacing=14), pad=16)

    def bolum_indir():
        t = T()
        metin = "↓  Sesi İndir" if st["tur"] == "ses" else "↓  Videoyu İndir"
        ogeler = [pri_btn(metin, indir, pasif=st["mesgul"] or st["analiz"])]
        if st["mesgul"]:
            ogeler.append(kutu(txt("✕  İptal", 13, True, HATA), alignment=ortala(), height=44, border_radius=12,
                               bgcolor=a(HATA, 0.12), border=kenar(1, a(HATA, 0.5)), on_click=iptal_et))
        return sutun(ogeler, spacing=10)

    def bolum_durum():
        t = T()
        ayarla(bar, color=t["glow"], bgcolor=a(t["txt"], 0.1), value=st["yuzde"] / 100,
               visible=st["mesgul"] or st["yuzde"] > 0)
        ayarla(durum_txt, value=st["durum"], color=t["mut"], size=11)
        return sutun([bar, durum_txt], spacing=6)

    def bolum_yol():
        t = T()
        return cam(sutun([
            txt("KAYIT YERİ", 10, True, t["glow"]),
            txt(st["yol"], 12, False, t["txt"], selectable=True),
            satir([sec_btn("Klasör seç", klasor_sec, h=38, boyut=11),
                   sec_btn("Varsayılan", yol_varsayilan, h=38, boyut=11, renk=t["mut"])], spacing=8),
        ], spacing=8), pad=14, r=16)

    def bolum_hata():
        return cam(txt(st["hata"], 12, False, HATA), pad=12, r=14)

    def render():
        t = T()
        try:
            ayarla(link, color=t["txt"], border_color=a(t["txt"], 0.25), focused_border_color=t["glow"],
                   bgcolor=a(t["txt"], 0.05), filled=True, border_radius=14, cursor_color=t["glow"])
            ayarla(link, label_style=ft.TextStyle(color=t["mut"]))
            bolumler = [bolum_ust(), bolum_link()]
            if st["hata"]:
                bolumler.append(bolum_hata())
            if st["bilgi"]:
                bolumler += [bolum_bilgi(), bolum_format(), bolum_indir()]
            else:
                bolumler.append(kutu(txt("Bir video linki yapıştır, “Analiz Et”e bas.", 12, False, t["mut"]),
                                     alignment=ortala(), padding=30))
            bolumler.append(bolum_durum())
            bolumler.append(bolum_yol())
            kolon = sutun(bolumler, spacing=14)
            ayarla(kolon, scroll=ft.ScrollMode.AUTO, expand=True)
            kok.content = kolon
            kok.gradient = arka_gradyan(t["bg"], t["bg2"])
            ayarla(page, bgcolor=t["bg"])
        except Exception:
            kok.content = ft.Text("Arayüz hatası:\n" + traceback.format_exc()[-900:], selectable=True)
        guncelle()

    try:
        page.on_resize = lambda e: render()
    except Exception:
        pass
    link.on_submit = analiz_et

    try:
        page.add(ft.SafeArea(content=kok, expand=True))
    except Exception:
        page.add(kok)
    render()


if __name__ == "__main__":
    (getattr(ft, "run", None) or ft.app)(main)
