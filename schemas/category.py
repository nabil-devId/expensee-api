from typing import List, Optional
from pydantic import BaseModel, Field, UUID4
from datetime import datetime


class CategoryBase(BaseModel):
    name: str
    icon: str
    color: str


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(CategoryBase):
    pass


class CategoryResponse(CategoryBase):
    category_id: UUID4

    class Config:
        from_attributes = True


class UserCategoryCreate(CategoryBase):
    pass


class UserCategoryUpdate(CategoryBase):
    pass


class UserCategoryResponse(CategoryBase):
    user_category_id: UUID4
    created_at: datetime

    class Config:
        from_attributes = True


class UserCategoryUpdateResponse(UserCategoryResponse):
    updated_at: datetime


class CategoryListResponse(BaseModel):
    default_categories: List[CategoryResponse]
    user_categories: List[UserCategoryResponse]


class CategoryDeleteResponse(BaseModel):
    status: str = "success"
    message: str = "Category deleted successfully"
