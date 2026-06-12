from conftest import register_and_login


async def create_workspace(client, headers, name="Team Docs"):
    res = await client.post("/workspaces", json={"name": name}, headers=headers)
    assert res.status_code == 201, res.text
    return res.json()


async def test_create_workspace_makes_caller_owner(client):
    headers = await register_and_login(client)
    workspace = await create_workspace(client, headers)
    assert workspace["role"] == "owner"

    res = await client.get("/workspaces", headers=headers)
    assert res.status_code == 200
    listed = res.json()
    assert len(listed) == 1
    assert listed[0]["id"] == workspace["id"]


async def test_workspaces_require_auth(client):
    res = await client.get("/workspaces")
    assert res.status_code == 401


async def test_owner_can_add_member(client):
    owner_headers = await register_and_login(client, email="owner@example.com")
    await register_and_login(client, email="member@example.com")
    workspace = await create_workspace(client, owner_headers)

    res = await client.post(
        f"/workspaces/{workspace['id']}/members",
        json={"email": "member@example.com"},
        headers=owner_headers,
    )
    assert res.status_code == 201
    assert res.json()["role"] == "member"

    res = await client.get(f"/workspaces/{workspace['id']}/members", headers=owner_headers)
    emails = {m["email"] for m in res.json()}
    assert emails == {"owner@example.com", "member@example.com"}


async def test_member_cannot_add_members(client):
    owner_headers = await register_and_login(client, email="owner@example.com")
    member_headers = await register_and_login(client, email="member@example.com")
    await register_and_login(client, email="other@example.com")
    workspace = await create_workspace(client, owner_headers)

    await client.post(
        f"/workspaces/{workspace['id']}/members",
        json={"email": "member@example.com"},
        headers=owner_headers,
    )
    res = await client.post(
        f"/workspaces/{workspace['id']}/members",
        json={"email": "other@example.com"},
        headers=member_headers,
    )
    assert res.status_code == 403


async def test_outsider_gets_404_not_403(client):
    owner_headers = await register_and_login(client, email="owner@example.com")
    outsider_headers = await register_and_login(client, email="outsider@example.com")
    workspace = await create_workspace(client, owner_headers)

    res = await client.get(f"/workspaces/{workspace['id']}/members", headers=outsider_headers)
    assert res.status_code == 404


async def test_add_member_unknown_email_404(client):
    headers = await register_and_login(client)
    workspace = await create_workspace(client, headers)
    res = await client.post(
        f"/workspaces/{workspace['id']}/members",
        json={"email": "ghost@example.com"},
        headers=headers,
    )
    assert res.status_code == 404


async def test_add_member_twice_conflicts(client):
    owner_headers = await register_and_login(client, email="owner@example.com")
    await register_and_login(client, email="member@example.com")
    workspace = await create_workspace(client, owner_headers)

    payload = {"email": "member@example.com"}
    await client.post(f"/workspaces/{workspace['id']}/members", json=payload, headers=owner_headers)
    res = await client.post(
        f"/workspaces/{workspace['id']}/members", json=payload, headers=owner_headers
    )
    assert res.status_code == 409
