from elastio_inspector.handler import _is


def test__is():
    s = "derp"
    r = _is(s)
    assert r is False

    s = "eLastio"
    r = _is(s)
    assert r is True

    s = "elastio"
    r = _is(s)
    assert r is True
