#!/usr/bin/env python3
"""Show the already-compiled ability-line node for one date."""
import argparse
import datetime as dt
import json
import re
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent
CHAIN = REPO / "data" / "question_chain.json"


def date_key(raw):
    if re.fullmatch(r"\d{4}", raw):
        return raw
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw):
        return raw[5:7] + raw[8:10]
    raise SystemExit("date must be MMDD or YYYY-MM-DD")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=dt.date.today().strftime("%m%d"))
    args = parser.parse_args()
    if not CHAIN.exists():
        raise SystemExit("question chain has not been built")
    chain = json.loads(CHAIN.read_text(encoding="utf-8"))
    key = date_key(args.date)
    node = next((item for item in chain["nodes"] if item["key"] == key), None)
    if node is None:
        raise SystemExit(
            f"{key} is outside this question chain "
            f"({chain['nodes'][0]['key']}..{chain['nodes'][-1]['key']})"
        )
    print(f"{node['key']} · {node['title']}")
    print(node["file"])
    print(" ".join(node["questions"]))
    print(f"答题卡：http://127.0.0.1:8409/?date={key}")


if __name__ == "__main__":
    main()
