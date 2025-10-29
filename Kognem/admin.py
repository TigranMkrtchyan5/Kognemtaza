from django.contrib import admin
from .models import Post, Category , State , Province, Logo

# If Post was already registered, unregister it first
try:
    admin.site.unregister(Post)
except admin.sites.NotRegistered:
    pass

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = (
        'title', 'user', 'category', 'state', 'province',
        'display_location', 'price', 'status', 'created_at'
    )
    list_filter = ('category', 'state', 'province', 'status', 'created_at')
    search_fields = ('title', 'description', 'location', 'user__username')
    ordering = ('-created_at',)
    list_select_related = ('user', 'category')

    def display_location(self, obj):
        return f"{obj.state} / {obj.province} / {obj.location}"
    display_location.short_description = 'Full Address'


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)


@admin.register(State)
class StateAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

@admin.register(Province)
class ProvinceAdmin(admin.ModelAdmin):
    list_display = ('name', 'state')
    list_filter = ('state',)
    search_fields = ('name', 'state__name')

admin.site.register(Logo)