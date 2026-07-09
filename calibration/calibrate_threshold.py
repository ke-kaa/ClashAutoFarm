
import cv2
from pathlib import Path
from vision.templates import match_score

DATA = Path(__file__).parent / "data"
TEMPLATES = Path(__file__).resolve().parent.parent / "assets" / "templates"


def _scores(folder, template):
    out = []
    for p in sorted(folder.glob("*.png")):
        img = cv2.imread(str(p))
        if img is None:
            print(f"  [warn] unreadable: {p}")
            continue
        out.append(match_score(img, template))
    return out


def main():
    for tdir in sorted(d for d in DATA.iterdir() if d.is_dir()):
        key = tdir.name
        template = cv2.imread(str(TEMPLATES / f"{key}.png"))
        if template is None:
            print(f"\n== {key} ==\n  [skip] missing template {key}.png")
            continue

        match = _scores(tdir / "match", template)
        nomatch = _scores(tdir / "nomatch", template)

        print(f"\n== {key} ==")
        print(f"  match   ({len(match)}): {sorted(round(s, 3) for s in match)}")
        print(f"  nomatch ({len(nomatch)}): {sorted(round(s, 3) for s in nomatch)}")
        if not match or not nomatch:
            print("  need >=1 image in BOTH match/ and nomatch/")
            continue

        lo, hi = min(match), max(nomatch)   # worst true-positive, best false-positive
        if lo > hi:
            print(f"  OK  separable -> threshold = {round((lo + hi) / 2, 3)}  (gap {round(lo - hi, 3)})")
        else:
            print(f"  BAD overlap (min match {round(lo,3)} <= max nomatch {round(hi,3)}) -> recrop template tighter")


if __name__ == "__main__":
    main()
