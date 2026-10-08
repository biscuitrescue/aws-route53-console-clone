from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import ZoneType


class VpcAssociation(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    vpc_id: str = Field(min_length=1, max_length=32, examples=["vpc-0a1b2c3d4e5f67890"])
    region: str = Field(min_length=1, max_length=32, examples=["us-east-1"])


class Tag(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    key: str = Field(min_length=1, max_length=128)
    value: str = Field(default="", max_length=256)


class HostedZoneCreate(BaseModel):
    name: str = Field(min_length=1, max_length=1024, examples=["example.com"])
    description: str = Field(default="", max_length=256)
    type: ZoneType = ZoneType.PUBLIC
    vpcs: list[VpcAssociation] = []
    tags: list[Tag] = []


class HostedZoneUpdate(BaseModel):
    description: str = Field(max_length=256)


class TagsUpdate(BaseModel):
    tags: list[Tag]


class TagList(BaseModel):
    tags: list[Tag]


class HostedZoneSummary(BaseModel):
    id: str = Field(examples=["Z0123456789ABCDEFGHIJ"])
    name: str = Field(
        description="Canonical zone name with trailing dot", examples=["example.com."]
    )
    type: ZoneType
    description: str
    created_by: str
    record_count: int
    created_at: datetime
    updated_at: datetime


class HostedZoneDetail(HostedZoneSummary):
    caller_reference: str
    name_servers: list[str]
    vpcs: list[VpcAssociation]
    tags: list[Tag]
