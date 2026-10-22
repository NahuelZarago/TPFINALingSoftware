"""Tests del protocolo JSON."""

from __future__ import annotations

from decimal import Decimal

import pytest

from tpfi.protocol import (
    ProtocolError,
    decode,
    decode_json,
    encode,
    request_id,
    response,
    validate_request,
    wire_payload,
)


def test_roundtrip() -> None:
    msg = {"UUID": "1", "ACTION": "list", "texto": "Concepción"}
    raw = encode(msg)
    assert raw.endswith(b"\n")
    assert decode(raw) == msg


def test_encode_decimal() -> None:
    assert decode(encode({"a": Decimal("3"), "b": Decimal("1.5")})) == {
        "a": 3,
        "b": 1.5,
    }


def test_encode_list() -> None:
    assert decode_json(encode([{"a": 1}, {"a": 2}])) == [{"a": 1}, {"a": 2}]


def test_encode_rejects_unknown_type() -> None:
    with pytest.raises(TypeError):
        encode({"a": object()})


@pytest.mark.parametrize("raw", [b"no es json", b"[1, 2]", b"\xff\xfe", b""])
def test_decode_errors(raw: bytes) -> None:
    with pytest.raises(ProtocolError):
        decode(raw)


def test_decode_json_error() -> None:
    with pytest.raises(ProtocolError):
        decode_json(b"\xff")


def test_decode_str() -> None:
    assert decode('{"a": 1}') == {"a": 1}


@pytest.mark.parametrize(
    "request_",
    [
        {"ACTION": "list"},
        {"UUID": "1"},
        {"UUID": "1", "ACTION": "borrar"},
        {"UUID": "1", "ACTION": "get"},
        {"UUID": "1", "ACTION": "set"},
    ],
)
def test_validate_rejects(request_: dict[str, str]) -> None:
    with pytest.raises(ProtocolError):
        validate_request(request_)


def test_validate_accepts() -> None:
    assert validate_request({"UUID": "1", "ACTION": "get", "ID": "A"})
    assert validate_request({"UUID": "1", "ACTION": "set", "id": "A"})
    assert validate_request({"UUID": "1", "ACTION": "list"})
    assert validate_request({"UUID": "1", "ACTION": "subscribe"})


def test_request_id_variants() -> None:
    assert request_id({"ID": "A"}) == "A"
    assert request_id({"id": "B"}) == "B"
    assert request_id({}) is None


def test_response_shape() -> None:
    msg = response({"UUID": "1", "ACTION": "get", "ID": "A"}, "OK", {"x": 1})
    assert msg == {
        "UUID": "1",
        "ACTION": "get",
        "STATUS": "OK",
        "ID": "A",
        "DATA": {"x": 1},
    }


def test_wire_payload_record_and_list() -> None:
    ok = response({"UUID": "1", "ACTION": "get", "ID": "A"}, "OK", {"id": "A"})
    assert wire_payload(ok) == {"id": "A"}
    listing = response({"UUID": "1", "ACTION": "list"}, "OK", [{"id": "A"}])
    assert wire_payload(listing) == [{"id": "A"}]
    empty = response({"UUID": "1", "ACTION": "list"}, "OK", [])
    assert wire_payload(empty) == []


def test_wire_payload_ack_and_error() -> None:
    ack = wire_payload(response({"UUID": "1", "ACTION": "subscribe"}, "OK"))
    assert ack == {"UUID": "1", "ACTION": "subscribe", "STATUS": "OK"}
    err = wire_payload(response({"UUID": "1", "ACTION": "get"}, "Error", "falla"))
    assert err["STATUS"] == "Error"
    assert err["ERROR"] == "falla"
