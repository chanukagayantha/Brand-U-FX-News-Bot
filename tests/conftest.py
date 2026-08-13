import os

import pytest

from src.storage import Storage


@pytest.fixture
def storage(tmp_path):
    db_path = os.path.join(tmp_path, "test.db")
    s = Storage(db_path)
    yield s
    s.close()
