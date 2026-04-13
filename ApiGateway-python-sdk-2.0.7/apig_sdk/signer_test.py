# Copyright Huawei Technologies Co., Ltd. 2024-2025. All rights reserved.

import os
from unittest import TestCase, mock
import signer
from signer import *

DateFormat = "%Y%m%dT%H%M%SZ"

class Test(TestCase):
    def test_hmacsha256(self):
        ans = hmacsha256("abc", "abc")
        self.assertEqual(b'/\x02\xe2J\xe2\xe1\xfe\x88\x03\x99\xf2v\x00\xaf\xa8\x83d\xe6\x06+'
            b'\xf9\xbb\xe1\x14\xb3/\xa8\xf2=\x03`\x8a', ans)

    def test_StringToSign(self):
        canonicalRequest = '''POST
            /app1%3Fa%3D1/
            a=1
            host:30030113-3657-4fb6-a7ef-90764239b038.apigw.cn-north-1.huaweicloud.com
            x-sdk-date:20240326T030801Z
            x-stage:RELEASE
            
            host;x-sdk-date;x-stage
            230d8358dc8e8890b4c58deeb62912ee2f20357ae92a5cc861b98e68fe31acb5'''
        time = datetime.strptime('20240326T030801Z', DateFormat)
        ans = StringToSign(canonicalRequest, time)
        self.assertEqual('''SDK-HMAC-SHA256
20240326T030801Z
5847720941657701137ad8098b63585092cea7d982e14b2efd0a668460f2da2a''', ans)

    def test_urlencode(self):
        ans = urlencode("abc")
        self.assertEqual('abc', ans)

    def test_findHeader(self):
        r = HttpRequest("POST",
                               "https://30030113-3657-4fb6-a7ef-90764239b038.apigw.cn-north-1.huaweicloud.com/app1?a=1",
                               {"x-stage": "RELEASE"},
                               "body")
        ans = findHeader(r, 'X-abc-Date')
        self.assertEqual(None, ans)
        ans = findHeader(r, 'x-stage')
        self.assertEqual('RELEASE', ans)

    def test_CanonicalRequest(self):
        r = HttpRequest("POST",
                        "https://30030113-3657-4fb6-a7ef-90764239b038.apigw.cn-north-1.huaweicloud.com/app1?a=1",
                        {"x-stage": "RELEASE"},
                        "body")
        ans = CanonicalRequest(r, ['x-stage'])
        self.assertEqual('''POST
/app1/
a=1
x-stage:RELEASE

x-stage
230d8358dc8e8890b4c58deeb62912ee2f20357ae92a5cc861b98e68fe31acb5''', ans)

    def test_SignedHeaders(self):
        r = HttpRequest("POST",
                        "https://30030113-3657-4fb6-a7ef-90764239b038.apigw.cn-north-1.huaweicloud.com/app1?a=1",
                        {"x-stage": "RELEASE"},
                        "body")
        ans = SignedHeaders(r)
        self.assertEqual(['x-stage'], ans)

    def test_SignStringToSign(self):
        ans = SignStringToSign("abc", "abc")
        self.assertEqual('2f02e24ae2e1fe880399f27600afa88364e6062bf9bbe114b32fa8f23d03608a', ans)

    def test_AuthHeaderValue(self):
        ans = AuthHeaderValue('abcdefghijklmnopqrst1234567890', 'ABCDE12345', ['host', 'x-sdk-date', 'x-stage'])
        self.assertEqual('SDK-HMAC-SHA256 Access=ABCDE12345, SignedHeaders=host;x-sdk-date;x-stage, Signature=abcdefghijklmnopqrst1234567890', ans)

    @mock.patch.object(signer, 'findHeader', mock.Mock(return_value='20240326T030801Z'))
    @mock.patch.object(signer, 'CanonicalQueryString', mock.Mock(return_value='abc'))
    @mock.patch.object(signer, 'SignedHeaders', mock.Mock())
    @mock.patch.object(signer, 'CanonicalRequest', mock.Mock())
    @mock.patch.object(signer, 'StringToSign', mock.Mock())
    @mock.patch.object(signer, 'SignStringToSign', mock.Mock())
    @mock.patch.object(signer, 'AuthHeaderValue', mock.Mock(return_value='abcde'))
    def test_Sign(self):
        r = HttpRequest("POST",
                        "https://30030113-3657-4fb6-a7ef-90764239b038.apigw.cn-north-1.huaweicloud.com/app1?a=1",
                        {"x-stage": "RELEASE"},
                        "body")
        sig = Signer()
        sig.Key = 'abcdefg12345'
        sig.Secret = '12345abcdefg'
        sig.Sign(r)
        self.assertEqual('abcde', r.headers["Authorization"])
        self.assertEqual('/app1', r.uri)
        self.assertEqual(['1'], r.query.get("a"))
        self.assertEqual(b'body', r.body)
        self.assertEqual('30030113-3657-4fb6-a7ef-90764239b038.apigw.cn-north-1.huaweicloud.com', r.headers["host"])

    @mock.patch.object(signer, 'findHeader', mock.Mock(return_value='20240326T030801Z'))
    @mock.patch.object(signer, 'SignedHeaders', mock.Mock())
    @mock.patch.object(signer, 'CanonicalRequest', mock.Mock())
    @mock.patch.object(signer, 'StringToSign', mock.Mock())
    @mock.patch.object(signer, 'SignStringToSign', mock.Mock())
    @mock.patch.object(signer, 'AuthHeaderValue', mock.Mock(return_value='abcde'))
    def test_Verify(self):
        r = HttpRequest("POST",
                        "https://30030113-3657-4fb6-a7ef-90764239b038.apigw.cn-north-1.huaweicloud.com/app1?a=1",
                        {"x-stage": "RELEASE"},
                        "body")
        sig = Signer()
        sig.Key = 'abcdefg12345'
        sig.Secret = '12345abcdefg'
        ans = sig.Verify(r, '123')
        self.assertEqual(False, ans)

        ans = sig.Verify(r, 'abcde')
        self.assertEqual(True, ans)