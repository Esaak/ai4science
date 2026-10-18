#!/usr/bin/env python3
"""Поиск недостающих полных текстов на arXiv — законный открытый доступ.

Для работ из library/corpus.jsonl, у которых нет файла в library/pdf/, спрашивает
arXiv по названию. Совпадение принимается, только если названия совпадают после
нормализации (без регистра, знаков и пробелов) или отличаются на пару символов.

Запуск из корня проекта:  .venv/bin/python src/fetch_arxiv.py [минимальный_год]
"""
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path

ATOM = "{http://www.w3.org/2005/Atom}"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36"
MIN_YEAR = int(sys.argv[1]) if len(sys.argv) > 1 else 2016


def norm(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def slug(rec):
    first = (rec["authors"] or ["anon"])[0]
    last = re.sub(r"[^A-Za-z]", "", first.split()[-1]) or "anon"
    return f"{last.lower()}_{rec['year'] or 0}_{rec['id']}"


def arxiv_search(title):
    q = urllib.parse.urlencode({
        "search_query": f'ti:"{title[:180]}"', "start": 0, "max_results": 5,
    })
    url = f"http://export.arxiv.org/api/query?{q}"
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=60) as r:
        feed = ET.fromstring(r.read())
    out = []
    for e in feed.findall(f"{ATOM}entry"):
        t = (e.findtext(f"{ATOM}title") or "").strip()
        pdf = None
        for link in e.findall(f"{ATOM}link"):
            if link.get("title") == "pdf":
                pdf = link.get("href")
        out.append((t, pdf))
    return out


def main():
    lib, out = Path("library"), Path("library/pdf")
    man = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    by_id = {r["id"]: r for r in man["записи"]}
    docs = [json.loads(l) for l in (lib / "corpus.jsonl").open(encoding="utf-8")]

    found = []
    for d in docs:
        if by_id.get(d["id"], {}).get("файл") or not d["year"] or d["year"] < MIN_YEAR:
            continue
        try:
            hits = arxiv_search(d["title"])
        except (urllib.error.HTTPError, urllib.error.URLError, ET.ParseError, TimeoutError) as e:
            print(f"  ? {d['title'][:58]:60s} arXiv недоступен: {e}")
            time.sleep(3)
            continue
        match = next((h for h in hits if norm(h[0]) == norm(d["title"])), None)
        if not match or not match[1]:
            print(f"  — {d['title'][:58]:60s} на arXiv нет")
        else:
            dest = out / f"{slug(d)}.pdf"
            try:
                req = urllib.request.Request(match[1], headers={"User-Agent": UA})
                with urllib.request.urlopen(req, timeout=120) as r:
                    data = r.read()
                if not data.startswith(b"%PDF"):
                    raise ValueError("не PDF")
                dest.write_bytes(data)
                by_id.setdefault(d["id"], {"id": d["id"], "title": d["title"]})
                by_id[d["id"]].update({"файл": dest.name, "байт": len(data),
                                       "источник": match[1], "oa_status": "arxiv"})
                found.append(d["title"])
                print(f"  + {d['title'][:58]:60s} {len(data)/1e6:.1f} МБ")
            except (urllib.error.HTTPError, urllib.error.URLError, ValueError, TimeoutError) as e:
                print(f"  ! {d['title'][:58]:60s} {type(e).__name__}: {e}")
        time.sleep(3.5)   # arXiv просит не чаще одного запроса в 3 секунды

    man["записи"] = [by_id.get(r["id"], r) for r in man["записи"]]
    man["скачано"] = sum(1 for r in man["записи"] if r.get("файл"))
    man["дополнено с arXiv"] = date.today().isoformat()
    (out / "manifest.json").write_text(json.dumps(man, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nнайдено на arXiv: {len(found)}; всего полных текстов: {man['скачано']}")


if __name__ == "__main__":
    main()
