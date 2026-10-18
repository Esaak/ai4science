#!/usr/bin/env python3
"""Разложить PDF, выгруженные вручную, по записям библиотеки.

Сопоставление: DOI из текста первых страниц, иначе заголовок записи как подстрока
нормализованного текста. Без аргумента только показывает сопоставление, с --copy
копирует файлы в library/pdf/ под именами записей.

Запуск из корня проекта:
    .venv/bin/python -I src/import_downloads.py <папка> [--copy]
"""
import json
import re
import shutil
import sys
from pathlib import Path

from pypdf import PdfReader

LIB = Path("library")
OUT = LIB / "pdf"


def norm(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def slug(rec):
    first = (rec["authors"] or ["anon"])[0]
    last = re.sub(r"[^A-Za-z]", "", first.split()[-1]) or "anon"
    return f"{last.lower()}_{rec['year'] or 0}_{rec['id']}"


def head_text(path, pages=3):
    try:
        r = PdfReader(str(path))
        return "\n".join((p.extract_text() or "") for p in r.pages[:pages])
    except Exception as e:                      # битый или зашифрованный файл
        print(f"  ! {path.name}: не читается ({type(e).__name__})")
        return ""


def main():
    src_dir = Path(sys.argv[1]).expanduser()
    do_copy = "--copy" in sys.argv
    docs = [json.loads(l) for l in (LIB / "corpus.jsonl").open(encoding="utf-8")]
    man = json.loads((OUT / "manifest.json").read_text(encoding="utf-8"))
    have = {r["id"] for r in man["записи"] if r.get("файл")}

    by_doi = {norm(d["doi"]): d for d in docs if d.get("doi")}
    pdfs = sorted(src_dir.glob("*.pdf"), key=lambda p: -p.stat().st_mtime)[:30]

    pairs, unmatched = [], []
    for pdf in pdfs:
        text = head_text(pdf)
        if not text.strip():
            unmatched.append((pdf, "текст не извлекается"))
            continue
        nt = norm(text)
        hit = None
        for m in re.finditer(r"10\.\d{4,9}/[-._;()/:a-z0-9]+", text, re.I):
            cand = by_doi.get(norm(m.group().rstrip(".")))
            if cand:
                hit = (cand, f"DOI {m.group()[:40]}")
                break
        if not hit:
            for d in docs:
                t = norm(d["title"])
                if len(t) > 25 and t in nt:
                    hit = (d, "заголовок")
                    break
        if hit:
            pairs.append((pdf, hit[0], hit[1]))
        else:
            unmatched.append((pdf, "не нашлось в библиотеке"))

    seen = {}
    print(f"сопоставлено {len(pairs)} из {len(pdfs)} просмотренных файлов\n")
    for pdf, d, how in sorted(pairs, key=lambda x: -(x[1]["year"] or 0)):
        name = slug(d)
        mark = "уже есть" if d["id"] in have else ("ДУБЛЬ" if name in seen else "новый")
        seen[name] = pdf
        print(f"  [{mark:8s}] {pdf.name[:38]:40s} → {name}.pdf")
        print(f"             {d['year']} {d['title'][:66]}  ({how})")
        if do_copy and mark == "новый":
            shutil.copy2(pdf, OUT / f"{name}.pdf")

    if unmatched:
        print(f"\nне сопоставлено ({len(unmatched)}):")
        for pdf, why in unmatched:
            print(f"  {pdf.name[:46]:48s} {why}")

    if do_copy:
        print("\nфайлы скопированы; дальше: .venv/bin/python src/link_pdfs.py")


if __name__ == "__main__":
    main()
