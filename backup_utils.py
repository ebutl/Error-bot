"""backup_utils.py — gz backup + split + restore"""

import os
import gzip
import shutil
import logging
from config import BACKUP_SPLIT_BYTES
from database import backup_database, restore_database

logger = logging.getLogger(__name__)


def make_gz_backup():
    """Returns list of file paths (1 or more) — .gz file(s). Empty on failure."""
    db_file = backup_database()
    if not db_file or not os.path.exists(db_file):
        return []
    try:
        gz_path = db_file + ".gz"
        with open(db_file, 'rb') as fin:
            with gzip.open(gz_path, 'wb', compresslevel=9) as fout:
                shutil.copyfileobj(fin, fout)
        try: os.remove(db_file)
        except Exception: pass

        size = os.path.getsize(gz_path)
        files = []

        if size <= BACKUP_SPLIT_BYTES:
            files.append(gz_path)
        else:
            part = 1
            with open(gz_path, 'rb') as f:
                while True:
                    chunk = f.read(BACKUP_SPLIT_BYTES)
                    if not chunk:
                        break
                    p = f"{gz_path}.part{part}"
                    with open(p, 'wb') as out:
                        out.write(chunk)
                    files.append(p)
                    part += 1
            try: os.remove(gz_path)
            except Exception: pass

        logger.info(f"gz backup: {len(files)} file(s), total {size/1024/1024:.1f}MB")
        return files
    except Exception as e:
        logger.error(f"make_gz_backup: {e}")
        try: os.remove(db_file)
        except Exception: pass
        return []


def restore_from_path(path):
    """Restore from .db, .db.gz, or concatenated .db.gz.partN."""
    try:
        if not os.path.exists(path):
            return False, "File missing"

        lower = path.lower()
        if lower.endswith(".gz") or ".gz." in lower:
            tmp_db = path + ".tmpdb"
            with gzip.open(path, 'rb') as fin:
                with open(tmp_db, 'wb') as fout:
                    shutil.copyfileobj(fin, fout)
            ok, msg = restore_database(tmp_db)
            try: os.remove(tmp_db)
            except Exception: pass
            return ok, msg

        # Plain .db
        return restore_database(path)

    except Exception as e:
        logger.error(f"restore_from_path: {e}")
        return False, str(e)
