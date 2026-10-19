#!/usr/bin/env python3
"""Создать заметки классов в ontology/ по ontology.yaml (через yaml)."""

from pathlib import Path
import yaml

ONT = "ontology.yaml"
OUT = Path("ontology")


def main():
    with open(ONT, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    classes = data["classes"]
    props = data["properties"]
    attrs = data["attributes"]

    OUT.mkdir(exist_ok=True)

    for name, info in classes.items():
        parent = info["parent"]
        definition = info["definition"]

        # Отношения, где этот класс — domain
        rel_lines = []
        for pname, spec in props.items():
            doms = spec["domain"]
            if not isinstance(doms, list):
                doms = [doms]
            if name in doms:
                rng = spec["range"]
                rng_str = ", ".join(rng) if isinstance(rng, list) else rng
                rel_lines.append(f"- {pname}: → {rng_str}")

        # Атрибуты
        attr_lines = [a for a, spec in attrs.items() if spec.get("domain") == name]

        lines = [
            "---",
            "kind: класс",
            "---",
            f"# {name}",
            "",
            definition,
            "",
            "## Отношения от этого класса",
        ]
        lines += rel_lines if rel_lines else ["- нет"]
        lines += ["", "## Атрибуты"]
        lines += attr_lines if attr_lines else ["- нет"]
        lines += ["", "## Связи"]
        if parent:
            lines.append(f"- подклассОт: [[{parent}]]")

        (OUT / f"{name}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"  {name}.md" + (f" (подкласс {parent})" if parent else " (верхний)"))


if __name__ == "__main__":
    main()