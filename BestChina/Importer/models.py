from django.db import models
from solo.models import SingletonModel
import json
from django.db.models import Q
from .functions import *
import json
import threading
from django.conf import settings
STATUS_CHOICES = [('Stopped', 'Stopped'),('Running', 'Running'),('Finished', 'Finished')]
IMPORT_ENDPOINT = settings.IMPORT_ENDPOINT

class CreateImporter(SingletonModel):
    category = models.OneToOneField("Category",max_length=255,unique=True,null=True,on_delete=models.SET_NULL)
    updated_at = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now=True)
    status = models.CharField(choices=STATUS_CHOICES,max_length=255,default='Running')
    is_periodic = models.BooleanField(default=False)
    period_length = models.PositiveIntegerField(default = 10)
    errors = models.TextField(default="Everything is Ok!",null=True)

    def save(self, *args,**kwargs):
        try:
            importers = Importer.objects.all()
            for importer in importers:
                if importer.category.Code in self.category.Code or self.category.Code in importer.category.Code:
                    raise Exception(f"This Category or it\'s Parent or it's Child is Importing now! Please Delete Importer of {importer.category.Name} Category with CategoryCod : {importer.category.Code} then try again...")
            if not self.category:
                raise Exception(f"Category not set!")
            if self.pk:
                Importer.objects.create(
                category=self.category,
                status=self.status,
                is_periodic=self.is_periodic,
                period_length=self.period_length,
                start_job=True)
        except Exception as e:
            self.errors = json.dumps(e.args)
            super(CreateImporter, self).save(*args,**kwargs)
        else:
            self.errors = "Importer Created Successfully!"
            super(CreateImporter, self).save(*args,**kwargs)


class Importer(models.Model):

    category = models.OneToOneField("Category",max_length=255,null=False,unique=True,on_delete=models.CASCADE)
    updated_at = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now=True)
    status = models.CharField(choices=STATUS_CHOICES,max_length=255,default='Running')
    is_periodic = models.BooleanField(default=False)
    period_length = models.PositiveIntegerField(default = 10)
    period_number = models.PositiveIntegerField(default = 1)
    Progress_percentage = models.FloatField(default = 0)
    Number_of_products = models.PositiveIntegerField(default=0) 
    Number_of_checked_products = models.PositiveIntegerField(default=0) 
    start_job = models.BooleanField(default=False)
    errors = models.TextField(default = "Everything is Ok!")
    @property
    def category_prepared_percent(self):
        return str(len(self.category.get_ItemList())/self.category.Total * 100)

    def save(self, *args,**kwargs):
        if not self.pk and self.start_job==True:
            super(Importer, self).save(*args,**kwargs)
            threading.Thread(target=Import_Job,args=(self,)).start()
        elif self.pk and self.status =="Running" and self.status_changed():
            super(Importer, self).save(*args,**kwargs)
            threading.Thread(target=Import_Job,args=(self,)).start()
        else:
            super(Importer, self).save(*args,**kwargs)

    def status_changed(self):
        if self.pk:
            original = Importer.objects.get(pk=self.pk)
            return self.status != original.status
        return False


class Category(models.Model):

    Code = models.CharField(max_length=255,null=False,unique=True)
    Name = models.CharField(max_length=255,null=False)
    FarsiName = models.CharField(max_length=255,null=False)
    ParentCode = models.CharField(max_length=255,null=False)
    Status = models.CharField(max_length=255,null=False)
    ItemList = models.TextField(default="[]")
    Total = models.PositiveBigIntegerField(default=1, blank=True)
    errors = models.TextField(default="Everything is Ok!")
    @property
    def category_prepared_percent(self):
        return len(self.get_ItemList())/self.Total * 100
    
    def __str__(self):
        return self.Name 

    class Meta:
        verbose_name="Category"
        verbose_name_plural="Categories"
    
    def get_ItemList(self):
        return json.loads(self.ItemList)
    
    def set_ItemList(self,ItemList):
        self.ItemList = json.dumps(ItemList)
        self.save()


class Model_Black_List(models.Model):
    black_item_no = models.CharField(max_length=255,null=False,unique=True)


def Import_Job(importer):
    try:
        AuthorizationToken = get_AuthorizationToken()
        if importer.category.category_prepared_percent != 100:
            set_all_item_list(AuthorizationToken,importer.category)
        category_item_list = importer.category.get_ItemList()
        while importer.Number_of_checked_products < len(category_item_list) and importer.status=="Running":
            ItemNo = category_item_list[importer.Number_of_checked_products]
            details = standardize_Details(get_Details(AuthorizationToken,ItemNo=ItemNo))
            for detail in details["ModelList"] :
                Model_Black_List.objects.create(black_item_no=detail["ItemNo"].strip())
            if  not Model_Black_List.objects.filter(black_item_no=details["Details"]["ItemNo"].strip()):
                response = requests.post(IMPORT_ENDPOINT,data=json.dumps(details),headers = {'Content-Type': 'application/json'})
                if response.json()["result"]:
                    importer.Number_of_products = importer.Number_of_products + 1
                    importer.Number_of_checked_products = importer.Number_of_checked_products + 1
                    importer.Progress_percentage = importer.Number_of_checked_products / len(category_item_list) * 100
                    importer.save(start_job=False)
                else:
                    raise Exception("Import Endpoint Has Error!")
            else:
                importer.Number_of_checked_products = importer.Number_of_checked_products + 1
                importer.Progress_percentage = importer.Number_of_checked_products / len(category_item_list) * 100
                importer.save(start_job=False)
            try:importer = Importer.objects.get(id=importer.id)
            except:break
        else:
            if importer.is_periodic :
                time.sleep(importer.period_length*24*60*60)
                importer.period_number = importer.period_number +1
                importer.save()
                Import_Job(importer)
            else:
                importer.status="Finished"
                importer.save()
    except Exception as e:
        importer.status = "stopped"
        importer.errors = json.dumps(e.args)
        importer.save(start_job=False)

