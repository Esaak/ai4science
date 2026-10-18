#!/usr/bin/env python3
"""Добавить работу в библиотеку: запись из OpenAlex + локальный PDF.

Запуск из корня проекта:
    .venv/bin/python -I src/add_work.py <идентификатор>=<путь к PDF> [ещё...]

Идентификатор — DOI или `title:<заголовок>`. После добавления запускается
извлечение текста: .venv/bin/python -I src/extract_text.py
"""
import json
import re
import shutil
import sys
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

LIB = Path("library")
SELECT = ("id,doi,display_name,publication_year,cited_by_count,abstract_inverted_index,"
          "primary_location,authorships,type,open_access")


def restore_abstract(inv):
    if not inv:
        return ""
    pos = {}
    for word, places in inv.items():
        for p in places:
            pos[p] = word
    return " ".join(pos[k] for k in sorted(pos))


def slug(rec):
    first = (rec["authors"] or ["anon"])[0]
    last = re.sub(r"[^A-Za-z]", "", first.split()[-1]) or "anon"
    return f"{last.lower()}_{rec['year'] or 0}_{rec['id']}"


def fetch(ident):
    if ident.startswith("title:"):
        url = ("https://api.openalex.org/works?per_page=1&select=" + SELECT
               + "&search=" + urllib.parse.quote(ident[6:]))
        with urllib.request.urlopen(url, timeout=60) as r:
            res = json.load(r)["results"]
        return (res[0] if res else None), url
    url = (f"https://api.openalex.org/works/doi:{urllib.parse.quote(ident, safe='')}"
           f"?select={SELECT}")
    with urllib.request.urlopen(url, timeout=60) as r:
        return json.load(r), url


def main():
    docs = [json.loads(l) for l in (LIB / "corpus.jsonl").open(encoding="utf-8")]
    known = {d["id"] for d in docs}
    man = json.loads((LIB / "pdf" / "manifest.json").read_text(encoding="utf-8"))

    for arg in sys.argv[1:]:
        ident, _, pdf_path = arg.partition("=")
        w, url = fetch(ident)
        if not w:
            print(f"  ! {ident}: в OpenAlex не найдено")
            continue
        loc = w.get("primary_location") or {}
        rec = {
            "id": w["id"].rsplit("/", 1)[-1],
            "title": w.get("display_name") or "",
            "abstract": restore_abstract(w.get("abstract_inverted_index")),
            "year": w.get("publication_year"),
            "doi": (w.get("doi") or "").replace("https://doi.org/", "") or None,
            "source": (loc.get("source") or {}).get("display_name") or "—",
            "authors": [a["author"]["display_name"] for a in (w.get("authorships") or [])][:8],
            "cited_by": w.get("cited_by_count", 0),
            "oa_status": (w.get("open_access") or {}).get("oa_status", "unknown"),
            "topic": "добавлено-вручную",
            "query": url,
            "retrieved": date.today().isoformat(),
            "searchable": True,
        }
        if rec["id"] in known:
            print(f"  = {rec['title'][:56]}: уже в библиотеке")
            continue
        name = slug(rec)
        src = Path(pdf_path).expanduser()
        if not src.exists():
            print(f"  ! {name}: нет файла {src}")
            continue
        shutil.copy2(src, LIB / "pdf" / f"{name}.pdf")

        head = {"type": "Источник", "openalex_id": rec["id"], "doi": rec["doi"],
                "year": rec["year"], "journal": rec["source"], "cited_by": rec["cited_by"],
                "oa_status": rec["oa_status"], "topic": rec["topic"],
                "вКорпусеПоиска": True, "найденЗапросом": rec["query"],
                "датаОбращения": rec["retrieved"]}
        lines = ["---"]
        lines += [f"{k}: {json.dumps(v, ensure_ascii=False) if isinstance(v, str) else v}"
                  for k, v in head.items()]
        lines += ["---", "", f"# {rec['title']}", "",
                  f"[источник] {', '.join(rec['authors'])} ({rec['year']}). "
                  f"*{rec['title']}*. {rec['source']}."
                  + (f" DOI: {rec['doi']}." if rec["doi"] else ""),
                  "[источник] Полный текст: будет связан скриптом extract_text.py", "",
                  "## Аннотация", "", f"[источник] {rec['abstract']}", "",
                  "## Зачем проекту", "", "[написано] <заполняется при чтении>", ""]
        (LIB / f"{name}.md").write_text("\n".join(lines), encoding="utf-8")

        docs.append(rec)
        man["записи"].append({"id": rec["id"], "файл": f"{name}.pdf", "title": rec["title"],
                              "oa_status": rec["oa_status"], "источник": "выгружено вручную",
                              "байт": (LIB / "pdf" / f"{name}.pdf").stat().st_size})
        print(f"  + {name}: {rec['year']} {rec['title'][:56]}")

    with (LIB / "corpus.jsonl").open("w", encoding="utf-8") as f:
        for d in docs:
            f.write(json.dumps(d, ensure_ascii=False) + "\n")
    man["скачано"] = sum(1 for r in man["записи"] if r.get("файл"))
    (LIB / "pdf" / "manifest.json").write_text(
        json.dumps(man, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nв библиотеке работ: {len(docs)}")


if __name__ == "__main__":
    main()
