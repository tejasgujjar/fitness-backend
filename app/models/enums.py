from __future__ import annotations

import enum


class LogSource(str, enum.Enum):
    text = "text"
    voice = "voice"
