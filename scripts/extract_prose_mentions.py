#!/usr/bin/env python3
"""Extract dated list memberships from each cohort member's Wikipedia article.

Targets DENSITY, not coverage. The density measurement showed every real
person-period carries exactly one observation, and that only a SECOND
observation on an existing person-year can widen the estimate distribution.
List-article parsing finds the winner rows; prose mentions are scattered through
individual biographies and are where a second judgment on the same year lives.

Every mention must quote the article verbatim, and the quote is checked against
the fetched text before the mention is kept.
"""
from __future__ import annotations
import argparse, json, re, sys, time, urllib.parse, urllib.request, hashlib
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
from packages.ids.keys import stable_id                               # noqa: E402
from packages.llmkit.accounts import resolve_account            # noqa: E402
from packages.llmkit.budget import Budget, BudgetExhausted            # noqa: E402
from packages.llmkit.contract import load_contract                    # noqa: E402
from packages.llmkit.judges import ClaudeJudge, JudgeError            # noqa: E402
from packages.llmkit.manifest import RunManifest                      # noqa: E402

RUBRIC = REPO / "rubrics/mentions/MENTIONS.md"
SCHEMA = REPO / "rubrics/mentions/mentions.schema.json"
#: Imported, not copied. This said M1, as did two other copies.
from packages.wiki.fetch import USER_AGENT  # noqa: E402
_JSON = re.compile(r"\{.*\}", re.S)


def extract_article(page: str, timeout: int = 45) -> tuple[str, str]:
    url = ("https://en.wikipedia.org/w/api.php?"
           + urllib.parse.urlencode({
               "action": "query", "format": "json", "formatversion": "2",
               "prop": "extracts", "explaintext": "1", "redirects": "1",
               "titles": page}))
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as fh:
        raw = fh.read()
    pages = json.loads(raw)["query"]["pages"]
    text = pages[0].get("extract", "") if pages else ""
    return text, hashlib.sha256(raw).hexdigest()


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).lower().strip()


def main() -> int:
    ap = argparse.ArgumentParser(description='Extract dated list memberships from biographical prose. SPENDS MODEL QUOTA.')
    ap.add_argument("--account", default=None,
                    help=("Claude Code config dir to run under. No default: "
                          "quota headroom moves between accounts. Run "
                          "`quotapick status` first, or set CELEB_ACCOUNT."))
    ap.add_argument("--max-calls", type=int, default=16)
    ap.add_argument("--pace", type=float, default=1.5)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--cohort", default="docs/pilot-cohort.json")
    ap.add_argument("--out", default="data/pilot/observations/prose_mentions.json")
    args = ap.parse_args()

    cohort = json.loads((REPO / args.cohort).read_text())["people"]
    if args.dry_run:
        print(f"would fetch and extract {len(cohort)} articles, "
              f"{len(cohort)} model calls, cap {args.max_calls}")
        return 0

    contract = load_contract(RUBRIC, SCHEMA, "mentions-1.0")
    rubric, schema = RUBRIC.read_text(), SCHEMA.read_text()
    judge = ClaudeJudge("fable", "claude-fable-5-1", config_dir=resolve_account(args.account))
    budget = Budget(max_calls=args.max_calls)
    manifest = RunManifest(stage_name="prose-mentions", repo=REPO, args=vars(args),
                           contracts={"mentions": contract.as_dict()},
                           caps={"max_calls": args.max_calls})
    stage = manifest.stage("extract")
    raw_dir = REPO / "data/pilot/observations/raw_mentions"
    raw_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    for p in cohort:
        name = p["display_name"]
        stage.attempted += 1
        fetch_failed = False
        for attempt in range(3):
            try:
                text, sha = extract_article(name)
                break
            except Exception as exc:
                if attempt == 2:
                    text, sha = "", ""
                    fetch_failed = True
                    stage.record_failure("transient_retryable")
                    print(f"  FETCH FAIL {name}: {exc}")
                else:
                    time.sleep(4 * (attempt + 1))
        if fetch_failed:
            # Already counted in `failed`. Falling through to the empty-text
            # branch below counted it a second time as `excluded`, so the
            # manifest failed to reconcile and was never written -- the only
            # trace was a zero-byte .tmp file.
            continue
        if not text:
            # Without this the record vanishes between `attempted` and the
            # buckets. The manifest's reconciliation caught exactly that: 22
            # attempted, 19 succeeded, nothing else, three records gone.
            stage.excluded += 1
            print(f"  EMPTY {name}: no article text")
            continue
        prompt = (f"{rubric}\n\n---\n\nSchema:\n\n{schema}\n\n---\n\n"
                  f"PERSON: {name}\n\nARTICLE TEXT:\n\n{text}\n\n---\n\n"
                  "Return the JSON object and nothing else.")
        try:
            budget.spend_call(name)
        except BudgetExhausted as exc:
            manifest.halt(str(exc)); print(f"  HALT {exc}"); break
        try:
            res = judge(prompt, timeout=900)
        except JudgeError as exc:
            stage.record_failure(exc.error_type)
            print(f"  FAIL {name}: {exc.error_type}")
            continue
        (raw_dir / f"{p['wikidata_qid']}.txt").write_text(res.text)
        m = _JSON.search(res.text or "")
        if not m:
            stage.record_failure("no_json_in_response")
            print(f"  FAIL {name}: no JSON"); continue
        try:
            obj = json.loads(m.group(0))
        except json.JSONDecodeError:
            stage.record_failure("json_parse_error")
            print(f"  FAIL {name}: bad JSON"); continue
        if obj.get("schema_version") != "mentions-1.0":
            stage.record_failure("schema_validation_failed")
            print(f"  FAIL {name}: wrong schema"); continue

        kept, dropped = [], 0
        for mention in obj.get("mentions") or []:
            ev = (mention.get("evidence") or "").strip()
            if not ev or _norm(ev) not in _norm(text):
                dropped += 1
                continue
            if mention.get("shape") != "ordered_rank" and mention.get("rank"):
                mention["rank"] = None      # a rank may never be inferred
            mention["person_id"] = p["wikidata_qid"]
            mention["person"] = name
            mention["article_sha256"] = sha
            mention["mention_id"] = stable_id(
                "pm", p["wikidata_qid"], str(mention.get("year")),
                mention.get("publisher", ""), mention.get("list_name", ""))
            kept.append(mention)
        stage.succeeded += 1
        rows.extend(kept)
        print(f"  {name:22} kept={len(kept)} ungrounded_dropped={dropped}")
        for k in kept:
            print(f"      {k['year']} {k['publisher'][:18]:18} {k['list_name'][:30]:30} "
                  f"{k['shape']}" + (f" rank {k['rank']}" if k.get("rank") else ""))
        time.sleep(args.pace)

    stage.notes = {"people": len(cohort), "mentions_kept": len(rows)}
    out = REPO / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "generated_at_utc": manifest.started_at_utc,
        "contract": contract.as_dict(),
        "route": "wikipedia-api (CC BY-SA), full article extract",
        "note": ("Every mention quotes the article verbatim and the quote is "
                 "checked against the fetched text. Ungrounded mentions are "
                 "dropped, not kept with a warning."),
        "mentions": rows}, indent=2))
    mpath = manifest.write(REPO / "data/pilot/manifests")
    print(f"\nmentions kept: {len(rows)}")
    print(f"wrote {out}\nmanifest {mpath}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
