#!/usr/bin/env python3
"""List or extract the screenshots in a Claude Code session log.

    session_screenshots.py list    <session.jsonl> [--grep TEXT]
    session_screenshots.py extract <session.jsonl> <out_dir> <index>=<name> [<index>=<name> ...]

A session log is ~/.claude/projects/<workspace-slug>/<session-id>.jsonl. Screenshots taken by
Claude in Chrome come back as image blocks inside tool results; this finds them in order, shows
the tool call that produced each, and writes the chosen ones as numbered files. Standard library only.
"""
import base64, json, sys
from pathlib import Path


def images(log):
    uses, out = {}, []
    for line in open(log, encoding="utf-8"):
        try:
            msg = json.loads(line).get("message") or {}
        except ValueError:
            continue
        content = msg.get("content")
        if not isinstance(content, list):
            continue
        for b in content:
            if b.get("type") == "tool_use":
                uses[b["id"]] = (b.get("name", "?"), json.dumps(b.get("input"))[:160])
            elif b.get("type") == "tool_result" and isinstance(b.get("content"), list):
                imgs = [x for x in b["content"] if isinstance(x, dict) and x.get("type") == "image"]
                if imgs:
                    name, call = uses.get(b.get("tool_use_id"), ("?", ""))
                    # a batch returns several; the last is the state after its actions
                    out.append({"tool": name.split("__")[-1], "call": call, "image": imgs[-1]})
    return out


def main(a):
    if len(a) >= 2 and a[0] == "list":
        grep = a[a.index("--grep") + 1] if "--grep" in a else None
        for i, im in enumerate(images(a[1])):
            if not grep or grep in im["call"]:
                print(f"{i:>3}  {im['tool']:<14} {im['call'][:120]}")
    elif len(a) >= 4 and a[0] == "extract":
        found, out = images(a[1]), Path(a[2])
        out.mkdir(parents=True, exist_ok=True)
        for pair in a[3:]:
            i, name = pair.split("=", 1)
            src = found[int(i)]["image"]["source"]
            ext = {"image/png": "png"}.get(src.get("media_type"), "jpg")
            p = out / f"{name}.{ext}"
            p.write_bytes(base64.b64decode(src["data"]))
            print(f"{p}  {p.stat().st_size // 1024} KB")
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
