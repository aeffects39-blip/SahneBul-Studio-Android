# -*- coding: utf-8 -*-
"""SahneBul İndirici (mobil) — Flet arayüzü."""
import threading

import flet as ft

import core


def main(page: ft.Page):
    page.title = "SahneBul İndirici"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 16
    page.scroll = ft.ScrollMode.AUTO

    durum = {"bilgi": None, "secim": 0, "iptal": threading.Event(), "mesgul": False}

    link = ft.TextField(label="Video linki", hint_text="https://…", expand=True)
    analiz_btn = ft.ElevatedButton("Analiz")
    resim = ft.Image(width=320, border_radius=12, visible=False)
    baslik = ft.Text(size=16, weight=ft.FontWeight.BOLD)
    kanal = ft.Text(size=12, opacity=0.7)
    kaliteler = ft.Column(spacing=6)
    indir_btn = ft.FilledButton("İndir", visible=False)
    iptal_btn = ft.OutlinedButton("İptal", visible=False)
    bar = ft.ProgressBar(value=0, visible=False)
    durum_txt = ft.Text("Hazır", size=12, opacity=0.7)

    def mesaj(m):
        page.snack_bar = ft.SnackBar(ft.Text(m))
        page.snack_bar.open = True
        page.update()

    def kalite_ciz():
        kaliteler.controls.clear()
        for i, k in enumerate(durum["bilgi"]["kaliteler"]):
            secili = i == durum["secim"]
            kaliteler.controls.append(ft.Container(
                content=ft.Row([ft.Text(k["ad"], weight=ft.FontWeight.BOLD, expand=True),
                                ft.Text(k["boyut"], size=12, opacity=0.7)]),
                padding=12, border_radius=12,
                bgcolor=ft.Colors.with_opacity(0.18 if secili else 0.06, ft.Colors.CYAN),
                border=ft.border.all(2 if secili else 1, ft.Colors.CYAN if secili else ft.Colors.WHITE24),
                on_click=lambda e, i=i: sec(i)))
        page.update()

    def sec(i):
        durum["secim"] = i
        kalite_ciz()

    def analiz_et(e):
        url = link.value.strip()
        if not url.lower().startswith(("http://", "https://")):
            return mesaj("Geçerli bir http(s) linki gir.")
        analiz_btn.disabled = True
        durum_txt.value = "Analiz ediliyor…"
        page.update()

        def is_():
            try:
                b = core.analiz(url)
                durum.update(bilgi=b, secim=0)
                baslik.value, kanal.value = b["baslik"], f"{b['kanal']}  ·  {b['sure']}"
                resim.src, resim.visible = b["resim"], bool(b["resim"])
                indir_btn.visible = True
                durum_txt.value = "Kaliteyi seç ve indir"
                kalite_ciz()
            except Exception as ex:
                durum_txt.value = "Hata"
                mesaj("Analiz başarısız: " + str(ex)[:150])
            analiz_btn.disabled = False
            page.update()
        threading.Thread(target=is_, daemon=True).start()

    def ilerleme(yuzde, metin):
        bar.value = yuzde / 100
        durum_txt.value = metin
        page.update()

    def indir(e):
        if durum["mesgul"] or not durum["bilgi"]:
            return
        k = durum["bilgi"]["kaliteler"][durum["secim"]]
        durum.update(mesgul=True)
        durum["iptal"].clear()
        indir_btn.disabled, iptal_btn.visible, bar.visible = True, True, True
        bar.value = 0
        page.update()

        def is_():
            try:
                yol = core.indir(durum["bilgi"]["url"], k, core.indirme_klasoru(), ilerleme, durum["iptal"])
                mesaj("İndirildi: " + (yol.split("/")[-1] if yol else "tamam"))
            except core.Iptal:
                durum_txt.value = "İptal edildi"
            except Exception as ex:
                durum_txt.value = "Hata"
                mesaj(str(ex)[:200])
            durum["mesgul"] = False
            indir_btn.disabled, iptal_btn.visible = False, False
            page.update()
        threading.Thread(target=is_, daemon=True).start()

    analiz_btn.on_click = analiz_et
    link.on_submit = analiz_et
    indir_btn.on_click = indir
    iptal_btn.on_click = lambda e: durum["iptal"].set()

    page.add(
        ft.Text("SahneBul İndirici", size=24, weight=ft.FontWeight.BOLD),
        ft.Row([link, analiz_btn]),
        resim, baslik, kanal, kaliteler,
        ft.Row([indir_btn, iptal_btn]), bar, durum_txt,
    )


ft.app(target=main)
