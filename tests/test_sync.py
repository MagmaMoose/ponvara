import pytest

from ponvara.sync import run_sync


class FakeDT:
    def __init__(self, projects):
        self._p = projects

    def projects(self):
        return self._p

    def export_fpf(self, uuid):
        if uuid == "bad":
            raise RuntimeError("boom")
        return b"{}"


class FakeDD:
    def __init__(self):
        self.imported = []

    def reimport_fpf(self, *, product_name, product_type, engagement, fpf_bytes):
        self.imported.append(product_name)
        return {"test_id": 1}


def test_run_sync_isolates_per_project_failures():
    dt = FakeDT(
        [
            {"name": "ok", "uuid": "1", "version": "1.0"},
            {"name": "bad", "uuid": "bad"},  # export raises -> skipped, not fatal
            {"name": "nouuid"},  # no uuid -> skipped silently
            {"uuid": "noname"},  # no name -> skipped silently
        ]
    )
    dd = FakeDD()
    summary = run_sync(dt, dd, product_type="DT", engagement="E", log=lambda m: None)

    assert summary.projects == 4
    assert summary.synced == 1
    assert summary.skipped == 1
    assert dd.imported == ["ok"]


class ExplodingDT:
    def projects(self):
        raise RuntimeError("dt down")

    def export_fpf(self, uuid):
        return b""


def test_run_sync_list_failure_is_fatal():
    with pytest.raises(RuntimeError):
        run_sync(ExplodingDT(), FakeDD(), product_type="t", engagement="e", log=lambda m: None)
