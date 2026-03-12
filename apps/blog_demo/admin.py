from sqladmin import ModelView

from apps.app_two.models import Category, Post


class CategoryAdmin(ModelView, model=Category):
    column_list = [Category.id, Category.name, Category.slug]
    column_searchable_list = [Category.name]
    name = "Category"
    name_plural = "Categories"
    icon = "fa-solid fa-folder"


class PostAdmin(ModelView, model=Post):
    column_list = [Post.id, Post.title, Post.slug, Post.published, Post.created_at]
    column_searchable_list = [Post.title]
    name = "Post"
    name_plural = "Posts"
    icon = "fa-solid fa-newspaper"
