import json
import requests
from pprintpp import pprint
import openai
from googletrans import Translator
from jinja2 import Template
import time
translator = Translator()
openai.api_key = "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"


append_html='''
<div  class="desitems mt-[20px]">
    <div  class="text-[22px] leading-[30px]">Compatible with:</div>
    <div  class="pl-[15px]">
        <ul  style="list-style: disc;">

            {% for compatible in Details["Detail"]["CompatibleList"] %}
                <li  class="text-[18px] leading-[30px]">{{ compatible["DisplayName"] }} </li>
            {% endfor %}

        </ul>
    </div>
</div>


<div  class="desitems">
    <div  class="text-[22px] pt-[12px] leading-[30px]">Package included:</div>
    <div  class="pl-[15px]">
        <ul  style="list-style: disc;">

            {% for package in Details["Detail"]["PackageList"] %}
                <li  class="text-[18px] leading-[20px]">{{ package }}</li>
            {% endfor %}

        </ul>
    </div>
</div>


<div 
    class="n-data-table __data-table-11a5fl2-m n-data-table--bottom-bordered n-data-table--single-line mt-[30px]">
    <div class="n-data-table-wrapper">
        <div class="n-data-table-base-table">
            <table class="n-data-table-table" style="table-layout: fixed;">
                <colgroup>
                    <col>
                    <col>
                </colgroup>
                <thead class="n-data-table-thead" data-n-id="d77a7923">
                    <tr class="n-data-table-tr">
                        <th colspan="1" rowspan="1" data-col-key="key" class="n-data-table-th">
                            <div class="n-data-table-th__title-wrapper">
                                <div class="n-data-table-th__title">
                                    <div class="n-data-table-th__ellipsis">
                                        <div style="font-size: 22px; font-weight: bold;">Specifications</div>
                                    </div>
                                </div>
                            </div>
                        </th>
                        <th colspan="1" rowspan="1" data-col-key="title" class="n-data-table-th n-data-table-th--last">
                            <div class="n-data-table-th__title-wrapper">
                                <div class="n-data-table-th__title">
                                    <div default="()=>&quot;&quot;"></div>
                                </div>
                            </div>
                        </th>
                    </tr>
                </thead>
                <tbody data-n-id="d77a7923" class="n-data-table-tbody">

                    {% for specific in Details["Detail"]["SpecificationList"] %}
                        <tr class="n-data-table-tr td">
                            <td colspan="1" rowspan="1" data-col-key="key" class="n-data-table-td"><span
                                    class="n-ellipsis" style="text-overflow: ellipsis;"><span>{{ specific["Name"] }}</span></span></td>
                            <td colspan="1" rowspan="1" data-col-key="title"
                                class="n-data-table-td n-data-table-td--last-col">{{ specific["Value"] }}</td>
                        </tr>
                    {% endfor %}
                    
                </tbody>
            </table>
        </div>
    </div>
</div>

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


def get_Category(AuthorizationToken, PageSize, CategoryCode, PageIndex):
    import requests

    reqUrl = f"http://openapi.tvc-mall.com/OpenApi/Product/Search?PageSize={PageSize}&CategoryCode={CategoryCode}&PageIndex={PageIndex}"

    headersList = {
        "Accept": "*/*",
        "User-Agent": "Thunder Client (https://www.thunderclient.com)",
        "Authorization": "TVC "+AuthorizationToken
    }

    response = requests.request("GET", reqUrl, data="",  headers=headersList)
    
    return response.json()["ProductItemNoList"]


def get_Image(AuthorizationToken, ItemNo, Size="1000x1000"):
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
    for model in Details["ModelList"]:
        model = delete_keyword(model, keywords_to_remove)
    return Details


def get_Details(AuthorizationToken, ItemNo):
    keywords_to_remove = ["EanCode", "Reminder", "IsSpecialOffer", "Price", "Modified","Added", "StockStatus", "CacheTime", "PriceList","PackageList", "CompatibleList", "SpecificationList"]
    reqUrl = f"http://openapi.tvc-mall.com/OpenApi/Product/Detail?ItemNo={ItemNo}"
    headersList = {"Authorization": "TVC "+AuthorizationToken}
    response = requests.request("GET", reqUrl, data="",  headers=headersList)
    Details = response.json()
    print(Details)
    template = Template(append_html)
    Details["Detail"]["Image"] = get_Image(AuthorizationToken, Details["Detail"]["ItemNo"])
    Details["Detail"]["Name"] = google_translate(Details["Detail"]["Name"])
    Details["Detail"]["Summary"] = google_translate(Details["Detail"]["Summary"])
    rendered_html = template.render(Details=Details)
    Details["Detail"]["Description"] = Details["Detail"]["Description"]+rendered_html
    Details["Detail"]["Description"] = google_translate(Details["Detail"]["Description"])
    Details = delete_custom_keyword(Details,keywords_to_remove)
    for model in Details["ModelList"]:
        model["Image"] = get_Image(AuthorizationToken, model["ItemNo"])
        model["Name"] = google_translate(model["Name"])
        model["Summary"] = google_translate(model["Summary"])
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

