import base64,json,sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from check_client_config import validate

def token(role):return 'header.'+base64.urlsafe_b64encode(json.dumps({'role':role}).encode()).decode().rstrip('=')+'.signature'

def test_publishable_and_anon_allowed():
 validate('sb_publishable_example');validate(token('anon'))

@pytest.mark.parametrize('key',[token('service_role'),'sb_secret_example','invalid'])
def test_privileged_or_unknown_build_keys_denied(key):
 with pytest.raises(ValueError):validate(key)
