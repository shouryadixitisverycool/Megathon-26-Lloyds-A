from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

CONTRACT_VERSION = "1.0.0"

Probability = Annotated[float, Field(ge=0.0, le=1.0)]


class Contract(BaseModel):
    """Base for every cross-workstream payload: immutable and closed to unknown fields."""

    model_config = ConfigDict(frozen=True, extra="forbid")
