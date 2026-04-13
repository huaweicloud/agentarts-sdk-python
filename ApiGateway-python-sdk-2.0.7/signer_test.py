#
# Copyright (c) Huawei Technologies CO., Ltd. 2025. All rights reserved.
#
import binascii
import hashlib
import hmac
import sys
import unittest
from apig_sdk import signer
from datetime import datetime, timedelta


class TestUtilityFunctions(unittest.TestCase):
    def test_urlencode(self):
        self.assertEqual(signer.urlencode("hello world"), "hello%20world")
        self.assertEqual(signer.urlencode("a/b/c"), "a%2Fb%2Fc")
        self.assertEqual(signer.urlencode("a~b"), "a~b")

    def test_findHeader(self):
        req = signer.HttpRequest()
        req.headers = {"Content-Type": "application/json", "X-Test": "value"}
        self.assertEqual(signer.findHeader(req, "content-type"), "application/json")
        self.assertIsNone(signer.findHeader(req, "non-existent"))

    def test_HexEncodeSHA256Hash(self):
        self.assertEqual(signer.HexEncodeSHA256Hash(b"test"),
                         hashlib.sha256(b"test").hexdigest())

    def test_CanonicalURI(self):
        req = signer.HttpRequest(u="https://example.com/api/v1/test")
        self.assertEqual(signer.CanonicalURI(req), "/api/v1/test/")

    def test_CanonicalQueryString(self):
        req = signer.HttpRequest(u="https://example.com/api?param1=value1&param2=value2")
        self.assertIn("param1=value1", signer.CanonicalQueryString(req))
        self.assertIn("param2=value2", signer.CanonicalQueryString(req))

    def test_CanonicalHeaders(self):
        req = signer.HttpRequest()
        req.headers = {"Content-Type": "application/json", "X-Test": "value"}
        signed_headers = ["content-type", "x-test"]
        self.assertIn("content-type:application/json",
                      signer.CanonicalHeaders(req, signed_headers))
        self.assertIn("x-test:value",
                      signer.CanonicalHeaders(req, signed_headers))

    def test_SignedHeaders(self):
        req = signer.HttpRequest()
        req.headers = {"Content-Type": "application/json", "X-Test": "value"}
        self.assertEqual(signer.SignedHeaders(req), ["content-type", "x-test"])

    def test_process_headers(self):
        headers = {"Content-Type": "application/json", "X-Test": "value"}
        signer._process_headers("SignedHeaders=content-type", headers)
        self.assertIn("Content-Type", headers)
        self.assertNotIn("X-Test", headers)


class TestSigner(unittest.TestCase):
    def setUp(self):
        self.key = "test_key"
        self.secret = "test_secret"
        self.region = "test_region"
        self.now = datetime.utcnow()
        self.headers = {
            "host": "example.com",
            "x-sdk-date": self.now.strftime("%Y%m%dT%H%M%SZ"),
            "content-type": "application/json"
        }
        self.request = signer.HttpRequest(
            m="GET",
            u="https://example.com/api/v1/test?param1=value1&param2=value2",
            h=self.headers,
            b='{"test": "data"}'
        )

    def test_Signer_init_success(self):
        # init with default
        sig = signer.Signer()
        self.assertEqual(sig.algorithm, "SDK-HMAC-SHA256")

        # init with v11
        sig = signer.Signer(algorithm="V11-HMAC-SHA256", region_id=self.region)
        self.assertEqual(sig.algorithm, "V11-HMAC-SHA256")

    def test_Signer_init_with_v11_without_region_id(self):
        with self.assertRaises(ValueError):
            sig = signer.Signer(algorithm="V11-HMAC-SHA256")

    def test_Verify_Success(self):
        sig = signer.Signer()
        sig.Key = self.key
        sig.Secret = self.secret

        sig.Sign(self.request)
        self.assertTrue(sig.Verify(self.request, self.request.headers["Authorization"]))

    def test_Verify_Raises(self):
        sig = signer.Signer()
        sig.Key = self.key
        sig.Secret = self.secret
        with self.assertRaises(ValueError):
            sig.Verify(self.request, "invalid_signature")

    def test_Sign_success(self):
        sig = signer.Signer()
        sig.Key = self.key
        sig.Secret = self.secret

        sig.Sign(self.request)
        self.assertIn("Authorization", self.request.headers)
        self.assertTrue(self.request.headers["Authorization"].startswith("SDK-HMAC-SHA256"))

    def test_canonical_request_success(self):
        sig = signer.Signer()
        sig.Key = self.key
        sig.Secret = self.secret

        signed_headers = ["content-type", "host", "x-sdk-date"]
        cr = sig._canonical_request(self.request, signed_headers)
        self.assertIn("GET", cr)
        self.assertIn("/api/v1/test/", cr)
        self.assertIn("param1=value1", cr)
        self.assertIn("param2=value2", cr)
        self.assertIn("content-type:", cr)
        self.assertIn("host:", cr)
        self.assertIn("x-sdk-date:", cr)

    def test_get_not_sign_body_header_key(self):
        sig = signer.Signer()
        self.assertEqual(sig._get_not_sign_body_header_key(), "x-sdk-content-sha256")

        sig = signer.Signer(algorithm="SDK-HMAC-SM3")
        self.assertEqual(sig._get_not_sign_body_header_key(), "x-sdk-content-sm3")

    def test_get_auth_value(self):
        sig = signer.Signer()
        sig.Key = self.key
        sig.Secret = self.secret

        auth_value = sig._get_auth_value(self.request)
        self.assertIn("SDK-HMAC-SHA256", auth_value)
        self.assertIn("Access=test_key", auth_value)
        self.assertIn("Signature=", auth_value)

    def test_sign_string_to_sign(self):
        sig = signer.Signer()
        sig.Secret = self.secret

        string_to_sign = "test_string"
        signature = sig.sign_string_to_sign(self.secret, string_to_sign)
        self.assertEqual(signature, binascii.hexlify(
            hmac.new(self.secret.encode(), string_to_sign.encode(),
                     digestmod=hashlib.sha256).digest()
        ).decode())

    def test_auth_header_value(self):
        sig = signer.Signer()
        sig.Key = self.key

        signature = "test_signature"
        signed_headers = ["content-type", "host"]
        auth_header = sig.auth_header_value(signature, signed_headers)
        self.assertEqual(auth_header,
                         "SDK-HMAC-SHA256 Access=test_key, SignedHeaders=content-type;host, Signature=test_signature")

    def test_hex_encode_hash(self):
        sig = signer.Signer()
        data = b"test_data"
        self.assertEqual(sig.hex_encode_hash(data), hashlib.sha256(data).hexdigest())

    def test_new_hmac_with_python_2_3(self):
        sig = signer.Signer()
        byte = "test_key"
        msg = "test_message"

        # Python 2测试
        if sys.version_info.major < 3:
            hmac_result = sig._new_hmac(byte, msg)
            self.assertEqual(hmac_result,
                             hmac.new(byte, msg, digestmod=hashlib.sha256).digest())
        # Python 3测试
        else:
            hmac_result = sig._new_hmac(byte, msg)
            self.assertEqual(hmac_result,
                             hmac.new(byte.encode(signer.UTF8), msg.encode(signer.UTF8),
                                      digestmod=hashlib.sha256).digest())

    def test_get_string_to_sign_with_python_2_3(self):
        sig = signer.Signer()
        sig.Key = self.key
        sig.Secret = self.secret

        # Python 2测试
        if sys.version_info.major < 3:
            string_to_sign = sig._get_string_to_sign(b"test_request", self.now)
            self.assertIn("SDK-HMAC-SHA256", string_to_sign)
            self.assertIn(self.now.strftime("%Y%m%dT%H%M%SZ"), string_to_sign)
        # Python 3测试
        else:
            string_to_sign = sig._get_string_to_sign("test_request", self.now)
            self.assertIn("SDK-HMAC-SHA256", string_to_sign)
            self.assertIn(self.now.strftime("%Y%m%dT%H%M%SZ"), string_to_sign)


class TestHttpRequest(unittest.TestCase):
    def test_init_with_query_params(self):
        req = signer.HttpRequest(u="https://example.com/api?param1=value1&param2=value2")
        self.assertEqual(req.query, {"param1": ["value1"], "param2": ["value2"]})

        req = signer.HttpRequest(u="https://example.com/api?param1=value1&param1=value2")
        self.assertEqual(req.query, {"param1": ["value1", "value2"]})

    def test_init_with_headers(self):
        headers = {"Content-Type": "application/json", "X-Test": "value"}
        req = signer.HttpRequest(h=headers)
        self.assertEqual(req.headers, headers)

    def test_init_with_body(self):
        # Python 2测试
        if sys.version_info.major < 3:
            req = signer.HttpRequest(b="test_body")
            self.assertEqual(req.body, "test_body")
        # Python 3测试
        else:
            req = signer.HttpRequest(b="test_body")
            self.assertEqual(req.body, b"test_body")

    def test_uri_parsing(self):
        req = signer.HttpRequest(u="https://example.com/api/v1/test")
        self.assertEqual(req.scheme, "https")
        self.assertEqual(req.host, "example.com")
        self.assertEqual(req.uri, "/api/v1/test")


if __name__ == '__main__':
    unittest.main()
