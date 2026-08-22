import httpx

from ponvara.github import GitHubClient


def _client(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_code_scanning_sarif_fetches_latest_analysis():
    seen = {}

    def handler(request):
        path = request.url.path
        if path.endswith("/code-scanning/analyses"):
            return httpx.Response(200, json=[{"id": 42}])
        if path.endswith("/code-scanning/analyses/42"):
            seen["accept"] = request.headers.get("Accept")
            return httpx.Response(200, content=b'{"version":"2.1.0","runs":[]}')
        return httpx.Response(404)

    gh = GitHubClient("https://api.github.com", "tok", client=_client(handler))
    sarif = gh.code_scanning_sarif("o", "r")

    assert sarif == b'{"version":"2.1.0","runs":[]}'
    assert seen["accept"] == "application/sarif+json"


def test_code_scanning_disabled_returns_none():
    def handler(request):
        return httpx.Response(404, json={"message": "no analysis found"})

    gh = GitHubClient("https://api.github.com", "tok", client=_client(handler))
    assert gh.code_scanning_sarif("o", "r") is None


def test_code_scanning_no_analyses_returns_none():
    def handler(request):
        return httpx.Response(200, json=[])

    gh = GitHubClient("https://api.github.com", "tok", client=_client(handler))
    assert gh.code_scanning_sarif("o", "r") is None


def test_dependabot_alerts_sends_auth_and_returns_list():
    seen = {}

    def handler(request):
        seen["auth"] = request.headers.get("Authorization")
        seen["apiver"] = request.headers.get("X-GitHub-Api-Version")
        return httpx.Response(200, json=[{"number": 1}, {"number": 2}])

    gh = GitHubClient("https://api.github.com", "tok", client=_client(handler))
    alerts = gh.dependabot_alerts("o", "r")

    assert [a["number"] for a in alerts] == [1, 2]
    assert seen["auth"] == "Bearer tok"
    assert seen["apiver"] == "2022-11-28"


def test_secret_scanning_disabled_returns_none():
    def handler(request):
        return httpx.Response(403, json={"message": "secret scanning disabled"})

    gh = GitHubClient("https://api.github.com", "tok", client=_client(handler))
    assert gh.secret_scanning_alerts("o", "r") is None


def test_paginate_follows_link_header_and_sends_params_only_on_first_page():
    """_paginate must follow Link: rel="next" and suppress params on subsequent pages."""
    seen_params: list[dict] = []

    def handler(request):
        seen_params.append(dict(request.url.params))
        if not request.url.params.get("page"):
            # First page: respond with one item and a Link header pointing to page 2.
            next_url = str(request.url).split("?")[0] + "?page=2"
            return httpx.Response(
                200,
                json=[{"number": 1}],
                headers={"Link": f'<{next_url}>; rel="next"'},
            )
        # Second page: respond with one item, no further Link header.
        return httpx.Response(200, json=[{"number": 2}])

    gh = GitHubClient("https://api.github.com", "tok", client=_client(handler))
    alerts = gh.dependabot_alerts("o", "r")

    assert alerts == [{"number": 1}, {"number": 2}]
    # First request carries the per_page/state params; second uses the next URL as-is.
    assert "per_page" in seen_params[0]
    assert "per_page" not in seen_params[1]


def test_list_org_repos_skips_archived():
    def handler(request):
        return httpx.Response(
            200,
            json=[
                {"full_name": "o/live", "archived": False},
                {"full_name": "o/old", "archived": True},
            ],
        )

    gh = GitHubClient("https://api.github.com", "tok", client=_client(handler))
    assert gh.list_org_repos("o") == ["o/live"]
