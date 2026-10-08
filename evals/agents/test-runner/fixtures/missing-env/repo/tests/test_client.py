from client import auth_header, base_url


def test_auth_header_is_bearer():
    assert auth_header()["Authorization"].startswith("Bearer ")


def test_auth_header_has_token():
    assert len(auth_header()["Authorization"]) > len("Bearer ")


def test_base_url():
    assert base_url().startswith("https://")
