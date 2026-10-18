#!/usr/bin/env python3
"""Сборка личной библиотеки проекта из OpenAlex.

Источники записей:
  * 18 работ из списка литературы gerasimov.pdf (запрос по DOI);
  * тематические запросы SEARCHES — работы с аннотациями.

Для каждой записи сохраняется происхождение: каким запросом и когда получена.
Запуск из корня проекта:  .venv/bin/python src/build_library.py
Результат: library/*.md, library/corpus.jsonl, library/corpus_provenance.json
"""
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

API = "https://api.openalex.org"
SELECT = ("id,doi,display_name,publication_year,cited_by_count,abstract_inverted_index,"
          "primary_location,authorships,type,open_access")

# Список литературы статьи: номер -> идентификатор (DOI) или название для поиска
SEEDS = {
    1: "10.3390/ijerph20032412",
    2: "10.1175/1520-0469(1972)029<0091:NIONAU>2.0.CO;2",
    3: "10.1175/1520-0469(1984)041<2052:ALESMF>2.0.CO;2",
    4: "10.1016/j.envsoft.2022.105387",
    5: "10.1145/2939672.2939738",
    6: "10.1016/j.buildenv.2021.108315",
    7: "10.1016/j.buildenv.2019.106394",
    8: "title:Fourier Neural Operator for Parametric Partial Differential Equations",
    9: "10.5194/gmd-9-2925-2016",
    10: "10.1515/rnam-2019-0010",
    11: "10.1134/S000143381902004X",
    12: "10.1175/1520-0493(1963)091<0099:GCEWTP>2.3.CO;2",
    13: "10.1063/1.857955",
    14: "10.1063/1.858280",
    15: "title:An Intriguing Failing of Convolutional Neural Networks and the CoordConv Solution",
    16: "10.1007/978-3-319-24574-4_28",
    17: "10.1609/aaai.v32i1.11671",
    18: "10.1007/s00703-003-0070-7",
}

# Тематические запросы: тема -> запрос к OpenAlex, сколько работ взять
SEARCHES = [
    ("surrogate-dispersion", "deep learning surrogate model urban pollutant dispersion", 7),
    ("les-street-canyon", "large eddy simulation street canyon pollutant dispersion", 7),
    ("cnn-flow-prediction", "convolutional neural network prediction steady flow field CFD", 7),
    ("model-evaluation", "air quality dispersion model evaluation statistical performance measures", 7),
    ("vegetation-aq", "urban trees vegetation effect on pollutant concentration street", 7),
]

# Работа идёт в корпус поиска, если аннотация не короче этого числа слов.
MIN_ABSTRACT_WORDS = 60


def get(path, **params):
    url = f"{API}{path}?" + urllib.parse.urlencode(params)
    for attempt in range(4):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                return json.load(r), url
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
            if attempt == 3:
                print(f"  ОШИБКА {e}: {url}")
                return None, url
            time.sleep(2 * (attempt + 1))


def restore_abstract(inv):
    if not inv:
        return ""
    pos = {}
    for word, places in inv.items():
        for p in places:
            pos[p] = word
    return " ".join(pos[k] for k in sorted(pos))


def slug(work):
    first = (work.get("authorships") or [{}])[0].get("author", {}).get("display_name", "anon")
    last = re.sub(r"[^A-Za-z]", "", first.split()[-1]) or "anon"
    return f"{last.lower()}_{work.get('publication_year') or 0}_{work['id'].rsplit('/', 1)[-1]}"


def record(work, query, found_by):
    loc = work.get("primary_location") or {}
    src = (loc.get("source") or {}).get("display_name") or "—"
    authors = [a["author"]["display_name"] for a in (work.get("authorships") or [])][:8]
    return {
        "id": work["id"].rsplit("/", 1)[-1],
        "title": work.get("display_name") or "",
        "abstract": restore_abstract(work.get("abstract_inverted_index")),
        "year": work.get("publication_year"),
        "doi": (work.get("doi") or "").replace("https://doi.org/", "") or None,
        "source": src,
        "authors": authors,
        "cited_by": work.get("cited_by_count", 0),
        "oa_status": (work.get("open_access") or {}).get("oa_status", "unknown"),
        "topic": found_by,
        "query": query,
        "retrieved": date.today().isoformat(),
        "searchable": len(restore_abstract(work.get("abstract_inverted_index")).split()) >= MIN_ABSTRACT_WORDS,
    }


def main():
    lib = Path("library")
    lib.mkdir(exist_ok=True)
    seen, docs, queries = {}, [], []

    print("Ссылки статьи (18 работ):")
    for n, ident in SEEDS.items():
        if ident.startswith("title:"):
            data, url = get("/works", search=ident[6:], per_page=1, select=SELECT)
            works = (data or {}).get("results") or []
        else:
            data, url = get(f"/works/doi:{urllib.parse.quote(ident, safe='')}", select=SELECT)
            works = [data] if data else []
        if not works:
            print(f"  [{n:>2}] не найдено: {ident}")
            continue
        w = works[0]
        r = record(w, url, "ссылка-статьи")
        r["ref_no"] = n
        seen[r["id"]] = r
        docs.append(r)
        print(f"  [{n:>2}] {r['year']} {r['title'][:66]}")
        queries.append({"kind": "seed", "ref_no": n, "ident": ident, "url": url})
        time.sleep(0.3)

    print("\nТематические запросы:")
    for topic, q, take in SEARCHES:
        # Порядок по релевантности (по умолчанию): сортировка по цитированиям
        # выносит наверх знаменитые, но нетематические работы.
        data, url = get("/works", search=q, per_page=30, filter="has_abstract:true",
                        select=SELECT)
        got = 0
        for w in (data or {}).get("results", []):
            if got >= take:
                break
            r = record(w, url, topic)
            if r["id"] in seen or len(r["abstract"].split()) < MIN_ABSTRACT_WORDS:
                continue
            seen[r["id"]] = r
            docs.append(r)
            got += 1
        print(f"  {topic:22s} взято {got:2d} | {q}")
        queries.append({"kind": "search", "topic": topic, "query": q, "take": take, "url": url})
        time.sleep(0.3)

    for r in docs:
        head = {
            "type": "Источник",
            "openalex_id": r["id"],
            "doi": r["doi"],
            "year": r["year"],
            "journal": r["source"],
            "cited_by": r["cited_by"],
            "oa_status": r["oa_status"],
            "topic": r["topic"],
            "вКорпусеПоиска": r["searchable"],
            "найденЗапросом": r["query"],
            "датаОбращения": r["retrieved"],
        }
        if "ref_no" in r:
            head["ссылкаВСтатье"] = r["ref_no"]
        lines = ["---"]
        lines += [f"{k}: {json.dumps(v, ensure_ascii=False) if isinstance(v, str) else v}"
                  for k, v in head.items()]
        lines += ["---", "", f"# {r['title']}", "",
                  f"[источник] {', '.join(r['authors'])} ({r['year']}). "
                  f"*{r['title']}*. {r['source']}." + (f" DOI: {r['doi']}." if r['doi'] else ""),
                  "", "## Аннотация", "",
                  (f"[источник] {r['abstract']}" if r["searchable"]
                   else "[написано] Аннотации в OpenAlex нет; работа остаётся в библиотеке "
                        "как ссылка статьи, в корпус поиска не входит."), "",
                  "## Зачем проекту", "",
                  "[написано] <заполняется при чтении>", ""]
        (lib / f"{slug({'id': 'https://openalex.org/' + r['id'], 'authorships': [{'author': {'display_name': a}} for a in r['authors']] or [{}], 'publication_year': r['year']})}.md").write_text(
            "\n".join(lines), encoding="utf-8")

    with (lib / "corpus.jsonl").open("w", encoding="utf-8") as f:
        for r in docs:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    (lib / "corpus_provenance.json").write_text(json.dumps({
        "source": "OpenAlex REST API",
        "license": "CC0 (метаданные OpenAlex); аннотации — права издателей, хранятся как цитата",
        "retrieved": date.today().isoformat(),
        "documents": len(docs),
        "seeds_from": "paper/paper.pdf, список литературы [1]-[18]",
        "queries": queries,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\nВсего документов: {len(docs)}")
    words = [len(f"{r['title']}. {r['abstract']}".split()) for r in docs]
    print(f"Слов в документе: минимум {min(words)}, в среднем {sum(words)//len(words)}, максимум {max(words)}")
    n_search = sum(1 for r in docs if r["searchable"])
    print(f"В корпусе поиска: {n_search} | только ссылкой: {len(docs) - n_search}")


if __name__ == "__main__":
    main()
