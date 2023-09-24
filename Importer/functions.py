import requests
from googletrans import Translator
from jinja2 import Template
import time
import re
import json
import os
import openai
import threading
from django.conf import settings

translator = Translator()

openai.api_key = settings.CHAT_GPT_API_KEY
# BASE_DIR=settings.BASE_DIR
# file_path = os.path.join(BASE_DIR, "Categories/FarsiCatJson.json")
with open("Categories/FarsiCatJson.json","r") as f:
    FarsiCatJson = json.loads(f.read())


def get_AuthorizationToken(email="bestchina.ir@gmail.com", password="poonish27634"):
    reqUrl = f"http://openapi.tvc-mall.com/Authorization/GetAuthorization?email={email}&password={password}"

    try:
        response = requests.request(
            "GET", reqUrl, data="",  headers={} , timeout=20)
    except:
        return get_AuthorizationToken(email, password)
    AuthorizationToken = response.json()["AuthorizationToken"]
    return AuthorizationToken


def get_item_list(AuthorizationToken,CategoryCode, lastProductId="", PageSize=100):
    import requests
    if lastProductId:
        reqUrl = f"http://openapi.tvc-mall.com/OpenApi/Product/Search?PageSize={PageSize}&CategoryCode={CategoryCode}&lastProductId={lastProductId}"
    else:
        reqUrl = f"http://openapi.tvc-mall.com/OpenApi/Product/Search?PageSize={PageSize}&CategoryCode={CategoryCode}"
    headersList = {
        "Accept": "*/*",
        "User-Agent": "Thunder Client (https://www.thunderclient.com)",
        "Authorization": "TVC "+AuthorizationToken
    }
    response = requests.request("GET", reqUrl, data="",  headers=headersList,timeout=20)
    if "Message" in response.json().keys():
        if response.json()["Message"] == 'unauthorized':
            AuthorizationToken = get_AuthorizationToken()
            return get_item_list(AuthorizationToken,CategoryCode, lastProductId, PageSize)
        else:
            raise Exception(f"get_item_list error on category : {CategoryCode}")
    return response.json()


def get_Image(AuthorizationToken, ItemNo, Size="700x700"):
    reqUrl = f"http://openapi.tvc-mall.com//OpenApi/Product/Image?ItemNo={ItemNo}&Size={Size}"

    headersList = {
        "Accept": "*/*",
        "User-Agent": "Thunder Client (https://www.thunderclient.com)",
        "Authorization": "TVC " + AuthorizationToken
    }

    payload = ""

    response = requests.request("GET", reqUrl, data=payload,  headers=headersList,timeout=20)
    if response.json()["Message"]=="unauthorized":
        AuthorizationToken = get_AuthorizationToken()
        return get_Image(AuthorizationToken, ItemNo)
    return response.json()["ImageUrl"]


def google_translate(text, source_language="en", target_language="fa"):
    time.sleep(0.5)
    translated = translator.translate(text, src=source_language, dest=target_language)
    return translated.text


def ChatGPT_translate(Details, source_language="English", target_language="Farsi"):
    prompt = f"translate this product name to {target_language} (dont't say anything else and if can not translate return it pure without change):"+Details["Detail"]["Name"]

    response=openai.Completion.create(
        engine='text-davinci-003',
        prompt=prompt,
        max_tokens=350,
        temperature=0.5
    )

    Details["Detail"]["Name"] =response["choices"][0]["text"]

    return Details["Detail"]["Name"]


def google_translate_large_text(html_content, max_chunk_size=4950, source_language="en", target_language="fa"):
    phrases = html_content.split("\n")
    translated_html = ""
    translated_chunk = ""
    for phrase in phrases:
        if len(translated_chunk + "\n"+phrase) < max_chunk_size:
            translated_chunk += "\n"+phrase
        else:
            translated_chunk = google_translate(translated_chunk, source_language=source_language, target_language=target_language)
            translated_html += translated_chunk
            translated_chunk = "\n"+phrase

    translated_chunk = google_translate(translated_chunk, source_language=source_language, target_language=target_language)
    translated_html += translated_chunk

    return translated_html.strip()


def delete_keyword(dictionary, keywords_to_remove):

    for keyword in keywords_to_remove:
        if keyword in dictionary:
            dictionary.pop(keyword)

    return dictionary


def delete_custom_keyword(Details, keywords_to_remove):
    Details["Detail"] = delete_keyword(Details["Detail"], keywords_to_remove)
    # Details["ModelList"] = [ model for model in Details["ModelList"] if model["ItemNo"]!=Details["Detail"]["ItemNo"]]
    for model in Details["ModelList"]:
        model = delete_keyword(model, keywords_to_remove)
        model = delete_keyword(model, ["Description","Summary","Name","CategoryCode"])
    return Details


def get_Details(AuthorizationToken, ItemNo):
    reqUrl = f"http://openapi.tvc-mall.com/OpenApi/Product/Detail?ItemNo={ItemNo}"
    headersList = {"Authorization": "TVC "+AuthorizationToken}
    response = requests.request("GET", reqUrl, data="",  headers=headersList,timeout=20)
    Details = response.json()
    if "Message" in response.json().keys():
        if response.json()["Message"] == 'unauthorized':
            AuthorizationToken = get_AuthorizationToken()
            return get_Details(AuthorizationToken, ItemNo)

    return Details


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

    Details["Detail"]["CategoryCode"]=get_Cat_Tree(Details["Detail"]["CategoryCode"])
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
    keywords_to_remove = ["EanCode", "Reminder", "IsSpecialOffer", "Price", "Modified","Added", "StockStatus", "CacheTime", "PriceList","PackageList", "CompatibleList", "SpecificationList","MOQ","LeadTime","PromotionPeriod","PromotionPrice","GrossWeight","VolumeWeight","WithPackage"]
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
        if model["ItemNo"]!=Details["Detail"]["ItemNo"]:
            model["Image"] = get_Image(AuthorizationToken, model["ItemNo"])
            if formula : model["OriginalPrice"] = change_with_formula(model["OriginalPrice"],formula)
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


def get_Cat_Tree(CategoryCode):
    CategoryList = []
    CategoryList.append(CategoryCode)
    while FarsiCatJson[CategoryCode]["ParentCode"].strip():
        CategoryCode = FarsiCatJson[CategoryCode]["ParentCode"]
        CategoryList.append(CategoryCode)
    return CategoryList


def change_with_formula(input_number, formula):
    number_list = list(formula.keys())
    larger_numbers = [float(num) for num in number_list if float(num) > input_number]
    for key in number_list:
        if float(key) == float(min(larger_numbers)):
            desired_key = key
            break
    return float(formula[desired_key])*input_number


def set_all_item_list(AuthorizationToken,category):
    try:
        ProductItemNoList =True
        lastProductId = ""
        i=0
        while ProductItemNoList:
            ItemList=[]
            NoList = get_item_list(AuthorizationToken=AuthorizationToken,CategoryCode=category.Code,lastProductId=lastProductId)
            ProductItemNoList = NoList["ProductItemNoList"]
            lastProductId = NoList["lastProductId"]
            # category.Total = NoList["Total"]-2
            category.save()
            for item in ProductItemNoList:
                i+=1
                ItemList.append(item["ItemNo"])
            category.extend_ItemList(ItemList)
    except Exception as e:
        category.errors = json.dumps(e.args)
        category.save()

def Shipping_Cost(AuthorizationToken, ItemNo,CountryCode="IR"):

    reqUrl = "http://openapi.tvc-mall.com/order/shippingcostenhancement"

    headersList = {
    "Accept": "*/*",
    "Authorization": "TVC "+AuthorizationToken,
    "Content-Type": "application/json" 
    }

    payload = json.dumps({
    "skuinfo":ItemNo+"*1",
    "countrycode":CountryCode
    })

    response = requests.request("POST", reqUrl, data=payload,  headers=headersList)


    if "Message" in response.json().keys():
        if response.json()["Message"] == 'unauthorized':
            AuthorizationToken = get_AuthorizationToken()
            return Shipping_Cost(AuthorizationToken, ItemNo,CountryCode)
    
    return response.json()