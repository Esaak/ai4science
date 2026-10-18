#!/usr/bin/env python3
"""Список работ без полного текста — для выгрузки руками.

Пишет library/pdf/MISSING.md: год, название, журнал, ссылки и имя, под которым
файл нужно сохранить в library/pdf/, чтобы он связался с записью библиотеки.

Запуск из корня проекта:  .venv/bin/python src/missing_report.py [минимальный_год]
"""
import json
import re
import sys
from datetime import date
from pathlib import Path

MIN_YEAR = int(sys.argv[1]) if len(sys.argv) > 1 else 0


def slug(rec):
    first = (rec["authors"] or ["anon"])[0]
    last = re.sub(r"[^A-Za-z]", "", first.split()[-1]) or "anon"
    return f"{last.lower()}_{rec['year'] or 0}_{rec['id']}"


def main():
    out = Path("library/pdf")
    man = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    by_id = {r["id"]: r for r in man["записи"]}
    docs = [json.loads(l) for l in open("library/corpus.jsonl", encoding="utf-8")]

    miss = [d for d in docs
            if not by_id.get(d["id"], {}).get("файл") and (d["year"] or 0) >= MIN_YEAR]
    miss.sort(key=lambda d: (-(d["year"] or 0), d["title"]))

    lines = [
        "# Работы без полного текста",
        "",
        f"Составлено {date.today().isoformat()}. Нет файла у {len(miss)} работ из {len(docs)}"
        + (f"; отобраны {MIN_YEAR} года и новее." if MIN_YEAR else "."),
        "",
        "Куда класть: скачанный PDF сохранить в `library/pdf/` под именем из столбца",
        "«сохранить как» — тогда запись библиотеки свяжется с файлом. После выгрузки:",
        "",
        "```bash",
        ".venv/bin/python src/link_pdfs.py    # обновит ссылки в library/*.md",
        "```",
        "",
        "Где брать: подписка МФТИ или МГУ (Elsevier, Springer, Taylor & Francis),",
        "страница работы у издателя, копия на странице авторов.",
        "",
    ]

    for d in miss:
        row = by_id.get(d["id"], {})
        doi = d.get("doi")
        lines += [
            f"## {d['year']} — {d['title']}",
            "",
            f"- Журнал: {d['source']}",
            f"- Авторы: {', '.join(d['authors'][:4]) or '—'}" + (" и др." if len(d["authors"]) > 4 else ""),
            f"- DOI: " + (f"https://doi.org/{doi}" if doi else "—"),
            f"- Страница: {row.get('страница') or '—'}",
            f"- Причина: {row.get('причина') or 'открытой копии нет'}",
            f"- Запись библиотеки: `library/{slug(d)}.md`",
            f"- Сохранить как: `library/pdf/{slug(d)}.pdf`",
            "",
        ]

    (out / "MISSING.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"library/pdf/MISSING.md: {len(miss)} работ")
    for d in miss[:8]:
        print(f"  {d['year']}  {d['title'][:66]}")


if __name__ == "__main__":
    main()
