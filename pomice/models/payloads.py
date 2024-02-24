from __future__ import annotations

from typing import Optional
from typing import Union

from pydantic import AliasPath
from pydantic import Field
from pydantic import field_validator
from pydantic import model_validator
from pydantic import TypeAdapter

from pomice.models import BaseModel
from pomice.models import LavalinkVersion3Type
from pomice.models import LavalinkVersion4Type
from pomice.models import VersionedModel

__all__ = (
    "VoiceUpdatePayload",
    "TrackStartPayload",
    "TrackUpdatePayload",
    "ResumePayloadType",
    "ResumePayloadTypeAdapter",
)


class VoiceUpdatePayload(BaseModel):
    token: str = Field(validation_alias=AliasPath("event", "token"))
    endpoint: str = Field(validation_alias=AliasPath("event", "endpoint"))
    session_id: str = Field(alias="sessionId")


class TrackUpdatePayload(BaseModel):
    encoded_track: Optional[str] = Field(default=None, alias="encodedTrack")
    position: float


class TrackStartPayload(VersionedModel):
    encoded_track: Optional[str] = Field(default=None, alias="encodedTrack")
    position: float
    end_time: str = Field(default="0", alias="endTime")

    @field_validator("end_time", mode="before")
    @classmethod
    def cast_end_time(cls, value: object) -> str:
        return str(value)

    @model_validator(mode="after")
    def adjust_end_time(self) -> TrackStartPayload:
        if self.version >= LavalinkVersion3Type(3, 7, 5):
            self.end_time = None


class ResumePayload(VersionedModel):
    timeout: int


class ResumePayloadV3(ResumePayload):
    version: LavalinkVersion3Type
    resuming_key: str = Field(alias="resumingKey")


class ResumePayloadV4(ResumePayload):
    version: LavalinkVersion4Type
    resuming: bool = True


ResumePayloadType = Union[ResumePayloadV3, ResumePayloadV4]
ResumePayloadTypeAdapter = lambda **kwargs: TypeAdapter(ResumePayloadType).validate_python(kwargs)
