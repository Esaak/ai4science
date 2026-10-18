#!/usr/bin/env python3
"""Докачка открытых PDF к библиотеке проекта.

Для каждой работы из library/corpus.jsonl спрашивает у OpenAlex адрес открытой копии
(best_oa_location.pdf_url) и скачивает её в library/pdf/<та же основа>.pdf.
Закрытые работы пропускаются: в библиотеке остаётся только запись с аннотацией.

Запуск из корня проекта:  .venv/bin/python src/fetch_pdfs.py
Результат: library/pdf/*.pdf и library/pdf/manifest.json
"""
import json
import re
import time
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36"
LIB = Path("library")
OUT = LIB / "pdf"


def slug(rec):
    first = (rec["authors"] or ["anon"])[0]
    last = re.sub(r"[^A-Za-z]", "", first.split()[-1]) or "anon"
    return f"{last.lower()}_{rec['year'] or 0}_{rec['id']}"


def oa_links(ids):
    """Адреса открытых копий, по 25 работ на запрос."""
    out = {}
    for i in range(0, len(ids), 25):
        url = ("https://api.openalex.org/works?per_page=25"
               "&select=id,open_access,best_oa_location,locations"
               "&filter=ids.openalex:" + "|".join(ids[i:i + 25]))
        with urllib.request.urlopen(url, timeout=60) as r:
            for w in json.load(r)["results"]:
                loc = w.get("best_oa_location") or {}
                # Кандидаты: сначала лучшая открытая копия, затем репозитории
                # (arXiv, PMC и прочие) — у издателей часто стоит защита от загрузки.
                cands = [loc.get("pdf_url")]
                for other in (w.get("locations") or []):
                    u = other.get("pdf_url")
                    if u and u not in cands:
                        cands.append(u)
                order = {"arxiv.org": 0, "europepmc.org": 1, "ncbi.nlm.nih.gov": 1}
                cands = [u for u in cands if u]
                cands.sort(key=lambda u: min((v for k, v in order.items() if k in u), default=2))
                out[w["id"].rsplit("/", 1)[-1]] = {
                    "is_oa": (w.get("open_access") or {}).get("is_oa"),
                    "oa_status": (w.get("open_access") or {}).get("oa_status"),
                    "pdf_url": cands[0] if cands else None,
                    "кандидаты": cands,
                    "landing": loc.get("landing_page_url"),
                }
        time.sleep(0.3)
    return out


def download(url, dest):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/pdf,*/*"})
    with urllib.request.urlopen(req, timeout=90) as r:
        data = r.read()
    if not data.startswith(b"%PDF"):
        raise ValueError(f"не PDF (первые байты {data[:8]!r}, {len(data)} байт)")
    dest.write_bytes(data)
    return len(data)


def main():
    docs = [json.loads(l) for l in (LIB / "corpus.jsonl").open(encoding="utf-8")]
    links = oa_links([d["id"] for d in docs])
    OUT.mkdir(exist_ok=True)
    manifest = []

    for d in docs:
        info = links.get(d["id"], {})
        name = slug(d)
        row = {"id": d["id"], "файл": None, "title": d["title"],
               "oa_status": info.get("oa_status"), "источник": info.get("pdf_url"),
               "страница": info.get("landing")}
        if not info.get("pdf_url"):
            row["причина"] = "открытой копии нет" if not info.get("is_oa") else "только страница, прямого PDF нет"
            print(f"  — {name[:48]:50s} {row['причина']}")
        else:
            dest = OUT / f"{name}.pdf"
            if dest.exists():
                row["файл"] = dest.name
                row["байт"] = dest.stat().st_size
                print(f"  = {name[:48]:50s} уже есть")
            else:
                last = None
                for url in info.get("кандидаты") or [info["pdf_url"]]:
                    try:
                        n = download(url, dest)
                        row["файл"] = dest.name
                        row["байт"] = n
                        row["источник"] = url
                        print(f"  + {name[:48]:50s} {n/1e6:.1f} МБ")
                        break
                    except (urllib.error.HTTPError, urllib.error.URLError, ValueError, TimeoutError) as e:
                        last = f"{type(e).__name__}: {e}"
                    time.sleep(0.4)
                if not row["файл"]:
                    row["причина"] = last
                    print(f"  ! {name[:48]:50s} {last}")
        manifest.append(row)

    got = [r for r in manifest if r["файл"]]
    (OUT / "manifest.json").write_text(json.dumps({
        "собрано": date.today().isoformat(),
        "источник адресов": "OpenAlex, best_oa_location.pdf_url",
        "всего работ": len(manifest),
        "скачано": len(got),
        "записи": manifest,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nскачано {len(got)} из {len(manifest)}; "
          f"объём {sum(r.get('байт', 0) for r in got)/1e6:.1f} МБ")


if __name__ == "__main__":
    main()
