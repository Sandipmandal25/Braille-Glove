from pydantic import BaseModel, Field


class MessageResponse(BaseModel):
    id:          int
    external_id: str
    sender_id:   str
    sender_name: str
    text:        str
    status:      str
    timestamp:   float


class MessageListResponse(BaseModel):
    items: list[MessageResponse]
    total: int


class FavoriteResponse(BaseModel):
    slot:        int
    name:        str
    telegram_id: str


class FavoriteUpsertRequest(BaseModel):
    name:        str
    telegram_id: str

    model_config = {"str_strip_whitespace": True}


class DeviceStatusResponse(BaseModel):
    connected:        bool
    mode:             str
    queue_length:     int
    cursor_position:  int
    unread_count:     int
    compose_slot:     int
    compose_text:     str
