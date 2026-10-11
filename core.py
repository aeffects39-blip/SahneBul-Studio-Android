# -*- coding: utf-8 -*-
"""Arayüzsüz çekirdek: yt_dlp modülüyle analiz + indirme (ffmpeg gerektirmez)."""
import os
import re
import threading

import yt_dlp

UCRETSIZ_MAX = 720


class Iptal(Exception):
    pass


def indirme_klasoru():
    for yol in ("/storage/emulated/0/Download/SahneBul",
                os.path.join(os.path.expanduser("~"), "Downloads", "SahneBul")):
        try:
            os.makedirs(yol, exist_ok=True)
            return yol
        except OSError:
            continue
    return os.getcwd()


def boyut_yaz(b):
    if not b:
        return "—"
    mb = b / 1048576
    return f"~{mb / 1024:.1f} GB" if mb >= 1024 else f"~{mb:.1f} MB"


def sure_yaz(sn):
    sn = int(sn or 0)
    if sn <= 0:
        return ""
    sa, k = divmod(sn, 3600)
    dk, sn = divmod(k, 60)
    return f"{sa}:{dk:02d}:{sn:02d}" if sa else f"{dk}:{sn:02d}"


def analiz(url):
    """Video bilgisini ve kalite seçeneklerini döndürür."""
    with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True, "noplaylist": True}) as y:
        info = y.extract_info(url, download=False)
    sure = info.get("duration") or 0

    def boyut(f):
        b = f.get("filesize") or f.get("filesize_approx")
        if not b and f.get("tbr") and sure:
            b = f["tbr"] * 1000 / 8 * sure
        return b or 0

    # ffmpeg olmadan yalnızca ses+görüntü birleşik (progressive) formatlar indirilebilir
    gruplar = {}
    for f in info.get("formats") or []:
        if f.get("vcodec") in (None, "none") or f.get("acodec") in (None, "none"):
            continue
        h = f.get("height") or 0
        if h and (h not in gruplar or (f.get("tbr") or 0) > (gruplar[h].get("tbr") or 0)):
            gruplar[h] = f
    kaliteler = [dict(tur="video", ad=f"{h}p", h=h, fid=str(f["format_id"]), boyut=boyut_yaz(boyut(f)))
                 for h, f in sorted(gruplar.items(), reverse=True)]
    kaliteler.append(dict(tur="ses", ad="Sadece ses (m4a)", h=0, fid="bestaudio[ext=m4a]/bestaudio",
                          boyut=""))
    return dict(url=url, baslik=info.get("title") or "Başlıksız", kanal=info.get("uploader") or "",
                sure=sure_yaz(sure), resim=info.get("thumbnail"), kaliteler=kaliteler)


def indir(url, kalite, klasor, ilerleme, iptal_olayi: threading.Event, premium=False):
    """ilerleme(yuzde, metin) çağrılır. Dönen değer: indirilen dosyanın yolu."""
    if kalite["tur"] == "video" and kalite["h"] > UCRETSIZ_MAX and not premium:
        raise RuntimeError(f"{UCRETSIZ_MAX}p üzeri Premium'a özel.")
    sonuc = {"yol": ""}

    def hook(d):
        if iptal_olayi.is_set():
            raise Iptal()
        if d["status"] == "downloading":
            top = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            yuzde = d.get("downloaded_bytes", 0) / top * 100 if top else 0
            hiz = re.sub(r"\x1b\[[0-9;]*m", "", d.get("_speed_str", "")).strip()
            eta = re.sub(r"\x1b\[[0-9;]*m", "", d.get("_eta_str", "")).strip()
            ilerleme(yuzde, f"%{yuzde:.0f}  ·  {hiz}  ·  kalan {eta}")
        elif d["status"] == "finished":
            sonuc["yol"] = d.get("filename", "")
            ilerleme(100, "Tamamlandı")

    opts = {"format": kalite["fid"], "outtmpl": os.path.join(klasor, "%(title).150s.%(ext)s"),
            "noplaylist": True, "quiet": True, "no_warnings": True, "retries": 10,
            "windowsfilenames": True, "progress_hooks": [hook]}
    try:
        with yt_dlp.YoutubeDL(opts) as y:
            y.download([url])
    except yt_dlp.utils.DownloadError as e:
        if iptal_olayi.is_set():
            raise Iptal()
        raise RuntimeError(str(e).splitlines()[-1][:300])
    return sonuc["yol"]
