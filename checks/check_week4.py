#!/usr/bin/env python3
"""Проверка онтологии и графа проекта — неделя 4 курса AI4Science.

[порождено] Скрипт написан Claude (Claude Code, модель Opus 5) 2026-10-19 по
спецификации курса, потому что `check_week4.py` в стартовом наборе недели 4
отсутствует. Источники спецификации:

  * `lectures/week_4/artefacts/practice.md` — шаги 3–5 и раздел «Формат ontology.yaml»;
  * `lectures/week_4/artefacts/ontology_template.yaml` — восемь видов проверки правил;
  * `lectures/week_4/artefacts/demo_graph/AGENTS.md`, раздел 2 — формат заметок, задач,
    связей и хранилища;
  * `lectures/week_4/artefacts/EXPECTED.md` — образец вывода.

Это замена, а не копия: расхождения с оригинальным скриптом курса возможны, и строгость
отдельных пунктов — решение автора скрипта, а не требование курса.

Запуск:
    .venv/bin/python checks/check_week4.py [ПРОЕКТ] [--strict] [--mermaid ФАЙЛ] [--no-git]

    ПРОЕКТ      корень проверяемого проекта, по умолчанию папка выше этого скрипта
    --strict    нарушенные правила графа тоже дают ненулевой код
    --mermaid   записать схему графа в файл (просмотр без Obsidian)
    --no-git    не проверять чистоту рабочего дерева

Код 0 — все обязательные пункты выполнены. Проверка идёт в закрытом мире: «связь не
найдена» значит «связь не записана», а не «связи не существует».
"""
from __future__ import annotations

import re
import subprocess
import sys
import unicodedata
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("PyYAML не установлен: .venv/bin/python -m pip install pyyaml")

NUM = {3: "трёх", 2: "двух", 10: "десяти"}


def nfc(s: str) -> str:
    """Имена файлов на macOS хранятся в NFD («й» — две кодовые точки), а в
    ontology.yaml и ссылках [[…]] те же слова записаны в NFC. Без приведения к одной
    форме совпадающие имена не совпадают."""
    return unicodedata.normalize("NFC", s)
LINK = re.compile(r"\[\[([^\]]+)\]\]")
REL_LINE = re.compile(r"^-\s*([^:\[\]]+?)\s*:\s*(.+)$")


class Report:
    """Строки вывода и два вида провалов: обязательный пункт и правило графа."""

    def __init__(self, strict: bool):
        self.strict = strict
        self.failed = False
        self.rule_failed = False

    def line(self, label: str, text: str) -> None:
        print(f"[{label}]".ljust(10) + text)

    def ok(self, text: str) -> None:
        self.line("OK", text)

    def no(self, text: str) -> None:
        self.line("НЕТ", text)
        self.failed = True

    def advice(self, text: str) -> None:
        self.line("СОВЕТ", text)

    def rule(self, text: str) -> None:
        self.line("ПРАВИЛО", text)
        self.rule_failed = True

    @property
    def code(self) -> int:
        return 1 if self.failed or (self.strict and self.rule_failed) else 0


class Note:
    """Заметка графа: заголовок из имени файла, тип, атрибуты, разделы, связи."""

    def __init__(self, path: Path, root: Path):
        self.path = path
        self.rel_path = nfc(path.relative_to(root).as_posix())
        self.name = nfc(path.stem)
        text = path.read_text(encoding="utf-8")
        self.front: dict[str, str] = {}
        body = text
        if text.startswith("---"):
            parts = text.split("---", 2)
            if len(parts) >= 3:
                for raw in parts[1].splitlines():
                    if ":" in raw:
                        k, v = raw.split(":", 1)
                        self.front[k.strip()] = v.strip()
                body = parts[2]
        self.sections = re.findall(r"^##\s+(.+?)\s*$", body, re.M)
        self.links: list[tuple[str, str]] = []
        in_links = False
        link_text: list[str] = []
        for raw in body.splitlines():
            if raw.startswith("## "):
                in_links = raw[3:].strip().startswith("Связи")
                continue
            if in_links:
                m = REL_LINE.match(raw.strip())
                if m:
                    rel = nfc(m.group(1).strip())
                    for target in LINK.findall(m.group(2)):
                        self.links.append((rel, nfc(target.strip())))
            else:
                link_text.append(raw)
        self.text_links = {nfc(t.strip()) for t in LINK.findall("\n".join(link_text))}

    @property
    def type(self) -> str | None:
        for rel, target in self.links:
            if rel == "тип":
                return target
        return self.front.get("type")


def load_ontology(path: Path, rep: Report):
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    classes = {nfc(k): v for k, v in (data.get("classes") or {}).items()}
    props = data.get("properties") or {}
    attrs = data.get("attributes") or {}
    rules = data.get("rules") or []

    def as_list(v):
        if v is None:
            return []
        return list(v) if isinstance(v, list) else [v]

    props = {
        nfc(name): {"domain": [nfc(c) for c in as_list((spec or {}).get("domain"))],
                    "range": [nfc(c) for c in as_list((spec or {}).get("range"))]}
        for name, spec in props.items()
    }
    attrs = {
        nfc(name): {"domain": [nfc(c) for c in as_list((spec or {}).get("domain"))],
                    "values": as_list((spec or {}).get("values"))}
        for name, spec in attrs.items()
    }
    for r in rules:
        chk = r.get("check") or {}
        for key in ("class", "property", "target", "source", "name", "attribute"):
            if isinstance(chk.get(key), str):
                chk[key] = nfc(chk[key])
        if isinstance(chk.get("properties"), list):
            chk["properties"] = [nfc(x) for x in chk["properties"]]
    return classes, props, attrs, rules


def collect_notes(root: Path) -> list[Note]:
    notes: list[Note] = []
    for folder in ("notes", "tasks", "reports"):
        d = root / folder
        if d.is_dir():
            notes += [Note(p, root) for p in sorted(d.glob("*.md"))]
    return notes


def main() -> int:
    args = [a for a in sys.argv[1:]]
    strict = "--strict" in args
    no_git = "--no-git" in args
    mermaid = None
    if "--mermaid" in args:
        i = args.index("--mermaid")
        if i + 1 >= len(args):
            return int(bool(sys.stderr.write("--mermaid: нужен путь к файлу\n"))) or 2
        mermaid = args[i + 1]
        del args[i:i + 2]
    positional = [a for a in args if not a.startswith("--")]
    root = Path(positional[0]).resolve() if positional else Path(__file__).resolve().parent.parent

    rep = Report(strict)
    onto_path = root / "ontology.yaml"
    print(f"== Онтология: {onto_path}")
    if not onto_path.is_file():
        rep.no("ontology.yaml не найден в корне проекта")
        print("\nПроверка не пройдена.")
        return 1
    classes, props, attrs, rules = load_ontology(onto_path, rep)

    (rep.ok if len(classes) >= 3 else rep.no)(
        f"классов — {len(classes)} (нужно не меньше {NUM[3]})")
    (rep.ok if len(rules) >= 2 else rep.no)(
        f"правил — {len(rules)} (нужно не меньше {NUM[2]})")
    for name, spec in props.items():
        unknown = [c for c in spec["domain"] + spec["range"] if c not in classes]
        if unknown:
            rep.no(f"отношение «{name}»: классов нет в онтологии — {', '.join(unknown)}")
    for name, spec in attrs.items():
        unknown = [c for c in spec["domain"] if c not in classes]
        if unknown:
            rep.no(f"атрибут «{name}»: классов нет в онтологии — {', '.join(unknown)}")

    print(f"\n== Граф проекта: {root}")

    obs = root / ".obsidian"
    have = [f for f in ("app.json", "graph.json") if (obs / f).is_file()]
    if obs.is_dir() and len(have) == 2:
        rep.ok("хранилище Obsidian инициализировано в корне проекта (.obsidian/)")
    elif obs.is_dir():
        rep.no(f".obsidian/ есть, но не хватает файлов: "
               f"{', '.join(f for f in ('app.json', 'graph.json') if f not in have)}")
    else:
        rep.no(".obsidian/ в корне проекта нет: хранилище не инициализировано")

    onto_dir = root / "ontology"
    class_notes = {nfc(p.stem) for p in onto_dir.glob("*.md")} if onto_dir.is_dir() else set()
    missing = [c for c in classes if c not in class_notes]
    extra = sorted(class_notes - set(classes))
    if not missing:
        rep.ok(f"заметки классов в ontology/ — {len(class_notes)}, "
               f"по одной на каждый класс")
    else:
        rep.no(f"заметок классов нет для: {', '.join(missing)}")
    if extra:
        rep.advice(f"заметки классов без класса в онтологии: {', '.join(extra)}")

    notes = collect_notes(root)
    node_by_key = {n.rel_path: n for n in notes}
    by_name: dict[str, list[Note]] = {}
    for n in notes:
        by_name.setdefault(n.name, []).append(n)
    clashes = [f"«{name}»: " + " и ".join(x.rel_path for x in group)
               for name, group in sorted(by_name.items()) if len(group) > 1]
    if clashes:
        rep.no("заметки с одинаковым названием — ссылки [[…]] ведут неоднозначно: "
               + "; ".join(clashes))

    typed = [n for n in notes if n.type]
    file_links = {t for n in notes for _, t in n.links if (root / t).is_file()}
    if not notes:
        rep.no("заметок объектов нет: пусты notes/, tasks/ и reports/")
    (rep.ok if len(typed) >= 10 else rep.no)(
        f"объектов с типом — {len(typed)} (нужно не меньше {NUM[10]}); "
        f"файлов проекта — {len(file_links)}")
    untyped = [n.rel_path for n in notes if not n.type]
    if untyped:
        rep.no(f"заметки без строки «- тип: [[Класс]]»: {', '.join(sorted(untyped))}")

    unknown_types = sorted({n.type for n in typed if n.type not in classes})
    if unknown_types:
        rep.advice(f"типы, которых нет в онтологии: {', '.join(unknown_types)}")

    def ancestry(cls: str) -> list[str]:
        chain, cur, seen = [], cls, set()
        while cur and cur in classes and cur not in seen:
            seen.add(cur)
            chain.append(cur)
            cur = (classes[cur] or {}).get("parent")
        return chain if chain else [cls]

    # Определяемые классы (виды проверки defined*) — множества ключей заметок.
    defined: dict[str, set[str]] = {}

    def extension(cls: str) -> set[str]:
        if cls in defined:
            return defined[cls]
        if cls == "Файл":
            return set(file_links)
        return {n.rel_path for n in typed if cls in ancestry(n.type or "")}

    def node_fits(n: Note, allowed: list[str]) -> bool:
        return True if not allowed else any(n.rel_path in extension(c) for c in allowed)

    def name_fits(name: str, allowed: list[str]) -> bool:
        """Ссылка [[имя]] годится, если подходит хоть одна заметка с этим именем."""
        if not allowed:
            return True
        if name in file_links and "Файл" in allowed:
            return True
        return any(node_fits(x, allowed) for x in by_name.get(name, []))

    links = [(n, rel, tg) for n in notes for rel, tg in n.links if rel != "тип"]
    type_links = sum(1 for n in notes for rel, _ in n.links if rel == "тип")
    rep.ok(f"типизированных связей — {len(links)}; связей «тип» с классами — {type_links}")

    def incoming(node: Note, rels: list[str]) -> list[Note]:
        return [s for s, rel, tg in links if tg == node.name and rel in rels]

    unknown_rels = sorted({rel for _, rel, _ in links if rel not in props})
    bad: list[str] = []
    for src, rel, target in links:
        if rel not in props:
            continue
        spec = props[rel]
        if not node_fits(src, spec["domain"]):
            bad.append(f"{src.rel_path} —{rel}→ {target}: источник не из "
                       f"{{{', '.join(spec['domain'])}}}")
        elif target not in by_name and target not in file_links:
            bad.append(f"{src.name} —{rel}→ {target}: "
                       f"цели нет ни среди заметок, ни среди файлов")
        elif not name_fits(target, spec["range"]):
            bad.append(f"{src.name} —{rel}→ {target}: цель не из "
                       f"{{{', '.join(spec['range'])}}}")
    bad = list(dict.fromkeys(bad))
    if bad:
        rep.no(f"связи, не согласованные с онтологией — {len(bad)}:")
        for b in bad:
            print(" " * 10 + b)
    else:
        rep.ok("типы концов всех известных связей согласованы с онтологией "
               "(локальная согласованность)")
    if unknown_rels:
        rep.advice(f"отношения, которых нет в онтологии: {', '.join(unknown_rels)}")

    for n in notes:
        loose = sorted(t for t in n.text_links
                       if t in by_name and t not in {tg for _, tg in n.links})
        if loose:
            rep.advice(f"{n.name}: ссылки в тексте без связи в разделе «Связи» — "
                       f"{', '.join(loose)}")

    if file_links:
        shown = ", ".join(sorted(file_links)[:5])
        rep.ok(f"файлов проекта, связанных с объектами, — {len(file_links)}: {shown}"
               + (" …" if len(file_links) > 5 else ""))
    else:
        rep.advice("ни один файл проекта не связан с объектом графа")

    task_keys = sorted(extension("Задача"))
    if task_keys:
        by_status: dict[str, int] = {}
        for k in task_keys:
            st = node_by_key[k].front.get("status", "без статуса")
            by_status[st] = by_status.get(st, 0) + 1
        allowed_vals = attrs.get("status", {}).get("values", [])
        wrong = [s for s in by_status if allowed_vals and s not in allowed_vals]
        text = ", ".join(f"{s} — {c}" for s, c in sorted(by_status.items()))
        (rep.no if wrong else rep.ok)(f"Задача по полю «status»: {text}")
        if wrong:
            print(" " * 10 + f"значения вне онтологии: {', '.join(wrong)}")

    # ---- правила ----
    def names(keys) -> str:
        got = sorted(node_by_key[k].name if k in node_by_key else k for k in keys)
        return "{" + ", ".join(got) + "}" if got else "пусто"

    for r in rules:
        rid = r.get("id", "?")
        chk = r.get("check")
        if not chk:
            continue
        kind = chk.get("kind")
        cls = chk.get("class")
        prop = chk.get("property")
        members = sorted(extension(cls)) if cls else []

        if kind == "defined":
            got = {k for k in members
                   if any(rel == prop and name_fits(tg, [chk.get("target")])
                          for rel, tg in node_by_key[k].links)}
            defined[chk["name"]] = got
            rep.ok(f"вывод по {rid}: {chk['name']} = {names(got)}")
        elif kind == "defined_inverse":
            want = chk.get("properties", [])
            got = {k for k in members if incoming(node_by_key[k], want)}
            defined[chk["name"]] = got
            rep.ok(f"вывод по {rid}: {chk['name']} = {names(got)}")
        elif kind == "defined_value":
            attr, vals = chk.get("attribute"), set(chk.get("values", []))
            got = {k for k in members if node_by_key[k].front.get(attr) in vals}
            defined[chk["name"]] = got
            rep.ok(f"вывод по {rid}: {chk['name']} = {names(got)}")
        elif kind == "some":
            miss = [node_by_key[k].name for k in members
                    if not any(rel == prop and name_fits(tg, [chk.get("target")])
                               for rel, tg in node_by_key[k].links)]
            _verdict(rep, rid, r, miss, f"нет связи «{prop}» к {chk.get('target')}")
        elif kind == "some_inverse":
            src_cls = chk.get("source")
            miss = [node_by_key[k].name for k in members
                    if not any(node_fits(s, [src_cls])
                               for s in incoming(node_by_key[k], [prop]))]
            _verdict(rep, rid, r, miss, f"нет входящей связи «{prop}» от {src_cls}")
        elif kind == "some_inverse_any":
            want = chk.get("properties", [])
            miss = [node_by_key[k].name for k in members
                    if not incoming(node_by_key[k], want)]
            _verdict(rep, rid, r, miss,
                     f"нет ни одной входящей связи из {{{', '.join(want)}}}")
        elif kind == "all_inverse":
            src_cls = chk.get("source")
            miss = []
            for k in members:
                node = node_by_key[k]
                outside = sorted({s.name for s in incoming(node, [prop])
                                  if not node_fits(s, [src_cls])})
                if outside:
                    miss.append(f"{node.name} ← {', '.join(outside)}")
            _verdict(rep, rid, r, miss, f"по связи «{prop}» ведут объекты не из {src_cls}")
        elif kind == "section":
            want = chk.get("section")
            miss = [node_by_key[k].name for k in members
                    if not any(sec.startswith(want) for sec in node_by_key[k].sections)]
            _verdict(rep, rid, r, miss, f"нет раздела «{want}»")
        elif kind == "disjoint_properties":
            pp = chk.get("properties", ["", ""])[:2]
            p1, p2 = pp[0], pp[1]
            pairs1 = {(s.name, tg) for s, rel, tg in links if rel == p1}
            pairs2 = {(s.name, tg) for s, rel, tg in links if rel == p2}
            miss = [f"{s} —{p1}/{p2}→ {tg}" for s, tg in sorted(pairs1 & pairs2)]
            _verdict(rep, rid, r, miss, f"связи «{p1}» и «{p2}» соединяют одну пару")
        else:
            rep.advice(f"{rid}: вид проверки «{kind}» этот скрипт не умеет")

    if mermaid:
        _write_mermaid(Path(mermaid), typed, links, file_links)
        print(" " * 10 + f"схема графа записана: {mermaid}")

    if not no_git:
        try:
            out = subprocess.run(["git", "status", "--short"], cwd=root,
                                 capture_output=True, text=True, timeout=30)
            if out.returncode != 0:
                rep.advice("git: это не репозиторий — пункт про коммиты не проверен")
            elif out.stdout.strip():
                rep.no("рабочее дерево не чисто: " +
                       ", ".join(l.strip() for l in out.stdout.strip().splitlines()[:5]))
            else:
                rep.ok("рабочее дерево чисто, всё в git")
        except Exception as e:
            rep.advice(f"git проверить не удалось: {type(e).__name__}")

    print()
    if rep.code == 0:
        print("Все обязательные пункты выполнены.")
    elif rep.failed:
        print("Проверка не пройдена: есть строки [НЕТ].")
    else:
        print("Проверка не пройдена: --strict и есть строки [ПРАВИЛО].")
    return rep.code


def _verdict(rep: Report, rid: str, r: dict, miss: list[str], why: str) -> None:
    if not miss:
        rep.ok(f"правило {rid} выполнено на графе")
        return
    rep.rule(f"{rid}: {r.get('text', '').strip()}")
    print(" " * 10 + f"{why}: {', '.join(miss[:6])}"
          + (" …" if len(miss) > 6 else ""))


def _write_mermaid(path: Path, typed: list, links: list, file_links: set) -> None:
    """Схема графа для просмотра без Obsidian: узлы заметок и файлов, подписи связей."""
    ids: dict[str, str] = {}
    palette = ["#dce6f4", "#e3eddc", "#f4e6dc", "#eadcf4", "#dcf0f4", "#f4dce6",
               "#f0f4dc", "#e8e8e8"]
    classes_seen: list[str] = []

    def nid(name: str) -> str:
        if name not in ids:
            ids[name] = f"n{len(ids)}"
        return ids[name]

    out = ["# Граф проекта", "",
           "Схема построена `checks/check_week4.py --mermaid`. Цвет — класс объекта,",
           "скруглённые узлы — файлы проекта.", "",
           "```mermaid", "graph LR"]
    for n in sorted(typed, key=lambda x: x.name):
        cls = n.type or "без класса"
        if cls not in classes_seen:
            classes_seen.append(cls)
        out.append(f'  {nid(n.name)}["{n.name}"]:::c{classes_seen.index(cls) % 8}')
    for f in sorted(file_links):
        out.append(f'  {nid(f)}[("{f}")]:::file')
    for src, rel, tgt in links:
        if src.name in ids and tgt in ids:
            out.append(f"  {nid(src.name)} -->|{rel}| {nid(tgt)}")
    for i, cls in enumerate(classes_seen[:8]):
        out.append(f"  classDef c{i} fill:{palette[i]},stroke:#5b6b7a;")
    out.append("  classDef file fill:#faf7ef,stroke:#a8945b;")
    out.append("```")
    out.append("")
    out.append("Классы в схеме: " + ", ".join(classes_seen) + ".")
    path.write_text("\n".join(out) + "\n", encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
