# -*- coding: utf-8 -*-
"""Arayüzsüz çekirdek: yt_dlp modülüyle analiz + indirme (ffmpeg gerektirmez)."""
import os
import re
import shutil
import threading

import yt_dlp



class Iptal(Exception):
    pass


def temiz(metin):
    """Terminal renk kodlarını sil, son satırı döndür."""
    m = re.sub(r"\x1b\[[0-9;]*m|\[[0-9;]*m", "", str(metin)).strip().splitlines()
    return (m[-1] if m else "")[:300]


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


FFMPEG = shutil.which("ffmpeg")      # masaüstünde varsa birleştirme yapılır; Android'de genelde yok


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

    gruplar = {}
    for f in info.get("formats") or []:
        if f.get("vcodec") in (None, "none"):
            continue
        sesli = f.get("acodec") not in (None, "none")
        if not sesli and not FFMPEG:          # ffmpeg yok: yalnızca sesli+görüntülü tek dosya
            continue
        h = f.get("height") or 0
        if not h:
            continue
        puan = (1 if sesli else 0, f.get("tbr") or 0)
        if h not in gruplar or puan > gruplar[h][0]:
            gruplar[h] = (puan, f, sesli)

    kaliteler = []
    for h, (_, f, sesli) in sorted(gruplar.items(), reverse=True):
        fid = str(f["format_id"]) if sesli else f"{f['format_id']}+bestaudio[ext=m4a]/{f['format_id']}+bestaudio"
        kaliteler.append(dict(tur="video", ad=f"{h}p", h=h, fid=fid, boyut=boyut_yaz(boyut(f))))
    if not kaliteler:                          # hiç uygun format yok: yt-dlp'nin kendi seçimine bırak
        kaliteler.append(dict(tur="video", ad="Otomatik (en iyi)", h=0, fid="b/best", boyut=""))
    kaliteler.append(dict(tur="ses", ad="Sadece ses (m4a)", h=0, fid="bestaudio[ext=m4a]/bestaudio/best",
                          boyut=""))
    return dict(url=url, baslik=info.get("title") or "Başlıksız", kanal=info.get("uploader") or "",
                sure=sure_yaz(sure), resim=info.get("thumbnail"), kaliteler=kaliteler, ffmpeg=bool(FFMPEG))


def indir(url, kalite, klasor, ilerleme, iptal_olayi: threading.Event):
    """ilerleme(yuzde, metin) çağrılır. Dönen değer: indirilen dosyanın yolu."""
    os.makedirs(klasor, exist_ok=True)
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

    h = kalite.get("h") or 0
    # 403 gelirse YouTube'un farklı istemcileriyle ve yüksekliğe göre genel format seçimiyle yeniden dene
    denemeler = [(kalite["fid"], None)]
    if kalite["tur"] == "video":
        genel = f"b[height<={h}]/b" if h else "b"
        denemeler += [(genel, ["tv"]), (genel, ["ios"]), (genel, ["android_vr"]), (genel, ["web_safari"])]
    else:
        denemeler += [("bestaudio/best", ["tv"]), ("bestaudio/best", ["ios"]), ("bestaudio/best", ["android_vr"])]

    son_hata = ""
    for fid, istemci in denemeler:
        if iptal_olayi.is_set():
            raise Iptal()
        opts = {"format": fid, "outtmpl": os.path.join(klasor, "%(title).150s.%(ext)s"),
                "noplaylist": True, "quiet": True, "no_warnings": True, "no_color": True, "retries": 5,
                "windowsfilenames": True, "progress_hooks": [hook]}
        if istemci:
            opts["extractor_args"] = {"youtube": {"player_client": istemci}}
        if FFMPEG:
            opts["merge_output_format"] = "mp4"
        try:
            with yt_dlp.YoutubeDL(opts) as y:
                bilgi = y.extract_info(url, download=True)
                try:
                    sonuc["yol"] = (bilgi.get("requested_downloads") or [{}])[0].get("filepath") or \
                        y.prepare_filename(bilgi)
                except Exception:
                    pass
            return sonuc["yol"]
        except yt_dlp.utils.DownloadError as e:
            if iptal_olayi.is_set():
                raise Iptal()
            son_hata = temiz(str(e))
            ilerleme(0, "Yeniden deneniyor…")
            if "403" not in son_hata and "not available" not in son_hata.lower() and "Forbidden" not in son_hata:
                break                      # 403 / format yok dışındaki hatalarda tekrar denemenin anlamı yok
    raise RuntimeError(son_hata or "İndirme başarısız.")
