from sqladmin import ModelView

from apps.app_one.models import Item


class ItemAdmin(ModelView, model=Item):
    # Columns shown in the list view
    column_list = [Item.id, Item.name, Item.description]
    # Allow searching by name in the admin UI
    column_searchable_list = [Item.name]
    name = "Item"
    name_plural = "Items"
    icon = "fa-solid fa-box"
