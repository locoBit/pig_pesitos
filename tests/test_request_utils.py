from pig_pesitos.utils.request import end_request, get_request_id, start_request


class DummyContext:
    def __init__(self) -> None:
        self.chat_data: dict[str, str] = {}


def test_start_request_sets_request_id() -> None:
    context = DummyContext()

    request_id = start_request(context)  # type: ignore[arg-type]

    assert "request_id" in context.chat_data
    assert context.chat_data["request_id"] == request_id
    assert len(request_id) == 32  # uuid4 hex length


def test_get_request_id_reuses_existing() -> None:
    context = DummyContext()
    context.chat_data["request_id"] = "existing"

    request_id = get_request_id(context)  # type: ignore[arg-type]

    assert request_id == "existing"


def test_get_request_id_generates_when_missing() -> None:
    context = DummyContext()

    request_id = get_request_id(context)  # type: ignore[arg-type]

    assert "request_id" in context.chat_data
    assert context.chat_data["request_id"] == request_id


def test_end_request_clears_request_id() -> None:
    context = DummyContext()
    context.chat_data["request_id"] = "existing"

    end_request(context)  # type: ignore[arg-type]

    assert "request_id" not in context.chat_data
