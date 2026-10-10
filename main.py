# -*- coding: utf-8 -*-
"""
SahneBul Studio — Android MVP: sadece video indirme.
Kivy + yt-dlp (Python kütüphanesi olarak kullanılır, .exe değil).

ÖNEMLİ SINIRLAMA:
ffmpeg Android tarafına henüz dahil edilmedi. Bu yüzden yalnızca
"tek parçada" (hem görüntü hem ses aynı dosyada) gelen formatlar
listelenir. YouTube gibi sitelerde en yüksek çözünürlükler genelde
görüntü/ses ayrı akış halinde gelir ve BİRLEŞTİRME için ffmpeg gerekir
— bu MVP'de kapsam dışıdır (sonraki adımda FFmpegKit eklenebilir).
"""
import os
import threading

import yt_dlp
from kivy.app import App
from kivy.clock import mainthread
from kivy.lang import Builder
from kivy.properties import StringProperty, NumericProperty, BooleanProperty, ListProperty
from kivy.uix.boxlayout import BoxLayout

try:
    from android.storage import app_storage_path  # type: ignore
    ANDROID = True
except Exception:
    ANDROID = False


def indirme_klasoru():
    if ANDROID:
        taban = app_storage_path()
    else:
        taban = os.path.join(os.path.expanduser("~"), "SahneBulIndirmeler")
    yol = os.path.join(taban, "Indirilenler")
    os.makedirs(yol, exist_ok=True)
    return yol


KV = """
<Kok>:
    orientation: "vertical"
    padding: dp(16)
    spacing: dp(10)

    BoxLayout:
        size_hint_y: None
        height: dp(48)
        spacing: dp(8)
        TextInput:
            id: link
            hint_text: "https://... video linki"
            multiline: False
            size_hint_x: 0.75
        Button:
            text: "Analiz Et"
            size_hint_x: 0.25
            on_release: root.analiz_et()

    Label:
        id: baslik_lbl
        text: root.baslik
        size_hint_y: None
        height: dp(60) if root.baslik else 0
        text_size: self.width, None
        halign: "left"
        valign: "top"

    Spinner:
        id: kalite
        text: "Kalite seç"
        values: root.kalite_listesi
        size_hint_y: None
        height: dp(44)
        disabled: not root.kalite_listesi

    Button:
        text: "İndiriliyor…" if root.indiriyor else "↓  İndir"
        size_hint_y: None
        height: dp(52)
        disabled: root.indiriyor or not root.kalite_listesi
        on_release: root.indir_baslat()

    ProgressBar:
        id: pb
        max: 100
        value: root.yuzde
        size_hint_y: None
        height: dp(20)

    Label:
        id: durum_lbl
        text: root.durum
        size_hint_y: None
        height: dp(28)

    Widget:
"""


class Kok(BoxLayout):
    baslik = StringProperty("")
    durum = StringProperty("Hazır")
    yuzde = NumericProperty(0)
    indiriyor = BooleanProperty(False)
    kalite_listesi = ListProperty([])

    def __init__(self, **kw):
        super().__init__(**kw)
        self._bilgi = None
        self._formatlar = {}   # "720p mp4 (45 MB)" -> format_id

    # ---------------------------------------------------------------- Analiz
    def analiz_et(self):
        link = self.ids.link.text.strip()
        if not link.lower().startswith(("http://", "https://")):
            self.durum = "Geçerli bir link girin."
            return
        self.durum = "Analiz ediliyor…"
        self.kalite_listesi = []
        self.ids.kalite.text = "Kalite seç"
        threading.Thread(target=self._analiz_isci, args=(link,), daemon=True).start()

    def _analiz_isci(self, link):
        try:
            opts = {"quiet": True, "no_warnings": True, "skip_download": True}
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(link, download=False)
            if info.get("_type") == "playlist":
                girdi = info.get("entries") or []
                if not girdi:
                    raise RuntimeError("Video bulunamadı.")
                info = girdi[0]
            self._analiz_tamam(info)
        except Exception as e:
            self._analiz_hata(str(e))

    @mainthread
    def _analiz_tamam(self, info):
        self._bilgi = info
        self.baslik = info.get("title") or "Başlıksız video"
        formatlar = [f for f in (info.get("formats") or [])
                     if f.get("vcodec") not in (None, "none") and f.get("acodec") not in (None, "none")]
        formatlar.sort(key=lambda f: f.get("height") or 0, reverse=True)
        self._formatlar = {}
        etiketler = []
        for f in formatlar:
            h = f.get("height") or 0
            ext = f.get("ext") or "mp4"
            boyut = f.get("filesize") or f.get("filesize_approx") or 0
            mb = f"{boyut / 1048576:.0f} MB" if boyut else "boyut bilinmiyor"
            etiket = f"{h}p · {ext} · {mb}"
            etiketler.append(etiket)
            self._formatlar[etiket] = f["format_id"]
        if not etiketler:
            etiketler = ["En iyi kalite (otomatik)"]
            self._formatlar[etiketler[0]] = "best"
        self.kalite_listesi = etiketler
        self.durum = "Hazır — kalite seç ve indir"

    @mainthread
    def _analiz_hata(self, hata):
        self.durum = "Hata: " + hata[:120]

    # ---------------------------------------------------------------- İndirme
    def indir_baslat(self):
        secili = self.ids.kalite.text
        if secili not in self._formatlar or not self._bilgi:
            self.durum = "Önce bir kalite seç."
            return
        self.indiriyor = True
        self.yuzde = 0
        self.durum = "İndirme başlıyor…"
        fid = self._formatlar[secili]
        url = self._bilgi.get("webpage_url") or self.ids.link.text.strip()
        threading.Thread(target=self._indir_isci, args=(url, fid), daemon=True).start()

    def _indir_isci(self, url, fid):
        try:
            cikti = indirme_klasoru()
            opts = {
                "format": fid,
                "outtmpl": os.path.join(cikti, "%(title).150s.%(ext)s"),
                "noplaylist": True,
                "quiet": True,
                "no_warnings": True,
                "progress_hooks": [self._ilerleme],
            }
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([url])
            self._indir_bitti(True, cikti)
        except Exception as e:
            self._indir_bitti(False, str(e))

    def _ilerleme(self, d):
        if d.get("status") == "downloading":
            toplam = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            indirilen = d.get("downloaded_bytes") or 0
            yuzde = (indirilen / toplam * 100) if toplam else 0
            self._ilerleme_guncelle(yuzde)

    @mainthread
    def _ilerleme_guncelle(self, yuzde):
        self.yuzde = yuzde
        self.durum = f"İndiriliyor… %{yuzde:.0f}"

    @mainthread
    def _indir_bitti(self, basarili, bilgi):
        self.indiriyor = False
        if basarili:
            self.yuzde = 100
            self.durum = "Tamamlandı: " + bilgi
        else:
            self.durum = "Hata: " + str(bilgi)[:120]


class SahneBulApp(App):
    def build(self):
        Builder.load_string(KV)
        return Kok()


if __name__ == "__main__":
    SahneBulApp().run()
