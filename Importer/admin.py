from django.contrib import admin
from import_export.admin import ImportExportModelAdmin
from import_export.resources import ModelResource
from .models import Category , Importer , CreateImporter
from solo.admin import SingletonModelAdmin
# Register your models here.
class CategoryResource(ModelResource):
    class Meta:
        model = Category
        report_skipped = True
        exclude = ('id',)
        fields = "__all__"

    def get_or_init_instance(self, instance_loader, row):
        unique_field = self._meta.model._meta.get_field('Code')
        unique_value = row.get('Code')  

        try:
            instance = self.get_queryset().get(**{unique_field.name: unique_value})
            return instance, False
        except self._meta.model.DoesNotExist:
            return super().get_or_init_instance(instance_loader, row)

class CategoryAdmin(ImportExportModelAdmin):
    list_display = ("Code","Name","FarsiName","ParentCode","Status")
    readonly_fields= ("Code","Name","FarsiName","ParentCode","Status","errors","number_of_items","ItemList")
    search_fields = ("Name","Code","FarsiName")
admin.site.register(Category,CategoryAdmin)

class ImporterAdmin(admin.ModelAdmin):
    list_display = ("category","status","is_periodic","Progress_bar")
    list_display_links = list_display
    exclude = ["start_job"]
    readonly_fields = ("is_periodic","period_length","category","category_prepared_Items","Progress_percentage","Progress_bar","period_number","Number_of_products","Number_of_checked_products","errors","updated_at","created_at","current_Item","operation","formula")
    search_fields = ("category.Name","category.Code")
admin.site.register(Importer,ImporterAdmin)

class CreateImporterAdmin(SingletonModelAdmin):
    readonly_fields = ("errors","updated_at","created_at")
    exclude = ["status"]
admin.site.register(CreateImporter,CreateImporterAdmin)

