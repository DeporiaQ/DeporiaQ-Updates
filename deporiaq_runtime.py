"""Independent process launch and application startup acknowledgements."""
import json
import os
from pathlib import Path
import re
import sys
import traceback
from datetime import datetime


def clean_environment(source=None):
    env = dict(os.environ if source is None else source)
    for key in list(env):
        if key.upper().startswith('_PYI') or key.upper() == '_MEIPASS2':
            env.pop(key,None)
    env['PYINSTALLER_RESET_ENVIRONMENT']='1'
    return env


def log_directory():
    path = Path(os.getenv('LOCALAPPDATA',str(Path.home()))) / 'DeporiaQ' / 'logs'
    path.mkdir(parents=True,exist_ok=True)
    return path


def startup_error(exc_type, error, tb):
    try:
        path=log_directory()/'startup.log'
        if path.exists() and path.stat().st_size > 2_000_000:
            path.replace(path.with_suffix('.previous.log'))
        with path.open('a',encoding='utf-8') as stream:
            stream.write(f'\n{datetime.now().isoformat()}\n')
            traceback.print_exception(exc_type,error,tb,file=stream)
    except OSError:
        pass
    if sys.__stderr__:
        traceback.print_exception(exc_type,error,tb,file=sys.__stderr__)


def acknowledge_startup(version, argv=None):
    argv = sys.argv if argv is None else argv
    if '--after-update' not in argv:
        return False
    index=argv.index('--after-update')+1
    if index >= len(argv) or not re.fullmatch(r'[a-fA-F0-9]{32}',argv[index]):
        return False
    path=log_directory()/f'ready-{argv[index]}.json'
    temp=path.with_suffix('.tmp')
    temp.write_text(json.dumps({'version':version,'pid':os.getpid(),'ready_at':datetime.now().isoformat()}),encoding='utf-8')
    temp.replace(path)
    return True
