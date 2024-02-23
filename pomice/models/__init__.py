import pydantic
from pydantic import ConfigDict

from .events import *
from .music import *
from .payloads import *
from .version import *


class BaseModel(pydantic.BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, populate_by_name=True)
