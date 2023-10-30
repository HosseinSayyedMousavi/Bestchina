from django.db import models
from solo.models import SingletonModel
import json
from django.db.models import Q
from .functions import *
import json
import threading
from django.conf import settings
from django.utils import timezone
from tqdm import tqdm

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
            if self.formula : self.check_formula(self.formula)
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

try:CreateImporter.objects.get_or_create()
except:pass

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
    Progress_bar = models.TextField(null=True,blank=True)
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
    ParentCode = models.CharField(max_length=255,null=True)
    ParentName = models.CharField(max_length=255,null=True)
    Status = models.CharField(max_length=255,null=False)
    ItemList = models.TextField(default='[]')
    errors = models.TextField(default="Everything is Ok!")
    lastProductId = models.CharField(max_length=255,null=True)

    def __str__(self):
        return self.Name 

    class Meta:
        verbose_name="Category"
        verbose_name_plural="Categories"
    
    def get_ItemList(self):
        return json.loads(self.ItemList)
    
    def extend_ItemList(self,ItemList):
        Item_List = json.loads(self.ItemList)
        Item_List.extend(ItemList)
        self.ItemList = json.dumps(Item_List)
        self.save()

    @property
    def number_of_items(self):
        Item_List = json.loads(self.ItemList)
        return len(Item_List)
    

class Model_Black_List(models.Model):
    black_item_no = models.CharField(max_length=255,null=False,unique=True)


def Import_Job(importer):
    try:

        AuthorizationToken = get_AuthorizationToken()
        update_itemlist(AuthorizationToken,importer.category)
        importer = Importer.objects.get(id=importer.id)
        category_item_list = importer.category.get_ItemList()
        Progress_bar = tqdm(total = len(category_item_list))
        Progress_bar.n = importer.Number_of_checked_products
        importer.Progress_bar = Progress_bar.__str__()
        importer.start_job=False
        importer.save()
        while importer.Number_of_checked_products < len(category_item_list) and importer.status=="Running":
            ItemNo = category_item_list[importer.Number_of_checked_products]
            print(ItemNo)
            importer = Importer.objects.get(id=importer.id)
            importer.current_Item = ItemNo
            importer.operation = "1. Check Product"
            importer.start_job=False
            importer.save()
            if  not Model_Black_List.objects.filter(black_item_no=ItemNo.strip()):
                shipping=Shipping_Cost(AuthorizationToken,MOQ=1,ItemNo=ItemNo)
                existence = check_existence(ItemNo)
                if (not existence and shipping["Shippings"]) or existence:
                    importer = Importer.objects.get(id=importer.id)
                    importer.operation = "2. Get From API"
                    importer.start_job=False
                    importer.save()
                    details = get_Details(AuthorizationToken,ItemNo=ItemNo)
                    if not shipping["Shippings"] : details["Detail"]["ProductStatus"] = 0
                    if (not existence and int(details["Detail"]["ProductStatus"]) == 1) or existence:
                        if "Message" not in details.keys():
                            importer = Importer.objects.get(id=importer.id)
                            importer.operation = "3. Standardize"
                            importer.start_job=False
                            importer.save()
                            
                            
                            if existence : details = standardize_update_Details(details,importer.formula)
                            else : details = standardize_Details(details,importer.formula)

                            for detail in details["ModelList"] :
                                # print(detail)
                                if detail["ItemNo"] != ItemNo :
                                    Model_Black_List.objects.get_or_create(black_item_no = detail["ItemNo"].strip())
                            importer = Importer.objects.get(id=importer.id)
                            importer.operation = "4. Import To Website"
                            importer.start_job=False
                            importer.save()
                            shipping=Shipping_Cost(AuthorizationToken,MOQ = details["Detail"]["MOQ"],ItemNo=ItemNo)
                            details["AddonList"] = create_add_on(shipping)
                            response = requests.post(IMPORT_ENDPOINT , data=json.dumps(details) , headers = {'Content-Type': 'application/json'} , timeout=180)
                            if response.json()["result"]:
                                importer = Importer.objects.get(id=importer.id)
                                importer.Number_of_products = importer.Number_of_products + 1
                                importer.Number_of_checked_products = category_item_list.index(importer.current_Item) + 1
                                Progress_bar.n = importer.Number_of_checked_products
                                importer.Progress_bar = Progress_bar.__str__()
                                importer.Progress_percentage = importer.Number_of_checked_products / len(category_item_list) * 100
                                importer.start_job=False
                                importer.save()
                            else:
                                raise Exception(response.text)
                        else:
                            simple_else(importer,category_item_list,Progress_bar)
                    else:
                            simple_else(importer,category_item_list,Progress_bar)
                else:
                                simple_else(importer,category_item_list,Progress_bar)
            else:
                                simple_else(importer,category_item_list,Progress_bar)
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
                importer = Importer.objects.get(id=importer.id)
                if importer.status=="Running":
                    importer.period_number = importer.period_number + 1
                    importer.start_job=True
                    importer.save()
            else:
                importer = Importer.objects.get(id=importer.id)
                importer.operation = "6. Import Finished Successfully!"
                importer.status="Finished"
                importer.start_job=False
                importer.save()

    except Exception as e:
        importer = Importer.objects.get(id=importer.id)
        importer.status = "Stopped"
        importer.errors = json.dumps(e.args)+"            ErrorLine:  "+ str(e.__traceback__.tb_lineno)
        importer.start_job=False
        importer.save()


def simple_else(importer,category_item_list,Progress_bar):
    importer = Importer.objects.get(id=importer.id)
    importer.Number_of_checked_products = category_item_list.index(importer.current_Item) + 1
    Progress_bar.n = importer.Number_of_checked_products
    importer.Progress_bar = Progress_bar.__str__()
    importer.Progress_percentage = importer.Number_of_checked_products / len(category_item_list) * 100
    importer.start_job=False
    importer.save()


def create_add_on(shipping):
    add_on = [{"Name":"هزینه ارسال","Description":"","Options":[]}]
    for sh in shipping["Shippings"]:
        sh_Dict = {}
        sh_Dict["Label"] = "ارسال از چین به ایران -  " + sh["ShippingMethod"].replace("China Post","پست سفارشی").replace("POST NL","پست ویژه")
        sh_Dict["Price"] = sh["ShippingCost"]
        add_on[0]["Options"].append(sh_Dict)
        # add_on[0]["Description"] += "مدت ارسال با  " +  sh["ShippingMethod"].replace("China Post","پست سفارشی").replace("POST NL","پست ویژه")+ " : " +  sh["DeliveryCycle"].replace("business","").replace("days","").strip() + " روز کاری\n" 

    return add_on


def get_Cat_Tree(CategoryCode):
    CategoryList = []
    CategoryList.append(CategoryCode)
    if not Category.objects.filter(Code=CategoryCode):
        AuthorizationToken = get_AuthorizationToken()
        category = get_Parent(AuthorizationToken,CategoryCode)["CateoryList"][0]
        category["FarsiName"] = google_translate[category["Name"]]
        Category.objects.create(**category)
    while Category.objects.get(Code=CategoryCode).ParentCode.strip():
        ParentCode = Category.objects.get(Code=CategoryCode).ParentCode.strip()
        if not Category.objects.filter(Code=ParentCode):
            category = get_Parent(AuthorizationToken,ParentCode)["CateoryList"][0]
            category["FarsiName"] = google_translate[category["Name"]]
            Category.objects.create(**category)
        CategoryCode = ParentCode
        CategoryList.append(CategoryCode)
    return CategoryList


def update_itemlist(AuthorizationToken,category):
    try:
        ProductItemNoList =True
        lastProductId = category.lastProductId
        category=Category.objects.get(id=category.id)
        while ProductItemNoList:
            ItemList=[]
            NoList = get_item_list(AuthorizationToken=AuthorizationToken,CategoryCode=category.Code,lastProductId=lastProductId)
            category.errors = "Everything is Ok!"
            ProductItemNoList = NoList["ProductItemNoList"]
            if ProductItemNoList:
                lastProductId = NoList["lastProductId"]
                category.lastProductId = lastProductId
                
                category.save()
            for item in ProductItemNoList:
                ItemList.append(item["ItemNo"])
            category=Category.objects.get(id=category.id)
            category.extend_ItemList(ItemList)
    except Exception as e:
        category.errors = json.dumps(e.args)
        category.save()


def standardize_Details(Details,formula):
    if int(Details["Detail"]["ProductStatus"])!=1:
        return Details
    append_html='''
    <div>
        <h3 class="titr">سازگار با:</h3>
        <ul class="parag">

            {% if  "CompatibleList" in Details["Detail"].keys()%}
                {% if  Details["Detail"]["CompatibleList"] is iterable %}
                    {% for compatible in Details["Detail"]["CompatibleList"] %}
                        <li class="parag">{{ compatible["DisplayName"] }}</li>
                    {% endfor %}
                {% endif %}
            {% endif %}
        </ul>
    </div>

    <div>
        <h3 class="titr">بسته شامل:</h3>
        <ul class="parag">

            {% if  "PackageList" in Details["Detail"].keys()%}
                {% if  Details["Detail"]["PackageList"] is iterable %}
                    {% for package in Details["Detail"]["PackageList"] %}
                        <li class="parag" >{{ package }}</li>
                    {% endfor %}
                {% endif %}
            {% endif %}

        </ul>
    </div>
    <div class="jay" style="text-align:right !important;direction:rtl !important">
    <table >
        <thead >
            <tr>
                <h3 class="titr" >مشخصات فنی</h3>
                <th></th>
            </tr>
        </thead>
        <tbody >
            {% if  "SpecificationList" in Details["Detail"].keys()%}
                {% if  Details["Detail"]["SpecificationList"] is iterable %}
                    {% for specific in Details["Detail"]["SpecificationList"] %}
                        <tr>
                            <td class="parag" style="font-size:13px">{{ specific["Name"] }}</td>
                            <td class="parag" style="font-size:13px">{{ specific["Value"] }}</td>
                        </tr>
                    {% endfor %}
                {% endif %}
            {% endif %}
        </tbody>
    </table>
    <div class="clear"></div>
    </div>
    
    </body>
    </html>

    '''

    Details["Detail"]["CategoryCode"]= get_Cat_Tree(Details["Detail"]["CategoryCode"])
    before_html = '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body>

    '''


    AuthorizationToken = get_AuthorizationToken()
    keywords_to_remove = ["EanCode", "Reminder", "IsSpecialOffer", "Price", "Modified","Added", "StockStatus", "CacheTime", "PriceList","PackageList", "CompatibleList", "SpecificationList","LeadTime","PromotionPeriod","PromotionPrice","GrossWeight","VolumeWeight","WithPackage"]
    if "-" in Details["Detail"]["Name"]:Details["Detail"]["Name"]=re.findall(r'(.*)-', Details["Detail"]["Name"])[0]
    if "-" in Details["Detail"]["Summary"]:Details["Detail"]["Name"]=re.findall(r'(.*)-', Details["Detail"]["Summary"])[0]
    Details["Detail"]["Description"]=Details["Detail"]["Description"].replace("-"+re.findall(r"-.*h5",Details["Detail"]["Description"])[0].split("-")[-1],"<\h5")
    Details["Detail"]["Image"] = get_Image(AuthorizationToken, Details["Detail"]["ItemNo"])
    if formula:Details["Detail"]["OriginalPrice"] = change_with_formula(Details["Detail"]["OriginalPrice"],formula)
    Details["Detail"]["Name"] = google_translate(Details["Detail"]["Name"])
    Details["Detail"]["Summary"] = google_translate(Details["Detail"]["Summary"])
    try:
        AttributeKeys = list(Details["Detail"]["Attributes"].keys())
        for attr in AttributeKeys:
            try:Details["Detail"]["Attributes"][google_translate(attr)] = google_translate(Details["Detail"]["Attributes"].pop(attr))
            except:
                try:Details["Detail"]["Attributes"][attr] = google_translate(Details["Detail"]["Attributes"].pop(attr))
                except:
                    try:Details["Detail"]["Attributes"][google_translate(attr)] = Details["Detail"]["Attributes"].pop(attr)
                    except:pass
    except:pass
    
    try:
        for specific in Details["Detail"]["SpecificationList"]:
            try:specific["Name"] = google_translate(specific["Name"])
            except:pass
            try:specific["Value"] = google_translate(specific["Value"])
            except:pass
    except:pass
    try:
        for package in Details["Detail"]["PackageList"]:
                try:package = google_translate(package)
                except:pass
    except:pass
    try:
        for compatible in Details["Detail"]["CompatibleList"]:
            try:compatible["DisplayName"] = google_translate(compatible["DisplayName"])
            except:pass
    except:pass
    Details["Detail"]["Description"]=re.sub(r"style.*?>",">",Details["Detail"]["Description"])
    Details["Detail"]["Description"] = google_translate_large_text(Details["Detail"]["Description"].replace("h5","h2").replace("system -title","system-title"))
    
    template = Template(before_html + Details["Detail"]["Description"] + append_html)
    rendered_html = template.render(Details=Details)
    Details["Detail"]["Description"] = rendered_html

    Details = delete_custom_keyword(Details,keywords_to_remove)
    Details["ModelList"] = [model for model in Details["ModelList"] if model["ProductStatus"]==1]
    for model in Details["ModelList"]:
        if formula : model["OriginalPrice"] = change_with_formula(model["OriginalPrice"],formula)
        if model["ItemNo"]!=Details["Detail"]["ItemNo"]:
            model["Image"] = get_Image(AuthorizationToken, model["ItemNo"])
            try:
                ModelKeys = list(model["Attributes"].keys())
                for attr in ModelKeys:
                    try:model["Attributes"][google_translate(attr)] = google_translate(model["Attributes"].pop(attr))
                    except:
                        try:model["Attributes"][attr] = google_translate(model["Attributes"].pop(attr))
                        except:
                            try:model["Attributes"][google_translate(attr)] = model["Attributes"].pop(attr)
                            except:pass
            except:pass
        else:
            model["Image"]=Details["Detail"]["Image"]
            try:model["Attributes"]=Details["Detail"]["Attributes"]
            except:pass
    return Details

