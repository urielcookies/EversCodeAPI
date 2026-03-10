from sqladmin import ModelView

from apps.app_two.models import Note, Tag


class NoteAdmin(ModelView, model=Note):
    column_list = [Note.id, Note.title, Note.content]
    column_searchable_list = [Note.title]
    name = "Note"
    name_plural = "Notes"
    icon = "fa-solid fa-note-sticky"


class TagAdmin(ModelView, model=Tag):
    column_list = [Tag.id, Tag.name, Tag.color]
    column_searchable_list = [Tag.name]
    name = "Tag"
    name_plural = "Tags"
    icon = "fa-solid fa-tag"
