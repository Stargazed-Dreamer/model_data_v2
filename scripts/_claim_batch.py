import json, datetime, sys
path = 'docs/batch_claim_ledger.jsonl'
batch_id = sys.argv[1]
platform_id = sys.argv[2]
rows = [json.loads(l) for l in open(path, encoding='utf-8')]
target = None
for r in rows:
    if r['batch_id'] == batch_id:
        target = r
        break
if not target:
    raise SystemExit('batch not found')
if target['status'] != 'pending':
    raise SystemExit(f"batch already {target['status']} by {target.get('claimed_by')}")
target['status'] = 'claimed'
target['claimed_by'] = platform_id
target['claimed_at'] = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%S+00:00')
with open(path, 'w', encoding='utf-8', newline='\n') as f:
    for r in rows:
        f.write(json.dumps(r, ensure_ascii=False, separators=(',', ':')) + '\n')
print('claimed:', json.dumps(target, ensure_ascii=False))
