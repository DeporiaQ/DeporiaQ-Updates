import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'server'))
from support_worker import run_once

def test_only_mark_sent_after_smtp_acceptance():
 calls=[]
 def rpc(name,p):
  calls.append((name,p))
  if name=='dpq_claim_support':return {'id':'ticket','lease':'lease'}
 def fail(t):raise RuntimeError('mail unavailable')
 assert not run_once(rpc,fail)
 assert calls[-1][1]['p_sent'] is False
 assert run_once(rpc,lambda _:None)
 assert calls[-1][1]['p_sent'] is True
