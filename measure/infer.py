"Classify private JSONL packets using a local schema-constrained inference server."

import argparse
import hashlib
import json
import threading
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

SCHEMA = json.loads((Path(__file__).parent / "schemas/leadership.json").read_text())


def payload(model, prompt, packet, schema=SCHEMA):
    user = {k: v for k, v in packet.items() if k not in ("case_id", "packet_sha256")}
    return {
        "model": model,
        "temperature": 0.0,
        "max_tokens": 1024,
        "seed": int(hashlib.sha256(packet["case_id"].encode()).hexdigest()[:8], 16),
        "messages": [
            {"role": "system", "content": prompt},
            {"role": "user", "content": json.dumps(user, ensure_ascii=False)},
        ],
        "response_format": {"type": "json_schema", "json_schema": {"name": "Review", "strict": True, "schema": schema}},
    }


def call(url, body, timeout):
    req = urllib.request.Request(
        url.rstrip("/") + "/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--packets", required=True)
    ap.add_argument("--prompt", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--urls", nargs="+", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--timeout", type=int, default=600)
    ap.add_argument("--schema", help="JSON schema file (default: the pair-review schema)")
    a = ap.parse_args()
    prompt = Path(a.prompt).read_text()
    schema = json.loads(Path(a.schema).read_text()) if a.schema else SCHEMA
    prompt_sha = hashlib.sha256(prompt.encode()).hexdigest()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    with Path(a.packets).open() as handle:
        packets = [json.loads(label) for label in handle]
    assert packets, "expected nonempty packets"
    assert len({p["case_id"] for p in packets}) == len(packets), "duplicate packet identifiers"
    assert a.workers > 0, f"expected workers > 0, got {a.workers}"
    schema_sha = hashlib.sha256(json.dumps(schema, sort_keys=True).encode()).hexdigest()
    todo = []
    for p in packets:
        f = out / f"{p['case_id']}.json"
        if f.exists():
            saved = json.loads(f.read_text())
            expected = {
                "packet_sha256": p["packet_sha256"],
                "prompt_sha256": prompt_sha,
                "model": a.model,
                "schema_sha256": schema_sha,
            }
            if any(saved.get(k) != v for k, v in expected.items()):
                raise ValueError("existing label has a different or incomplete measurement specification")
            if saved["status"] == "success":
                continue
        todo.append(p)
    print(f"{len(packets)} packets, {len(todo)} to run, prompt sha {prompt_sha[:12]}", flush=True)
    lock, done = (threading.Lock(), [0, 0])

    def work(i, p):
        url = a.urls[i % len(a.urls)]
        rec = {
            "case_id": p["case_id"],
            "packet_sha256": p["packet_sha256"],
            "prompt_sha256": prompt_sha,
            "model": a.model,
            "schema_sha256": schema_sha,
        }
        try:
            body = call(url, payload(a.model, prompt, p, schema), a.timeout)
            msg = body["choices"][0]["message"]
            rec.update(status="success", label=json.loads(msg.get("content") or ""), usage=body.get("usage", {}))
        except (urllib.error.URLError, json.JSONDecodeError, KeyError, TimeoutError) as e:
            rec.update(status="error", error=repr(e)[:500])
        (out / f"{p['case_id']}.json").write_text(json.dumps(rec, ensure_ascii=False))
        with lock:
            done[rec["status"] != "success"] += 1
            if sum(done) % 200 == 0:
                print(f"progress ok={done[0]} err={done[1]}", flush=True)

    with ThreadPoolExecutor(a.workers) as ex:
        for f in as_completed([ex.submit(work, i, p) for i, p in enumerate(todo)]):
            f.result()
    print(f"DONE ok={done[0]} err={done[1]}", flush=True)
    if done[1]:
        raise RuntimeError(f"inference failed for {done[1]} packets")


if __name__ == "__main__":
    main()
