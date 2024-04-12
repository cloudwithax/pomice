import pydantic
from pydantic import ConfigDict

from .events import *
from .music import *
from .payloads import *
from .version import *


class BaseModel(pydantic.BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, populate_by_name=True)

    def model_dump(self, *args, **kwargs) -> dict:
        by_alias = kwargs.pop("by_alias", True)
        mode = kwargs.pop("mode", "json")
        return super().model_dump(*args, **kwargs, by_alias=by_alias, mode=mode)


class VersionedModel(BaseModel):
    version: LavalinkVersionType

    def model_dump(self, *args, **kwargs) -> dict:
        return super().model_dump(*args, **kwargs, exclude={"version"})
