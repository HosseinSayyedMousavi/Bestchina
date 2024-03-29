from django.contrib import admin
from import_export.admin import ImportExportModelAdmin
from import_export.resources import ModelResource
from .models import Category , Importer , CreateImporter , Product
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
    readonly_fields= ("Code","Name","FarsiName","ParentCode","ParentName","Status","errors","number_of_items","lastProductId")
    search_fields = ("Name","Code","FarsiName")
admin.site.register(Category,CategoryAdmin)

class ImporterAdmin(admin.ModelAdmin):
    list_display = ("category","status","is_periodic","Progress_percentage","Progress_bar","errors")
    list_display_links = list_display
    exclude = ["start_job"]
    readonly_fields = ('category',"is_periodic","period_length","items_of_category","Progress_percentage","Progress_bar","period_number","Number_of_products","Number_of_checked_products","errors","updated_at","created_at","current_Item","operation","formula")
    search_fields = ("category.Name","category.Code")
    def items_of_category(self, obj):
        return obj.category.number_of_items
    def has_add_permission(self, request):
        return False
admin.site.register(Importer,ImporterAdmin)

class CreateImporterAdmin(SingletonModelAdmin):
    readonly_fields = ("errors","updated_at","created_at")
    exclude = ["status"]
admin.site.register(CreateImporter,CreateImporterAdmin)

class ProductAdmin(admin.ModelAdmin):
    readonly_fields = ("ItemNo","category","product_num")
    list_display = ("ItemNo","category","product_num")
    list_filter = ("category",)
    search_fields = ("ItemNo",)
    def has_add_permission(self, request):
        return False

admin.site.register(Product,ProductAdmin)