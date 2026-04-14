import uuid

from telegram.ext import ContextTypes


def start_request(context: ContextTypes.DEFAULT_TYPE) -> str:
    request_id = uuid.uuid4().hex
    context.chat_data["request_id"] = request_id
    return request_id


def get_request_id(context: ContextTypes.DEFAULT_TYPE) -> str:
    request_id = context.chat_data.get("request_id")
    if not request_id:
        request_id = start_request(context)
    return request_id


def end_request(context: ContextTypes.DEFAULT_TYPE) -> None:
    context.chat_data.pop("request_id", None)
