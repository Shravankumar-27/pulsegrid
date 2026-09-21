from app.services.providers.bookmyshow_response import (
    classify_response,
)


def test_response_with_showtimes():
    data = {
        "data": {
            "showtimeWidgets": [],
        }
    }

    assert classify_response(data) == "showtimes"


def test_response_without_showtimes_is_not_on_sale():
    data = {
        "data": {
            "someOtherField": [],
        }
    }

    assert classify_response(data) == "not_on_sale"


def test_invalid_response():
    assert classify_response({}) == "invalid"


def test_non_dict_response_is_invalid():
    assert classify_response([]) == "invalid"