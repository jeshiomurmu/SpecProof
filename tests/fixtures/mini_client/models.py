"""FX-04 models: size is required (doc: optional, absent from the doc sample), created_at is a
str (doc: Integer), and serial does not exist in the doc."""

from pydantic import BaseModel


class Widget(BaseModel):
    id: str
    name: str
    color: str
    size: int
    created_at: str
    serial: str
