import csv
import sys
from pathlib import Path

import sounddevice as sd
import soundfile as sf

ROOT = Path(__file__).resolve().parent.parent
CLIPS = ROOT / "clips"
SPEAKER = sys.argv[1] if len(sys.argv) > 1 else "me"
SECONDS, RATE = 8, 16000

SENTENCES = [
    ("Article 21 ke under right to privacy ko Puttaswamy judgment mein recognise kiya gaya tha.", "Article 21;privacy;Puttaswamy"),
    ("Basic structure doctrine Kesavananda Bharati case se aayi.", "Basic structure;Kesavananda Bharati"),
    ("Monsoon mein ITCZ ka northward shift aur Tibetan plateau ki heating important hoti hai.", "ITCZ;Tibetan plateau"),
    ("Fiscal deficit aur revenue deficit mein kya difference hota hai?", "Fiscal deficit;revenue deficit"),
    ("Panchayati Raj ko 73rd Constitutional Amendment se constitutional status mila.", "Panchayati Raj;Constitutional Amendment"),
    ("As a District Magistrate, I would first ensure law and order and then coordinate relief.", "District Magistrate;law and order"),
    ("Federalism ka matlab hai power ka division between the Centre and the States.", "Federalism;Centre;States"),
    ("I believe the Goods and Services Tax improved tax compliance but increased the burden on small traders.", "Goods and Services Tax;tax compliance"),
    ("Mere hometown Indore mein urban planning aur waste management ek bada issue hai.", "Indore;urban planning;waste management"),
    ("Directive Principles of State Policy are non-justiciable, lekin governance ke liye guide karte hain.", "Directive Principles;non-justiciable"),
    ("Climate change aur development ke beech balance banana sustainable development kehlata hai.", "Climate change;sustainable development"),
    ("Ethics mein integrity ka matlab hai sahi kaam karna, even when no one is watching.", "Ethics;integrity"),
]


def main() -> None:
    CLIPS.mkdir(exist_ok=True)
    manifest = CLIPS / "manifest.csv"
    new = not manifest.exists()
    with open(manifest, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["file", "speaker", "reference", "terms"])
        for i, (text, terms) in enumerate(SENTENCES, start=1):
            name = f"{SPEAKER}_{i:02d}.wav"
            while True:
                print(f"\n[{i}/{len(SENTENCES)}] Read this aloud after pressing Enter:\n  {text}")
                input("Press Enter to record (8 seconds)... ")
                rec = sd.rec(int(SECONDS * RATE), samplerate=RATE, channels=1, dtype="int16")
                sd.wait()
                sf.write(CLIPS / name, rec, RATE)
                if input("Keep it? Enter = yes, r = redo: ").strip().lower() != "r":
                    break
            w.writerow([name, SPEAKER, text, terms])
    print(f"\nDone. Saved to {CLIPS}")


if __name__ == "__main__":
    main()