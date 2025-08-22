from django.contrib import admin
from .models import Location, Province, City, SchoolType, User

class ProvinceModelAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('name',)}
    list_display = ('name', 'slug')

class CityModelAdmin(admin.ModelAdmin):
    list_display = ('name', 'province', 'slug')
    list_filter = ('province',)

admin.site.register(Location)
admin.site.register(Province, ProvinceModelAdmin)
admin.site.register(City, CityModelAdmin)
admin.site.register(SchoolType)
admin.site.register(User)