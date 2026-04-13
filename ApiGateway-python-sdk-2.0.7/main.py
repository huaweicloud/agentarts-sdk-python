#
# Copyright (c) Huawei Technologies CO., Ltd. 2022-2025. All rights reserved.
#
# coding=utf-8
import os
import requests
from apig_sdk import signer
from demo_v11 import demo_app_v11


def demo_app():
    sig = signer.Signer()
    # 认证用的ak和sk硬编码到代码中或者明文存储都有很大的安全风险，建议在配置文件或者环境变量中密文存放，使用时解密，确保安全；
    # 本示例以ak和sk保存在环境变量中为例，运行本示例前请先在本地环境中设置环境变量HUAWEICLOUD_SDK_AK和HUAWEICLOUD_SDK_SK。
    # sig.Key = ""
    # sig.Secret = ""
    sig.Key = os.getenv('HUAWEICLOUD_SDK_AK')
    sig.Secret = os.getenv('HUAWEICLOUD_SDK_SK')

    method = "POST"
    url = "http://127.0.0.1/test?ip=127.0.0.1"
    headers = {"host": "test.com"}
    body = "{'success':'ok'}"

    # sign
    r = signer.HttpRequest(method, url, headers, body)
    sig.Sign(r)
    print(r.headers["X-Sdk-Date"])
    print(r.headers["Authorization"])
    resp = requests.request(method, url, headers=r.headers, data=body)
    print(resp.status_code, resp.reason)
    print(resp.content)

    # verify
    v = sig.Verify(r, r.headers["Authorization"])
    print(v)


if __name__ == '__main__':
    demo_app()
    demo_app_v11()
