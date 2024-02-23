from pydantic import Field
from typing import Union

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


_ResumePayloadType = Union[ResumePayloadV3, ResumePayloadV4]
ResumePayloadType = lambda **kwargs: TypeAdapter(_ResumePayloadType).validate_python(kwargs)
