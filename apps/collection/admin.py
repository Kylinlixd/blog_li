from django.contrib import admin

from .models import Collection, CollectionItem


class CollectionItemInline(admin.TabularInline):
    model = CollectionItem
    extra = 0
    ordering = ['sort', 'id']


@admin.register(Collection)
class CollectionAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'series', 'sort', 'status', 'updated_at')
    list_editable = ('sort', 'status')
    search_fields = ('title', 'series')
    inlines = [CollectionItemInline]


@admin.register(CollectionItem)
class CollectionItemAdmin(admin.ModelAdmin):
    list_display = ('collection', 'dynamic', 'sort', 'created_at')
    list_editable = ('sort',)
