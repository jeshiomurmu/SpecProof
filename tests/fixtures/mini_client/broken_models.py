"""FX-04: a module whose import fails, to test environment errors (CNF-013)."""

import not_a_real_dependency  # noqa: F401
from pydantic import BaseModel


class Widget(BaseModel):
    id: str
