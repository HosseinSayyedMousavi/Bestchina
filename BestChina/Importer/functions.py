import requests
from googletrans import Translator
from jinja2 import Template
import time
import re
import json
translator = Translator()



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
    response = requests.request("GET", reqUrl, data="",  headers=headersList)
    if "Message" in response.json().keys():
        AuthorizationToken = get_AuthorizationToken()
        return get_item_list(AuthorizationToken,CategoryCode, lastProductId, PageSize)
    
    return response.json()


def get_Image(AuthorizationToken, ItemNo, Size="700x700"):
    reqUrl = f"http://openapi.tvc-mall.com//OpenApi/Product/Image?ItemNo={ItemNo}&Size={Size}"

    headersList = {
        "Accept": "*/*",
        "User-Agent": "Thunder Client (https://www.thunderclient.com)",
        "Authorization": "TVC " + AuthorizationToken
    }

    payload = ""

    response = requests.request("GET", reqUrl, data=payload,  headers=headersList)
    if response.json()["Message"]=="unauthorized":
        AuthorizationToken = get_AuthorizationToken()
        return get_Image(AuthorizationToken, ItemNo)
    return response.json()


def google_translate(text, source_language="en", target_language="fa"):
    time.sleep(0.5)
    translated = translator.translate(text, src=source_language, dest=target_language)
    return translated.text


def delete_keyword(dictionary, keywords_to_remove):

    for keyword in keywords_to_remove:
        if keyword in dictionary:
            dictionary.pop(keyword)

    return dictionary


def delete_custom_keyword(Details, keywords_to_remove):
    Details["Detail"] = delete_keyword(Details["Detail"], keywords_to_remove)
    Details["ModelList"] = [ model for model in Details["ModelList"] if model["ItemNo"]!=Details["Detail"]["ItemNo"]]
    for model in Details["ModelList"]:
        model = delete_keyword(model, keywords_to_remove)
        model = delete_keyword(model, ["Description","Summary","Name","CategoryCode"])
    return Details


def get_Details(AuthorizationToken, ItemNo):
    reqUrl = f"http://openapi.tvc-mall.com/OpenApi/Product/Detail?ItemNo={ItemNo}"
    headersList = {"Authorization": "TVC "+AuthorizationToken}
    response = requests.request("GET", reqUrl, data="",  headers=headersList)
    Details = response.json()
    if "Message" in response.json().keys():
        AuthorizationToken = get_AuthorizationToken()
        return get_Details(AuthorizationToken, ItemNo)
    return Details


def standardize_Details(Details):
    append_html='''
    <div>
        <div class="titr">سازگار با:</div>
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
        <div class="titr">بسته شامل:</div>
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
                <th class="titr" >مشخصات فنی</th>
                <th></th>
            </tr>
        </thead>
        <tbody >
            {% if  "SpecificationList" in Details["Detail"].keys()%}
                {% if  Details["Detail"]["SpecificationList"] is iterable %}
                    {% for specific in Details["Detail"]["SpecificationList"] %}
                        <tr>
                            <td class="parag">{{ specific["Name"] }}</td>
                            <td class="parag">{{ specific["Value"] }}</td>
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


    before_html = '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            .system-title {
                text-align: right;
                font-family: "Vazir";
                direction: rtl;
            }

            .system-description {
                text-align: right;
                font-family: "Vazir";
                direction: rtl;
            }

            .system-description ul {
                position: relative;
            }

            @font-face {
                font-family: 'Vazir';
                src: url('https://raw.githubusercontent.com/rastikerdar/vazirmatn/master/fonts/webfonts/Vazirmatn-Regular.woff2') format('woff2'), url('https://raw.githubusercontent.com/rastikerdar/vazirmatn/master/fonts/webfonts/Vazirmatn-Regular.woff') format('woff');
            }

            .titr {
                font-weight: bold;
                font-size: 16px;
                font-family: "Vazir";
                text-align: right;
                direction: rtl;
            }

            .titr tr td {
                font-size: 12px;
                font-family: "Vazir";
                text-align: right;
                direction: rtl;
            }

            .parag {
                text-align: right;
                font-family: "Vazir";
                direction: rtl;
            }

            .clear {
                clear: both;
            }

            .jay {
                text-align: right !important;
                direction: rtl !important;
                display: block !important;
                ;
                position: relative;
            }
        </style>
    </head>
    <body>

    '''


    AuthorizationToken = get_AuthorizationToken()
    keywords_to_remove = ["EanCode", "Reminder", "IsSpecialOffer", "Price", "Modified","Added", "StockStatus", "CacheTime", "PriceList","PackageList", "CompatibleList", "SpecificationList","MOQ","LeadTime","PromotionPeriod","PromotionPrice","GrossWeight","VolumeWeight","WithPackage"]
    Details["Detail"]["Image"] = get_Image(AuthorizationToken, Details["Detail"]["ItemNo"])
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
    Details["Detail"]["Description"] = google_translate(Details["Detail"]["Description"].replace("h5","h2").replace("system -title","system-title"))

    template = Template(before_html + Details["Detail"]["Description"] + append_html)
    rendered_html = template.render(Details=Details)
    Details["Detail"]["Description"] = rendered_html

    Details = delete_custom_keyword(Details,keywords_to_remove)
    for model in Details["ModelList"]:
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
    return Details


def set_all_item_list(AuthorizationToken,category):
    try:
        ProductItemNoList =True
        ItemList=[]
        lastProductId = ""
        i=0
        print(category)
        while ProductItemNoList:
            NoList = get_item_list(AuthorizationToken=AuthorizationToken,CategoryCode=category.Code,lastProductId=lastProductId)
            ProductItemNoList = NoList["ProductItemNoList"]
            lastProductId = NoList["lastProductId"]
            category.Total = NoList["Total"]
            category.save()
            for item in ProductItemNoList:
                i+=1
                print(i)
                ItemList.append(item["ItemNo"])
                category.set_ItemList(ItemList)
    except Exception as e:
        category.errors = json.dumps(e.args)
        category.save()

