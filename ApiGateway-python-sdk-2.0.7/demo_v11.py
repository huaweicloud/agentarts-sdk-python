#
# Copyright (c) Huawei Technologies CO., Ltd. 2025. All rights reserved.
#
# coding=utf-8
import os
import requests
from apig_sdk import signer


# demo_app_v11 Generating a Signature Using the v11 Algorithm.
def demo_app_v11():
    # When two signature algorithms starting with V11 are used, region_id is mandatory. For details about how to
    # obtain region_id, see https://support.huaweicloud.com/api-iam/iam_17_0002.html.
    # Supports algorithms used for signatures: SDK-HMAC-SHA256;V11-HMAC-SHA256;SDK-HMAC-SM3;V11-HMAC-SM3.
    sig_v11 = signer.Signer(algorithm=signer.V11HmacSha256, region_id="cn-north-1")
    sig_v11.Key = os.getenv('HUAWEICLOUD_SDK_AK')
    sig_v11.Secret = os.getenv('HUAWEICLOUD_SDK_SK')
    method = "POST"
    url = "https://30030113-3657-4fb6-a7ef-90764239b038.apigw.cn-north-1.huaweicloud.com/app1?a=1&b=2"
    headers = {"content-type": "application/json; charset=utf-8"}
    body = "{'success':'ok'}"

    # sign
    r = signer.HttpRequest(method, url, headers, body)
    sig_v11.Sign(r)
    print(r.headers["X-Sdk-Date"])
    print(r.headers["Authorization"])
    resp = requests.request(method, url, headers=r.headers, data=body)
    print(resp.status_code, resp.reason)
    print(resp.content)

    # verify
    v = sig_v11.Verify(r, r.headers["Authorization"])
    print(v)
