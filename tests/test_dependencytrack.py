import httpx

from ponvara.dependencytrack import DependencyTrackClient


def test_projects_paginate_and_auth():
    calls = []

    def handler(request):
        calls.append(request)
        page = int(request.url.params["pageNumber"])
        if page == 1:
            return httpx.Response(200, json=[{"name": f"p{i}", "uuid": str(i)} for i in range(100)])
        return httpx.Response(200, json=[{"name": "last", "uuid": "x"}])

    client = httpx.Client(transport=httpx.MockTransport(handler))
    dt = DependencyTrackClient("http://dt:8080/", "key", client=client)
    projects = dt.projects()

    assert len(projects) == 101
    assert calls[0].headers["X-Api-Key"] == "key"
    assert len(calls) == 2  # stopped once a short page returned


def test_export_fpf():
    def handler(request):
        assert request.url.path.endswith("/api/v1/finding/project/abc/export")
        return httpx.Response(200, content=b'{"findings": []}')

    client = httpx.Client(transport=httpx.MockTransport(handler))
    dt = DependencyTrackClient("http://dt:8080", "key", client=client)
    assert dt.export_fpf("abc") == b'{"findings": []}'
