#!/usr/bin/env python3
"""Связать файлы из library/pdf/ с записями library/*.md.

Запускается после выгрузки PDF руками: находит в library/pdf/ файлы, которых нет
в манифесте, добавляет их туда и переписывает строку о полном тексте в записи.

Запуск из корня проекта:  .venv/bin/python src/link_pdfs.py
"""
import json
import re
from datetime import date
from pathlib import Path

LIB, OUT = Path("library"), Path("library/pdf")


def slug(rec):
    first = (rec["authors"] or ["anon"])[0]
    last = re.sub(r"[^A-Za-z]", "", first.split()[-1]) or "anon"
    return f"{last.lower()}_{rec['year'] or 0}_{rec['id']}"


def main():
    man = json.loads((OUT / "manifest.json").read_text(encoding="utf-8"))
    by_id = {r["id"]: r for r in man["записи"]}
    docs = [json.loads(l) for l in (LIB / "corpus.jsonl").open(encoding="utf-8")]
    added = 0

    for d in docs:
        name = slug(d)
        pdf = OUT / f"{name}.pdf"
        row = by_id.setdefault(d["id"], {"id": d["id"], "title": d["title"]})
        if pdf.exists() and not row.get("файл"):
            row.update({"файл": pdf.name, "байт": pdf.stat().st_size,
                        "источник": "выгружено вручную", "oa_status": row.get("oa_status")})
            added += 1

        p = LIB / f"{name}.md"
        if not p.exists():
            continue
        text = p.read_text(encoding="utf-8")
        if row.get("файл"):
            line = (f"[источник] Полный текст: [`pdf/{row['файл']}`](pdf/{row['файл']}), "
                    f"{row['байт']/1e6:.1f} МБ.")
        else:
            why = row.get("причина") or "открытой копии нет"
            page = row.get("страница") or (f"https://doi.org/{d['doi']}" if d.get("doi") else None)
            line = (f"[написано] Полного текста в библиотеке нет: {why}."
                    + (f" Страница работы: {page}" if page else ""))
        text = re.sub(r"^\[(?:источник|написано)\] (?:Полный текст|Полного текста).*$",
                      line, text, count=1, flags=re.M)
        p.write_text(text, encoding="utf-8")

    man["записи"] = list(by_id.values())
    man["скачано"] = sum(1 for r in man["записи"] if r.get("файл"))
    man["обновлено"] = date.today().isoformat()
    (OUT / "manifest.json").write_text(json.dumps(man, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"добавлено выгруженных вручную: {added}; всего полных текстов: {man['скачано']}")


if __name__ == "__main__":
    main()
