from __future__ import annotations

import hashlib
from dataclasses import dataclass, field


@dataclass(slots=True)
class CompassPrincipal:
    username: str
    password: str = field(repr=False)
    access_token: str | None = field(default=None, repr=False)

    @property
    def identity(self) -> str:
        return self.username

    @property
    def cache_key(self) -> str:
        payload = f"{self.username}\0{self.password}".encode()
        return hashlib.sha256(payload).hexdigest()
