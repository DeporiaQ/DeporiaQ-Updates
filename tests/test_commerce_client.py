import json
import sys
from pathlib import Path
from types import SimpleNamespace
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from deporiaq_commerce import CommerceClient,CommerceError,SHORTCUTS,PLANS

class FakeCloud:
    def __init__(self,tmp_path):
        self.vt=SimpleNamespace(yol=tmp_path/'business.db');self.bagli=True;self.company_id='company';self.cihaz_kimligi='device';self.calls=[];self.responses=[]
    def _istek(self,path,method,payload):
        self.calls.append(payload)
        answer=self.responses.pop(0) if self.responses else {'ok':True}
        if isinstance(answer,Exception):raise answer
        return answer

def test_ambiguous_network_retry_survives_restart(tmp_path):
    cloud=FakeCloud(tmp_path);cloud.responses=[RuntimeError('connection lost'),{'found':True,'result':{'sale':'one'}}]
    c=CommerceClient(cloud)
    with pytest.raises(CommerceError):c.mutate('sale',{'quantity':1})
    request=cloud.calls[-1]['p_payload']['request_id']
    c=CommerceClient(cloud)
    with pytest.raises(CommerceError,match='belirsiz'):c.mutate('sale',{'quantity':2})
    assert c.reconcile()=={'sale':'one'}
    assert cloud.calls[-1]['p_payload']['request_id']==request
    c.mutate('sale',{'quantity':1})
    assert cloud.calls[-1]['p_payload']['request_id']!=request

def test_known_rejection_does_not_stick(tmp_path):
    cloud=FakeCloud(tmp_path);cloud.responses=[RuntimeError('Cloud isteği reddedildi (400): DPQ_STOCK: yetersiz')]
    c=CommerceClient(cloud)
    with pytest.raises(CommerceError):c.mutate('sale',{'quantity':2})
    assert c.mutate('sale',{'quantity':1})=={'ok':True}

def test_no_offline_fallback(tmp_path):
    cloud=FakeCloud(tmp_path);cloud.bagli=False;c=CommerceClient(cloud)
    with pytest.raises(CommerceError,match='Çevrimdışı'):c.mutate('sale',{'quantity':1})
    assert cloud.calls==[]

def test_exactly_five_unique_shortcuts_and_device_limits():
    assert len(SHORTCUTS)==len({r[0] for r in SHORTCUTS})==5
    assert [r[2] for r in PLANS]==[1,1,3,6,20]


def test_pending_not_found_retries_same_uuid(tmp_path):
    cloud=FakeCloud(tmp_path);cloud.responses=[RuntimeError('network'),{'found':False},{'ok':True}]
    client=CommerceClient(cloud)
    with pytest.raises(CommerceError):client.mutate('sale',{'quantity':1})
    uid=cloud.calls[0]['p_payload']['request_id']
    client.reconcile()
    assert cloud.calls[-1]['p_action']=='sale'
    assert cloud.calls[-1]['p_payload']['request_id']==uid

def test_atomic_sql_constraint_failure_can_be_corrected(tmp_path):
    cloud=FakeCloud(tmp_path);cloud.responses=[RuntimeError('Cloud isteği reddedildi (409): duplicate key')]
    client=CommerceClient(cloud)
    with pytest.raises(CommerceError):client.mutate('reserve',{'reference':'duplicate'})
    assert client.mutate('reserve',{'reference':'corrected'})=={'ok':True}
