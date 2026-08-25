import os
import tempfile
from pathlib import Path


test_data_dir = Path(tempfile.mkdtemp(prefix="torrentflow-tests-"))
os.environ["TORRENTFLOW_DATABASE_URL"] = f"sqlite+aiosqlite:///{(test_data_dir / 'torrentflow.db').as_posix()}"
os.environ["TORRENTFLOW_ADMIN_PASSWORD"] = "change-me"
os.environ["TORRENTFLOW_SESSION_SECRET"] = "test-session-secret-is-not-used-in-production"
os.environ.pop("TORRENTFLOW_ENV", None)
