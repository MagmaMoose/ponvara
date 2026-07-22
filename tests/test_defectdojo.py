import httpx
import pytest

from securitybridge.defectdojo import DefectDojoClient


def test_reimport_fpf_posts_multipart():
    seen = {}

    def handler(request):
        seen["path"] = request.url.path
        seen["auth"] = request.headers.get("Authorization")
        seen["body"] = request.content
        return httpx.Response(201, json={"test_id": 5})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    dd = DefectDojoClient("http://dd", "tok", client=client)
    res = dd.reimport_fpf(
        product_name="svc", product_type="Dependency-Track", engagement="DT", fpf_bytes=b'{"x": 1}'
    )

    assert res["test_id"] == 5
    assert seen["path"] == "/api/v2/reimport-scan/"
    assert seen["auth"] == "Token tok"
    assert b"Dependency Track Finding Packaging Format" in seen["body"]
    assert b"svc" in seen["body"]


def test_reimport_raises_on_http_error():
    def handler(request):
        return httpx.Response(400, json={"detail": "bad"})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    dd = DefectDojoClient("http://dd", "tok", client=client)
    with pytest.raises(httpx.HTTPStatusError):
        dd.reimport_fpf(product_name="x", product_type="t", engagement="e", fpf_bytes=b"{}")
