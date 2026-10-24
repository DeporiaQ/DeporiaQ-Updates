"""One-time, backed-up removal of the legacy unique product-name constraint."""
import re
import sqlite3
from pathlib import Path

def migrate_product_names(database):
    db=database.baglanti
    definition=db.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='urunler'").fetchone()[0]
    revised,count=re.subn(r'\bad\s+TEXT\s+NOT\s+NULL\s+UNIQUE\b','ad TEXT NOT NULL',definition,count=1,flags=re.I)
    if not count:return
    db.commit()
    backup=Path(database.yol).with_name(Path(database.yol).stem+'.before-0.27.1.db')
    if not backup.exists():
        with sqlite3.connect(backup) as target:db.backup(target)
    original_violations=[tuple(r) for r in db.execute('PRAGMA foreign_key_check')]
    extras=[r[0] for r in db.execute("SELECT sql FROM sqlite_master WHERE tbl_name='urunler' AND type IN ('index','trigger') AND sql IS NOT NULL")]
    columns=','.join('"'+r['name'].replace('"','""')+'"' for r in db.execute('PRAGMA table_info(urunler)'))
    revised=re.sub(r'^(CREATE\s+TABLE\s+)(?:"urunler"|urunler)',r'\1urunler_0271_copy',revised,count=1,flags=re.I)
    foreign_keys=db.execute('PRAGMA foreign_keys').fetchone()[0]
    db.execute('PRAGMA foreign_keys=OFF')
    try:
        db.execute('BEGIN IMMEDIATE');db.execute(revised)
        db.execute(f'INSERT INTO urunler_0271_copy({columns}) SELECT {columns} FROM urunler')
        db.execute('DROP TABLE urunler');db.execute('ALTER TABLE urunler_0271_copy RENAME TO urunler')
        for sql in extras:db.execute(sql)
        if [tuple(r) for r in db.execute('PRAGMA foreign_key_check')]!=original_violations:
            raise sqlite3.IntegrityError('Product cache migration changed foreign-key integrity')
        db.commit()
    except Exception:
        db.rollback();raise
    finally:db.execute('PRAGMA foreign_keys='+str(int(foreign_keys)))
