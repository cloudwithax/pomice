from typing import Union

from pydantic import Field
from pydantic import TypeAdapter

from pomice.models import BaseModel
from pomice.models import LavalinkVersion
from pomice.models import LavalinkVersion3Type
from pomice.models import LavalinkVersion4Type

__all__ = ("ResumePayload", "ResumePayloadV3", "ResumePayloadV4")


class ResumePayload(BaseModel):
    version: LavalinkVersion
    timeout: int

    def model_dump(self) -> dict:
        return super().model_dump(by_alias=True, exclude={"version"})


class ResumePayloadV3(BaseModel):
    version: LavalinkVersion3Type
    timeout: int
    resuming_key: str = Field(serialization_alias="resumingKey")


class ResumePayloadV4(BaseModel):
    version: LavalinkVersion4Type
    timeout: int
    resuming: bool = True


ResumePayloadType = Union[ResumePayloadV3, ResumePayloadV4]
ResumePayloadTypeAdapter = lambda **kwargs: TypeAdapter(ResumePayloadType).validate_python(kwargs)
