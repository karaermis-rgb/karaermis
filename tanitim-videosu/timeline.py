"""Senaryo zaman çizelgesi: sahneler, çekimler, kartlar ve altyazılar.

Seslendirme dosyaları (ses/vo/NN.mp3) varsa cümle süreleri onlardan alınır;
yoksa okunma hızından tahmin edilir (taslak).
"""
import json
import os
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
VO_DIR = os.path.join(HERE, "ses", "vo")

SCHOOL = "Şehit Yavuz Sonat Güzel Mesleki ve Teknik Anadolu Lisesi"
FIELD = "Yiyecek İçecek Hizmetleri Alanı"

# Cümleler (altyazı = seslendirme). id -> metin
LINES = {
    1: "Mutfakta bir lezzet doğarken, onun arkasındaki ustayı hiç merak ettin mi?",
    2: "Peki o usta… sen olabilir misin?",
    3: f"{SCHOOL}'nde {FIELD}'na hoş geldin.",
    4: "Burada mesleği kitaptan değil, tezgâhın başında, yaparak öğreniyorsun.",
    5: "Alanımızda şu dallarda uzmanlaşabilirsin: [BOŞLUK – okuldaki dallar].",
    6: "[BOŞLUK – 1. dalın tek cümlelik tanımı]",
    16: "[BOŞLUK – 2. dalın tek cümlelik tanımı]",
    17: "[BOŞLUK – 3. dalın tek cümlelik tanımı]",
    18: "Mutfakta her tabak; bilgi, emek ve yaratıcılığın buluştuğu küçük bir eserdir.",
    19: "Malzemeyi tanımayı, doğru pişirme tekniklerini ve tabağı özenle sunmayı adım adım öğreniyorsun.",
    20: "Disiplin, özen ve yaratıcılık; bu meslekte seni öne çıkaracak üç anahtar.",
    21: "Her uygulamada, her denemede yanında olacaklar.",
    22: "Geleceğini kendi ellerinle hazırla.",
    7: "Uygulamalarımızı [BOŞLUK – atölye adı ve donanımı] ortamında yapıyoruz.",
    8: "Hijyen, mutfak güvenliği ve ekip çalışması, her uygulamanın temelidir.",
    9: "[BOŞLUK – işletmelerde beceri eğitimi / staj bilgisi]",
    10: "Bu alan, yetenekli ellere birçok kapı açar.",
    11: "Restoranlar, oteller, pastaneler, toplu yemek işletmeleri ve kendi işletmen…",
    12: "[BOŞLUK – okulun vermek istediği somut kariyer bilgisi]",
    13: "Bu yolda sana alan öğretmenlerimiz Ebru KARAERMİŞ ve Alpay ŞİMŞEK rehberlik ediyor.",
    14: "Lezzetin peşinden gitmeye hazır mısın?",
    15: "Seni de mutfağımıza bekliyoruz!",
}

# Sahneler: her sahnede cümleler, çekimler (foto yuvası + hareket) ve kartlar.
# move: zoom_in | zoom_out | pan_r | pan_l | parallax
SCENES_169 = [
    dict(name="acilis", lines=[1, 2], pad=2.0, ticks=True,
         shots=[("FOTO-1", "zoom_in")],
         cards=[dict(at=0.4, kind="question", title="Bu usta sen olabilir misin?")]),
    dict(name="alan", lines=[3, 4, 18], pad=1.5,
         shots=[("FOTO-2", "pan_r")],
         cards=[dict(at=0.5, kind="title", title=FIELD, sub="Kandıra · Kocaeli")]),
    dict(name="dallar", lines=[5, 6, 16, 17], pad=2.0,
         shots=[("FOTO-3", "parallax"), ("FOTO-4", "parallax"), ("FOTO-5", "parallax")],
         cards=[dict(at=0.0, shot=0, kind="info", title="DAL 1", sub="[BOŞLUK]"),
                dict(at=0.0, shot=1, kind="info", title="DAL 2", sub="[BOŞLUK]"),
                dict(at=0.0, shot=2, kind="info", title="DAL 3", sub="[BOŞLUK]")]),
    dict(name="atolye", lines=[7, 19, 8, 9], pad=2.0, sizzle=True,
         shots=[("FOTO-6", "parallax"), ("FOTO-7", "pan_l"), ("FOTO-8", "zoom_out")],
         cards=[dict(at=0.6, kind="label", title="Atölye ve Uygulama")]),
    dict(name="kariyer", lines=[10, 11, 20, 12], pad=2.0, lift=True,
         shots=[("FOTO-9", "parallax"), ("FOTO-10", "pan_r")],
         cards=[dict(at=0.3, kind="list", title="Nerelerde çalışabilirsin?",
                     items=["Restoranlar", "Oteller", "Pastaneler",
                            "Toplu yemek işletmeleri", "Kendi işletmen"])]),
    dict(name="ogretmenler", lines=[13, 21], pad=2.5, calm=True,
         shots=[("FOTO-11", "zoom_out")],
         cards=[dict(at=0.4, kind="names", title="Alan Öğretmenlerimiz",
                     items=["Ebru KARAERMİŞ", "Alpay ŞİMŞEK"])]),
    dict(name="kapanis", lines=[14, 22, 15], pad=1.5,
         shots=[("FOTO-12", "zoom_out")],
         cards=[dict(at=0.3, kind="cta", title="Seni de mutfağımıza bekliyoruz!")]),
    dict(name="kunye", lines=[], pad=9.0, endcard=True, shots=[], cards=[]),
]

# 60 sn dikey kesit: aynı cümlelerin alt kümesi
SCENES_916 = [
    dict(name="acilis", lines=[1, 2], pad=1.4, ticks=True,
         shots=[("FOTO-1", "zoom_in")],
         cards=[dict(at=0.2, kind="question", title="Bu usta sen olabilir misin?")]),
    dict(name="alan", lines=[4], pad=0.6,
         shots=[("FOTO-2", "pan_r")],
         cards=[dict(at=0.3, kind="title", title=FIELD, sub="Kandıra · Kocaeli")]),
    dict(name="dallar", lines=[5, 6, 16, 17], pad=0.8,
         shots=[("FOTO-3", "parallax"), ("FOTO-4", "parallax"), ("FOTO-5", "parallax")],
         cards=[dict(at=0.0, shot=0, kind="info", title="DAL 1", sub="[BOŞLUK]"),
                dict(at=0.0, shot=1, kind="info", title="DAL 2", sub="[BOŞLUK]"),
                dict(at=0.0, shot=2, kind="info", title="DAL 3", sub="[BOŞLUK]")]),
    dict(name="atolye", lines=[8], pad=1.0, sizzle=True,
         shots=[("FOTO-6", "zoom_in"), ("FOTO-7", "pan_l")],
         cards=[dict(at=0.3, kind="label", title="Atölye ve Uygulama")]),
    dict(name="kariyer", lines=[11], pad=2.0, lift=True,
         shots=[("FOTO-9", "parallax")],
         cards=[dict(at=0.2, kind="list", title="Nerelerde çalışabilirsin?",
                     items=["Restoranlar", "Oteller", "Pastaneler",
                            "Toplu yemek", "Kendi işletmen"])]),
    dict(name="kapanis", lines=[15], pad=0.6,
         shots=[("FOTO-12", "zoom_out")],
         cards=[dict(at=0.2, kind="cta", title="Seni de mutfağımıza bekliyoruz!")]),
    dict(name="kunye", lines=[], pad=7.0, endcard=True, shots=[], cards=[]),
]

ENDCARD = dict(
    title=SCHOOL,
    sub=FIELD,
    rows=["Adres: [BOŞLUK]", "Telefon: [BOŞLUK]", "Web / Sosyal medya: [BOŞLUK]"],
)

GAP = 0.35  # cümleler arası sessizlik


def vo_path(i):
    return os.path.join(VO_DIR, f"{i:02d}.mp3")


def line_duration(i):
    p = vo_path(i)
    if os.path.exists(p):
        out = subprocess.check_output(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", p]).decode().strip()
        return float(out)
    return max(1.6, len(LINES[i]) / 13.0 + 0.4)  # tahmini okuma süresi


def build(scenes, target=None):
    """Mutlak zamanlı zaman çizelgesi döndürür."""
    t = 0.0
    out_scenes, subs = [], []
    for sc in scenes:
        start = t
        lt = start + 0.3
        for i in sc["lines"]:
            d = line_duration(i)
            subs.append(dict(id=i, start=lt, end=lt + d, text=LINES[i]))
            lt += d + GAP
        end = max(lt, start + 0.3) + sc["pad"]
        out_scenes.append(dict(sc, start=start, end=end))
        t = end
    total = t
    if target and abs(total - target) > 0.5:
        # pad'leri orantılı ayarla (yalnızca kısa kesit için)
        pass
    return dict(scenes=out_scenes, subs=subs, total=total)


def load_photos():
    with open(os.path.join(HERE, "fotolar.json"), encoding="utf-8") as f:
        return json.load(f)


if __name__ == "__main__":
    for name, sc in (("16:9", SCENES_169), ("9:16", SCENES_916)):
        tl = build(sc)
        print(name, f"{tl['total']:.1f} sn")
        for s in tl["scenes"]:
            print(f"  {s['name']:12s} {s['start']:6.1f} → {s['end']:6.1f}")
