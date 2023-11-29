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
translator.raise_Exception = True
translator_waiter = False
openai.api_key = settings.CHAT_GPT_API_KEY
EXISTENCE_CHECK_ENDPOINT = settings.EXISTENCE_CHECK_ENDPOINT


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
    translated=""
    global translator_waiter

    while translator_waiter:
        time.sleep(0.5)
    translator_waiter = True
    try:translated = translator.translate(text, src=source_language, dest=target_language).text
    except:pass
    time.sleep(0.5)
    translator_waiter = False

    return translated


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


def standardize_update_Details(Details,formula):
    update_Detail = {}
    update_Detail["Detail"]={"OriginalPrice":"","MOQ":"","ProductStatus":"","ItemNo":""}
    if formula:Details["Detail"]["OriginalPrice"] = change_with_formula(Details["Detail"]["OriginalPrice"],formula)
    update_Detail["Detail"]["OriginalPrice"] = Details["Detail"]["OriginalPrice"]
    update_Detail["Detail"]["MOQ"] = Details["Detail"]["MOQ"]
    update_Detail["Detail"]["ProductStatus"] = Details["Detail"]["ProductStatus"]
    update_Detail["Detail"]["ItemNo"] = Details["Detail"]["ItemNo"]
    update_Detail["ModelList"]=[]
    for model in Details["ModelList"]:
        if formula : model["OriginalPrice"] = change_with_formula(model["OriginalPrice"],formula)
        update_model = {}
        update_model["ItemNo"] = model["ItemNo"]
        update_model["OriginalPrice"] = model["OriginalPrice"]
        update_model["MOQ"] = model["MOQ"]
        update_model["ProductStatus"] = model["ProductStatus"]
        update_Detail["ModelList"].append(update_model)
    return update_Detail


def change_with_formula(input_number, formula):
    number_list = list(formula.keys())
    larger_numbers = [float(num) for num in number_list if float(num) > input_number]
    for key in number_list:
        if float(key) == float(min(larger_numbers)):
            desired_key = key
            break
    return float(formula[desired_key])*input_number


def Shipping_Cost(AuthorizationToken, ItemNo,MOQ,CountryCode="IR"):

    reqUrl = "http://openapi.tvc-mall.com/order/shippingcostenhancement"

    headersList = {
    "Accept": "*/*",
    "Authorization": "TVC "+AuthorizationToken,
    "Content-Type": "application/json" 
    }

    payload = json.dumps({
    "skuinfo":ItemNo+"*"+str(MOQ),
    "countrycode":CountryCode
    })

    response = requests.request("POST", reqUrl, data=payload,  headers=headersList)


    if "Message" in response.json().keys():
        if response.json()["Message"] == 'unauthorized':
            AuthorizationToken = get_AuthorizationToken()
            return Shipping_Cost(AuthorizationToken, ItemNo,MOQ,CountryCode)
    
    return response.json()


def get_Parent(AuthorizationToken,CategoryCode):
    GetParentUrl = f"https://openapi.tvc-mall.com/OpenApi/Category/GetParent?categoryCode={CategoryCode}"
    headersList = {
        "Authorization": "TVC "+AuthorizationToken
    }
    try:
        response = requests.request("GET", GetParentUrl, data="",  headers=headersList, timeout=20)
        Parent = response.json()
    except:Parent = get_Parent(AuthorizationToken,CategoryCode)
    if "CateoryList" not in Parent.keys():
        AuthorizationToken = get_AuthorizationToken()
        Parent = get_Parent(AuthorizationToken,CategoryCode)
    
    return Parent


def check_existence(ItemNo):
    payload = json.dumps({"ItemNo":ItemNo})
    header = {"Content-Type": "application/json"}
    response = requests.request("POST", EXISTENCE_CHECK_ENDPOINT ,data = payload ,headers=header,timeout=20)
    return response.json()["response"]
