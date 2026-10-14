import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

ROWS = [
    ("me_01.wav", "Article 21 ke under right to privacy ko Puttaswamy judgment mein recognise kiya gaya tha.",
     "Article 21|आर्टिकल 21;privacy|प्राइवेसी;Puttaswamy|पुट्टस्वामी"),
    ("me_02.wav", "Basic structure doctrine Kesavananda Bharati case se aayi.",
     "Basic structure|बेसिक स्ट्रक्चर;Kesavananda Bharati|केशवानंद भारती|केशवानंदा भारती"),
    ("me_03.wav", "Monsoon mein ITCZ ka northward shift aur Tibetan plateau ki heating important hoti hai.",
     "ITCZ|आईटीसीजेड;Tibetan plateau|तिब्बतन प्लेटो|तिब्बतन प्लेट्यू"),
    ("me_04.wav", "Fiscal deficit aur revenue deficit mein kya difference hota hai?",
     "Fiscal deficit|फिस्कल डेफिसिट;revenue deficit|रेवेन्यू डेफिसिट"),
    ("me_05.wav", "Panchayati Raj ko 73rd Constitutional Amendment se constitutional status mila.",
     "Panchayati Raj|पंचायती राज;Constitutional Amendment|कॉन्स्टिट्यूशनल अमेंडमेंट"),
    ("me_06.wav", "As a District Magistrate, I would first ensure law and order and then coordinate relief.",
     "District Magistrate|डिस्ट्रिक्ट मजिस्ट्रेट;law and order|लॉ एंड ऑर्डर"),
    ("me_07.wav", "Federalism ka matlab hai power ka division between the Centre and the States.",
     "Federalism|फेडरलिज्म;Centre|Center|सेंटर;States|स्टेट्स"),
    ("me_08.wav", "I believe the Goods and Services Tax improved tax compliance but increased the burden on small traders.",
     "Goods and Services Tax|गुड्स एंड सर्विसेज टैक्स;tax compliance|टैक्स कंप्लायंस"),
    ("me_09.wav", "Mere hometown Indore mein urban planning aur waste management ek bada issue hai.",
     "Indore|इंदौर;urban planning|अर्बन प्लानिंग;waste management|वेस्ट मैनेजमेंट"),
    ("me_10.wav", "Directive Principles of State Policy are non-justiciable, lekin governance ke liye guide karte hain.",
     "Directive Principles|डायरेक्टिव प्रिंसिपल्स;non-justiciable|non justiciable|नॉन-जस्टिसेबल|नॉन जस्टिसेबल"),
    ("me_11.wav", "Climate change aur development ke beech balance banana sustainable development kehlata hai.",
     "Climate change|क्लाइमेट चेंज;sustainable development|सस्टेनेबल डेवलपमेंट"),
    ("me_12.wav", "Ethics mein integrity ka matlab hai sahi kaam karna, even when no one is watching.",
     "Ethics|एथिक्स;integrity|इंटीग्रिटी"),
]

for r in ROWS:
    assert len(r) == 3, f"Bad row: {r}"

out = ROOT / "clips" / "manifest.csv"
with open(out, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["file", "speaker", "reference", "terms"])
    for file, ref, terms in ROWS:
        w.writerow([file, "me", ref, terms])
print(f"Wrote {len(ROWS)} rows to {out}")