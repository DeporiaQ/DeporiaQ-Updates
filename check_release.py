"""Refuse customer publication until evidence-backed release gates are completed."""
import json
from pathlib import Path
r=json.loads(Path(__file__).with_name('release_readiness.json').read_text())
missing=[name for name,done in r['required_evidence'].items() if done is not True]
if r['candidate_only'] or missing:
    raise SystemExit('Müşteri yayını kapalı. Aday sürüm; eksik doğrulamalar: '+', '.join(missing))
print('Yayın kanıtları işaretlenmiş. CI kurulum testleri ayrıca zorunludur.')
