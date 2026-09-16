from app.security import create_access_token, decode_access_token


def test_create_and_decode_access_token():
    token = create_access_token(123)

    user_id = decode_access_token(token)

    assert user_id == 123


def test_access_token_is_string():
    token = create_access_token(123)

    assert isinstance(token, str)