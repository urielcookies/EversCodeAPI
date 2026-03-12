from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class CategoryRead(BaseModel):
    id: int
    name: str
    slug: str

    model_config = {"from_attributes": True}


class PostCreate(BaseModel):
    title: str
    slug: str
    content: Optional[str] = None
    published: bool = False
    category_id: Optional[int] = None


class PostUpdate(BaseModel):
    title: Optional[str] = None
    slug: Optional[str] = None
    content: Optional[str] = None
    published: Optional[bool] = None
    category_id: Optional[int] = None


class PostRead(BaseModel):
    id: int
    title: str
    slug: str
    content: Optional[str]
    published: bool
    created_at: datetime
    category: Optional[CategoryRead]

    model_config = {"from_attributes": True}
