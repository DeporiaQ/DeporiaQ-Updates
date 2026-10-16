"""Prevent a privileged server key from ever entering a desktop build."""
import base64,json
from pathlib import Path

def validate(key):
    if key.startswith('sb_publishable_'):return
    try:
        segment=key.split('.')[1]
        payload=json.loads(base64.urlsafe_b64decode(segment+'='*((-len(segment))%4)))
    except Exception:raise ValueError('Geçerli publishable veya anon anahtarı gerekli') from None
    if payload.get('role')!='anon':raise ValueError('Masaüstüne yalnızca anon/publishable anahtarı gömülebilir')

if __name__=='__main__':
    validate(json.loads(Path('deporiaq_cloud.json').read_text(encoding='utf-8-sig'))['publishable_key'])
    print('İstemci anahtar türü doğrulandı.')
