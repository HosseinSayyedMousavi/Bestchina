import json
import requests
from pprintpp import pprint
import openai
from googletrans import Translator
from jinja2 import Template
import time
import re
translator = Translator()
openai.api_key = "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"

append_html='''
<div>
    <div class="titr">سازگار با:</div>
    <ul class="parag">
        {% for compatible in Details["Detail"]["CompatibleList"] %}
            <li class="parag">{{ compatible["DisplayName"] }}</li>
        {% endfor %}
    </ul>
</div>

<div>
    <div class="titr">بسته شامل:</div>
    <ul class="parag">
        {% for package in Details["Detail"]["PackageList"] %}
            <li class="parag" >{{ package }}</li>
        {% endfor %}
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
        {% for specific in Details["Detail"]["SpecificationList"] %}
            <tr>
                <td class="parag">{{ specific["Name"] }}</td>
                <td class="parag">{{ specific["Value"] }}</td>
            </tr>
        {% endfor %}
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

def get_AuthorizationToken(email="bestchina.ir@gmail.com", password="poonish27634"):
    reqUrl = f"http://openapi.tvc-mall.com/Authorization/GetAuthorization?email={email}&password={password}"

    try:
        response = requests.request(
            "GET", reqUrl, data="",  headers={} , timeout=20)
    except:
        return get_AuthorizationToken(email, password)
    AuthorizationToken = response.json()["AuthorizationToken"]
    return AuthorizationToken


def get_Children(AuthorizationToken,ParentCode=""):
    GetChildrenUrl = f"http://openapi.tvc-mall.com/OpenApi/Category/GetChildren?ParentCode={ParentCode}"
    headersList = {
        "Authorization": "TVC "+AuthorizationToken
    }
    try:
        response = requests.request("GET", GetChildrenUrl, data="",  headers=headersList, timeout=20)
        Children = response.json()
    except:Children = get_Children(AuthorizationToken,ParentCode)

    if "CateoryList" not in Children.keys():
        AuthorizationToken = get_AuthorizationToken()
        Children = get_Children(AuthorizationToken,ParentCode)
    return Children


def get_Category(AuthorizationToken, PageSize, CategoryCode, lastProductId=""):
    import requests

    reqUrl = f"http://openapi.tvc-mall.com/OpenApi/Product/Search?PageSize={PageSize}&CategoryCode={CategoryCode}&lastProductId={lastProductId}"

    headersList = {
        "Accept": "*/*",
        "User-Agent": "Thunder Client (https://www.thunderclient.com)",
        "Authorization": "TVC "+AuthorizationToken
    }

    response = requests.request("GET", reqUrl, data="",  headers=headersList)
    
    return response.json()


def get_Image(AuthorizationToken, ItemNo, Size="700x700"):
    reqUrl = f"http://openapi.tvc-mall.com//OpenApi/Product/Image?ItemNo={ItemNo}&Size={Size}"

    headersList = {
        "Accept": "*/*",
        "User-Agent": "Thunder Client (https://www.thunderclient.com)",
        "Authorization": "TVC " + AuthorizationToken
    }

    payload = ""

    response = requests.request(
        "GET", reqUrl, data=payload,  headers=headersList)
    return response.json()["ImageUrl"]


def ChatGPT_translate(text, source_language="English", target_language="Farsi"):
    prompt = f"Translate values of all 'Name' and 'Summary' keywords of json this and replace and return  '{source_language}' text to '{target_language}': {text}"

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system",
                "content": "You are a helpful assistant that translates json file."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=150,
        n=1,
        stop=None,
        temperature=0.5,
    )

    translation = response.choices[0].message.content.strip()
    return translation


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
    keywords_to_remove = ["EanCode", "Reminder", "IsSpecialOffer", "Price", "Modified","Added", "StockStatus", "CacheTime", "PriceList","PackageList", "CompatibleList", "SpecificationList","MOQ","LeadTime","PromotionPeriod","PromotionPrice","GrossWeight","VolumeWeight","WithPackage"]
    reqUrl = f"http://openapi.tvc-mall.com/OpenApi/Product/Detail?ItemNo={ItemNo}"
    headersList = {"Authorization": "TVC "+AuthorizationToken}
    response = requests.request("GET", reqUrl, data="",  headers=headersList)
    Details = response.json()
    
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
    

    for specific in Details["Detail"]["SpecificationList"]:
        try:specific["Name"] = google_translate(specific["Name"])
        except:pass
        try:specific["Value"] = google_translate(specific["Value"])
        except:pass

    for package in Details["Detail"]["PackageList"]:
            try:package = google_translate(package)
            except:pass

    for compatible in Details["Detail"]["CompatibleList"]:
         try:compatible["DisplayName"] = google_translate(compatible["DisplayName"])
         except:pass
    
    Details["Detail"]["Description"]=re.sub(r"style.*?>",">",Details["Detail"]["Description"])
    Details["Detail"]["Description"] = google_translate(Details["Detail"]["Description"].replace("h5","h2"))

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
    print(Details["Detail"]["Description"].replace("\n","").replace("\\",""))
    return Details


def get_All_Children(AuthorizationToken,ParentCode="",CatList=[]):
    Children = get_Children(AuthorizationToken,ParentCode)
    for child in Children["CateoryList"]:
        child["Name"]=google_translate(child["Name"])
    CatList.extend(Children["CateoryList"])
    for child in Children["CateoryList"]:
        print(child["Code"])
        CatList = get_All_Children(AuthorizationToken,child["Code"],CatList)
    return CatList

from six import u
def decode(encoded_text):
    return u(encoded_text)


def translate_children(children):
    for child in children["CateoryList"]:
        child["Name"]=google_translate(child["Name"])
        translate_children(child)
    return children