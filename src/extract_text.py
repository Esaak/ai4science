#!/usr/bin/env python3
"""Извлечь текст из PDF библиотеки в library/text/<запись>.md.

Текст нужен корпусу поиска недели 5: на аннотациях (медиана 218 слов) разброс длин
документов не виден, на полных текстах виден. Страницы размечаются метками [с. N].
Файл записи в library/ остаётся коротким, в него добавляется ссылка на текст.

Запуск из корня проекта:  .venv/bin/python -I src/extract_text.py
"""
import json
import re
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

from pypdf import PdfReader

LIB = Path("library")
PDF = LIB / "pdf"
TXT = LIB / "text"


def slug(rec):
    first = (rec["authors"] or ["anon"])[0]
    last = re.sub(r"[^A-Za-z]", "", first.split()[-1]) or "anon"
    return f"{last.lower()}_{rec['year'] or 0}_{rec['id']}"


def main():
    TXT.mkdir(exist_ok=True)
    docs = [json.loads(l) for l in (LIB / "corpus.jsonl").open(encoding="utf-8")]
    done, skipped = 0, 0

    for d in docs:
        name = slug(d)
        pdf = PDF / f"{name}.pdf"
        if not pdf.exists():
            continue
        out = TXT / f"{name}.md"
        if out.exists() and out.stat().st_size > 0:
            d["text_file"] = out.name
            d["full_text"] = out.read_text(encoding="utf-8")
            skipped += 1
            continue
        try:
            pages = [(p.extract_text() or "") for p in PdfReader(str(pdf)).pages]
        except Exception as e:                  # битый файл не должен ронять проход
            print(f"  ! {name}: {type(e).__name__}: {e}")
            continue
        body = []
        for i, t in enumerate(pages, start=1):
            t = re.sub(r"[ \t]+", " ", t).strip()
            if t:
                body.append(f"\n[с. {i}]\n{t}")
        text = "\n".join(body)
        words = len(text.split())
        if words < 200:
            print(f"  ! {name}: текст не извлекается ({words} слов) — вероятно сканированный PDF")
            continue
        out.write_text(
            f"---\ntype: ПолныйТекст\nзапись: {name}.md\nфайл: pdf/{pdf.name}\n"
            f"страниц: {len(pages)}\nслов: {words}\n---\n\n"
            f"# {d['title']}\n\n"
            f"[источник] Текст извлечён из `pdf/{pdf.name}`; метки `[с. N]` — страницы.\n"
            + text + "\n", encoding="utf-8")
        d["text_file"] = out.name
        d["full_text"] = text
        done += 1
        print(f"  + {name[:46]:48s} {len(pages):3d} с., {words:6d} слов")

    with (LIB / "corpus.jsonl").open("w", encoding="utf-8") as f:
        for d in docs:
            f.write(json.dumps(d, ensure_ascii=False) + "\n")

    with_text = [d for d in docs if d.get("text_file")]
    w = [len(d["full_text"].split()) for d in with_text]
    print(f"\nизвлечено {done}, уже было {skipped}; текстов всего {len(with_text)}")
    if w:
        print(f"слов в тексте: минимум {min(w)}, медиана {sorted(w)[len(w)//2]}, максимум {max(w)}")


if __name__ == "__main__":
    main()
