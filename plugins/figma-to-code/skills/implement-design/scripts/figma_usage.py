#!/usr/bin/env python3
"""Local tally of Figma requests made by this plugin. Figma exposes no usage API,
so this is the only count available. It sees only this plugin's calls on this machine.

  figma_usage.py log <source> <tier> <requests> <fileKey>   # source: figma-view | official-mcp
  figma_usage.py summary                                    # last 30 days
  figma_usage.py self-test
"""
import json, os, sys, tempfile, time
from collections import Counter

# ponytail: stored outside the plugin folder so plugin updates don't wipe it.
LOG = os.path.expanduser(os.environ.get("FIGMA_USAGE_LOG", "~/.figma-to-code/usage.jsonl"))
DAY = 86400


def log(source, tier, requests, file_key, now=None):
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    with open(LOG, "a") as f:
        f.write(json.dumps({"ts": int(now or time.time()), "source": source, "tier": tier,
                            "requests": int(requests), "file": file_key}) + "\n")


def summary(now=None):
    now = now or time.time()
    by_tier, by_file = Counter(), Counter()
    if os.path.exists(LOG):
        with open(LOG) as f:
            for line in f:
                try:
                    e = json.loads(line)
                except ValueError:
                    continue  # a torn write shouldn't break the count
                if e["ts"] >= now - 30 * DAY:
                    by_tier[(e["source"], e["tier"])] += e["requests"]
                    by_file[e["file"]] += e["requests"]
    return by_tier, by_file


def print_summary():
    by_tier, by_file = summary()
    if not by_tier:
        print("No Figma requests logged in the last 30 days.")
        return
    print("Figma requests by this plugin on this machine, last 30 days:")
    for (source, tier), n in sorted(by_tier.items()):
        print(f"  {source} {tier}: {n}")
    print("  by file: " + ", ".join(f"{k} {v}" for k, v in by_file.most_common()))


def self_test():
    global LOG
    LOG = os.path.join(tempfile.mkdtemp(), "usage.jsonl")
    now = time.time()
    log("figma-view", "tier1", 1, "abc", now)
    log("figma-view", "tier1", 2, "abc", now)
    log("figma-view", "tier2", 1, "xyz", now)
    log("figma-view", "tier1", 5, "abc", now - 31 * DAY)  # too old, not counted
    with open(LOG, "a") as f:
        f.write("{torn")
    by_tier, by_file = summary(now)
    assert by_tier == {("figma-view", "tier1"): 3, ("figma-view", "tier2"): 1}, by_tier
    assert by_file == {"abc": 3, "xyz": 1}, by_file
    print("ok")


if __name__ == "__main__":
    cmd = sys.argv[1:2]
    if cmd == ["log"] and len(sys.argv) == 6:
        log(*sys.argv[2:6])
    elif cmd == ["summary"]:
        print_summary()
    elif cmd == ["self-test"]:
        self_test()
    else:
        sys.exit(__doc__)
