from django.db import models
from solo.models import SingletonModel
import json
from django.db.models import Q
from .functions import *
import json
import threading
from django.conf import settings
from django.utils import timezone
STATUS_CHOICES = [('Stopped', 'Stopped'),('Running', 'Running'),('Finished', 'Finished')]
IMPORT_ENDPOINT = settings.IMPORT_ENDPOINT

class CreateImporter(SingletonModel):
    category = models.OneToOneField("Category",max_length=255,unique=True,null=True,on_delete=models.SET_NULL)
    updated_at = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now=True)
    is_periodic = models.BooleanField(default=False)
    period_length = models.IntegerField(default = 10)
    errors = models.TextField(default="Everything is Ok!",null=True)
    formula = models.JSONField(null=True , blank = True)
    def save(self, *args,**kwargs):
        try:
            importers = Importer.objects.all()
            for importer in importers:
                if importer.category.Code in self.category.Code or self.category.Code in importer.category.Code:
                    raise Exception(f"This Category or it\'s Parent or it's Child is Importing now! Please Delete Importer of {importer.category.Name} Category with CategoryCod : {importer.category.Code} then try again...")
            if not self.category:
                raise Exception(f"Category not set!")
            if self.formula : self.check_formula(dict(self.formula))
            if self.pk:
                Importer.objects.create(
                category=self.category,
                status="Running",
                is_periodic=self.is_periodic,
                period_length=self.period_length,
                formula = self.formula,
                start_job=True)
            
        except Exception as e:
            self.errors = json.dumps(e.args)
            super(CreateImporter, self).save(*args,**kwargs)
        else:
            self.errors = "Importer Created Successfully!"
            super(CreateImporter, self).save(*args,**kwargs)

    def check_formula(self,input_dict):
        for key, value in input_dict.items():
            try:
                float(key)
                float(value)
            except ValueError:
                raise ValueError(f"The key '{key}' or value '{value}' is not convertible to float.")


class Importer(models.Model):

    category = models.OneToOneField("Category",max_length=255,null=False,unique=True,on_delete=models.CASCADE)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    current_Item = models.CharField(max_length=255,null=True,blank=True)
    operation = models.CharField(max_length=255,null=True,blank=True)
    status = models.CharField(choices=STATUS_CHOICES,max_length=255,default='Running')
    is_periodic = models.BooleanField(default=False)
    period_length = models.IntegerField(default = 10)
    period_number = models.IntegerField(default = 1)
    Progress_percentage = models.FloatField(default = 0)
    Number_of_products = models.IntegerField(default=0) 
    Number_of_checked_products = models.IntegerField(default=0) 
    start_job = models.BooleanField(default=False)
    errors = models.TextField(default = "Everything is Ok!")
    formula = models.JSONField(null=True, blank=True)
    # @property
    # def category_prepared_percent(self):
    #     return str(len(self.category.get_ItemList())/self.category.Total * 100)

    @property
    def category_prepared_Items(self):
        return len(self.category.get_ItemList())

    def save(self, *args,**kwargs):
        if self.start_job==True:
            self.errors = "Everything is Ok!"
            self.start_job=False
            super(Importer, self).save(*args,**kwargs)
            Import_thread = threading.Thread(target=Import_Job,args=(self,))
            Import_thread.daemon = True
            Import_thread.start()
            self.check_thread(Import_thread)
        elif self.status =="Running" and self.status_changed() and not "Import_thread" in locals():
            self.errors = "Everything is Ok!"
            self.start_job=False
            super(Importer, self).save(*args,**kwargs)
            Import_thread = threading.Thread(target=Import_Job,args=(self,))
            Import_thread.daemon = True
            Import_thread.start()
            self.check_thread(Import_thread)
        elif self.status =="Running" and self.status_changed() and "Import_thread" in locals():
            if not Import_thread.is_alive():
                self.errors = "Everything is Ok!"
                self.start_job=False
                super(Importer, self).save(*args,**kwargs)
                Import_thread = threading.Thread(target=Import_Job,args=(self,))
                Import_thread.daemon = True
                Import_thread.start()
                self.check_thread(Import_thread)
        else:
            self.start_job=False
            super(Importer, self).save(*args,**kwargs)

    def check_thread(self,Import_thread):

        if not Import_thread.is_alive() and Importer.objects.get(pk=self.pk).status == "Running":

            Import_thread = threading.Thread(target=Import_Job,args=(Importer.objects.get(pk=self.pk),))
            Import_thread.daemon = True
            Import_thread.start()
        elif not Import_thread.is_alive():
            return
        threading.Timer(50, self.check_thread,args = (Import_thread,)).start()

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
    errors = models.TextField(default="Everything is Ok!")

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
    # try:

        AuthorizationToken = get_AuthorizationToken()
        if importer.category_prepared_Items == 0:
            set_all_item_list(AuthorizationToken,importer.category)
        category_item_list = importer.category.get_ItemList()
        while importer.Number_of_checked_products < len(category_item_list) and importer.status=="Running":
            ItemNo = category_item_list[importer.Number_of_checked_products]
            importer = Importer.objects.get(id=importer.id)
            importer.current_Item = ItemNo
            importer.operation = "1. Check Product"
            importer.start_job=False
            importer.save()
            if  not Model_Black_List.objects.filter(black_item_no=ItemNo.strip()):
                importer = Importer.objects.get(id=importer.id)
                importer.operation = "2. Get From API"
                importer.start_job=False
                importer.save()
                details = get_Details(AuthorizationToken,ItemNo=ItemNo)
                if int(details["Detail"]["ProductStatus"]) == 1:
                    if "Message" not in details.keys():
                        importer = Importer.objects.get(id=importer.id)
                        importer.operation = "3. Standardize"
                        importer.start_job=False
                        importer.save()
                        details = standardize_Details(details,dict(importer.formula))
                        
                        for detail in details["ModelList"] :
                            if detail["ItemNo"] != ItemNo and not Model_Black_List.objects.filter(black_item_no = detail["ItemNo"].strip()).exists():
                                Model_Black_List.objects.create(black_item_no = detail["ItemNo"].strip())
                        importer = Importer.objects.get(id=importer.id)
                        importer.operation = "4. Import To Website"
                        importer.start_job=False
                        importer.save()
                        response = requests.post(IMPORT_ENDPOINT,data=json.dumps(details),headers = {'Content-Type': 'application/json'},timeout=180)
                        if response.json()["result"]:
                            importer = Importer.objects.get(id=importer.id)
                            importer.Number_of_products = importer.Number_of_products + 1
                            importer.Number_of_checked_products = importer.Number_of_checked_products + 1
                            importer.Progress_percentage = importer.Number_of_checked_products / len(category_item_list) * 100
                            importer.start_job=False
                            importer.save()
                        else:
                            raise Exception(response.text)
                    else:
                        importer = Importer.objects.get(id=importer.id)
                        importer.Number_of_checked_products = importer.Number_of_checked_products + 1
                        importer.Progress_percentage = importer.Number_of_checked_products / len(category_item_list) * 100
                        importer.start_job=False
                        importer.save()
                else:
                    importer = Importer.objects.get(id=importer.id)
                    importer.Number_of_checked_products = importer.Number_of_checked_products + 1
                    importer.Progress_percentage = importer.Number_of_checked_products / len(category_item_list) * 100
                    importer.start_job=False
                    importer.save()
            else:
                importer = Importer.objects.get(id=importer.id)
                importer.Number_of_checked_products = importer.Number_of_checked_products + 1
                importer.Progress_percentage = importer.Number_of_checked_products / len(category_item_list) * 100
                importer.start_job=False
                importer.save()
            try:importer = Importer.objects.get(id=importer.id)
            except:break
        else:
            if importer.status=="Stopped":return

            if importer.status=="Running" and importer.is_periodic :
                importer = Importer.objects.get(id=importer.id)
                importer.operation = "5. Wait For Next Period Time..."
                importer.start_job=False
                importer.save()
                time.sleep(importer.period_length*24*60*60)
                importer.period_number = importer.period_number + 1
                importer.start_job=True
                importer.save()
            else:
                importer = Importer.objects.get(id=importer.id)
                importer.operation = "6. Import Finished Successfully!"
                importer.status="Finished"
                importer.start_job=False
                importer.save()

    # except Exception as e:
    #     importer = Importer.objects.get(id=importer.id)
    #     importer.status = "Stopped"
    #     importer.errors = json.dumps(e.args)
    #     importer.start_job=False
    #     importer.save()


