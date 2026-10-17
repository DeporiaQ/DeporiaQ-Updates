import json
import os
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from deporiaq_runtime import clean_environment, acknowledge_startup, startup_error

def test_frozen_environment_is_not_inherited():
    source={'PATH':'keep','LOCALAPPDATA':'user','_PYI_PARENT_PROCESS_LEVEL':'1','_PYI_ARCHIVE_FILE':'old.exe','_PYI_APPLICATION_HOME_DIR':'gone','_PYI_SPLASH_IPC':'0','_MEIPASS2':'gone'}
    clean=clean_environment(source)
    assert clean=={'PATH':'keep','LOCALAPPDATA':'user','PYINSTALLER_RESET_ENVIRONMENT':'1'}
    assert '_PYI_PARENT_PROCESS_LEVEL' in source

def test_window_readiness_is_versioned_and_atomic(tmp_path,monkeypatch):
    monkeypatch.setenv('LOCALAPPDATA',str(tmp_path));token='a'*32
    assert acknowledge_startup('0.23.0',['app','--after-update',token])
    receipt=tmp_path/'DeporiaQ'/'logs'/f'ready-{token}.json'
    data=json.loads(receipt.read_text())
    assert data['version']=='0.23.0' and data['pid']==os.getpid()
    assert not receipt.with_suffix('.tmp').exists()

def test_no_receipt_for_missing_or_invalid_token(tmp_path,monkeypatch):
    monkeypatch.setenv('LOCALAPPDATA',str(tmp_path))
    for args in ([],['app','--after-update'],['app','--after-update','../escape']):
        assert not acknowledge_startup('0.23.0',args)
    assert not (tmp_path/'DeporiaQ').exists()

def test_startup_failure_leaves_log(tmp_path,monkeypatch):
    monkeypatch.setenv('LOCALAPPDATA',str(tmp_path))
    try:raise ValueError('fixture startup failure')
    except ValueError as e:startup_error(type(e),e,e.__traceback__)
    assert 'fixture startup failure' in (tmp_path/'DeporiaQ/logs/startup.log').read_text()

def test_installer_gets_fresh_environment_and_log(tmp_path,monkeypatch):
    import deporiaq_guncelleme_bildirici as updater
    monkeypatch.setenv('LOCALAPPDATA',str(tmp_path))
    monkeypatch.setenv('_PYI_PARENT_PROCESS_LEVEL','1')
    calls=[]
    class Result:returncode=0
    monkeypatch.setattr(updater.subprocess,'run',lambda args,**kwargs:(calls.append((args,kwargs)) or Result()))
    assert updater.kurulumu_calistir(tmp_path/'installer.exe').returncode==0
    args,options=calls[0]
    assert '/VERYSILENT' in args and any(a.startswith('/LOG=') for a in args)
    assert options['env']['PYINSTALLER_RESET_ENVIRONMENT']=='1'
    assert '_PYI_PARENT_PROCESS_LEVEL' not in options['env']

def test_installer_failure_is_not_converted_to_success(tmp_path,monkeypatch):
    import deporiaq_guncelleme_bildirici as updater
    monkeypatch.setenv('LOCALAPPDATA',str(tmp_path))
    class Result:returncode=5
    monkeypatch.setattr(updater.subprocess,'run',lambda *args,**kwargs:Result())
    assert updater.kurulumu_calistir(tmp_path/'installer.exe').returncode==5

def test_manifest_rejects_path_like_version(monkeypatch):
    import deporiaq_guncelleme_bildirici as updater
    class Response:
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def read(self,*args):return json.dumps({'version':'../../bad','download_url':'https://example.com/file.exe','sha256':'a'*64}).encode()
    monkeypatch.setattr(updater,'ayarlari_oku',lambda:'https://example.com/manifest')
    monkeypatch.setattr(updater.urllib.request,'urlopen',lambda *args,**kwargs:Response())
    assert updater.manifest_getir() is None

def test_updater_follows_saved_language_and_keeps_legacy_fallback(tmp_path,monkeypatch):
    import deporiaq_guncelleme_bildirici as updater
    monkeypatch.setenv('LOCALAPPDATA',str(tmp_path))
    settings=tmp_path/'DeporiaQ'/'ayarlar.json';settings.parent.mkdir()
    for data,expected in [({'ui_language':'en'},True),
                          ({'uygulama_dili':'en'},True),
                          ({'ui_language':'tr','uygulama_dili':'en'},False),
                          ({'ui_language':'invalid'},False)]:
        settings.write_text(json.dumps(data),encoding='utf-8')
        assert updater.ingilizce_mi() is expected
    settings.write_text('{invalid',encoding='utf-8')
    assert updater.ingilizce_mi() is False

def test_english_update_notes_and_installer_language(tmp_path,monkeypatch):
    import deporiaq_guncelleme_bildirici as updater
    monkeypatch.setenv('LOCALAPPDATA',str(tmp_path))
    monkeypatch.setattr(updater,'ingilizce_mi',lambda:True)
    class Response:
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def read(self,*args):return json.dumps({'version':'9.0.0','download_url':'https://example.com/setup.exe','sha256':'a'*64,'notes':'Yeni özellikler','notes_en':'New features'}).encode()
    monkeypatch.setattr(updater,'ayarlari_oku',lambda:'https://example.com/manifest')
    monkeypatch.setattr(updater.urllib.request,'urlopen',lambda *args,**kwargs:Response())
    manifest=updater.manifest_getir()
    assert updater.surum_notlari(manifest)=='New features'
    assert updater.surum_notlari(manifest,False)=='Yeni özellikler'
    assert updater.surum_notlari({'notes':'Türkçe notlar'})=='Your stock and business data will be preserved.'
    calls=[]
    class Result:returncode=0
    monkeypatch.setattr(updater.subprocess,'run',lambda args,**kwargs:(calls.append(args) or Result()))
    assert updater.kurulumu_calistir(tmp_path/'installer.exe').returncode==0
    assert '/LANG=english' in calls[0] and '/VERYSILENT' in calls[0]

