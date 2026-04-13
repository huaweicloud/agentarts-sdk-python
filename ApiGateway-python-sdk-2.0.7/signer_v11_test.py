#
# Copyright (c) Huawei Technologies CO., Ltd. 2025. All rights reserved.
#

import hashlib
import sys
import unittest
from datetime import datetime
from unittest.mock import patch, MagicMock
from apig_sdk import signer_v11, signer


class TestSignV11(unittest.TestCase):
    def setUp(self):
        self.mock_signer = MagicMock()
        self.mock_signer.Key = "test_key"
        self.mock_signer.Secret = "test_secret"
        self.mock_signer.region_id = "test_region"
        self.mock_signer.algorithm = signer.V11_HMAC_SHA256
        self.mock_signer.hash_func = hashlib.sha256

        self.sign_v11 = signer_v11.SignV11(self.mock_signer)

        self.now = datetime.utcnow()
        self.mock_signer.hex_encode_hash.return_value = "test_hash"

    def test_init(self):
        self.assertEqual(self.sign_v11.signer, self.mock_signer)
        self.assertEqual(self.sign_v11._credential_scope, "")

    def test_set_credential_scope(self):
        self.sign_v11._set_credential_scope(self.now)
        expected_scope = f"{self.now.strftime('%Y%m%d')}/test_region/{signer_v11.APIC}"
        self.assertEqual(self.sign_v11._credential_scope, expected_scope)

    def test_get_auth_header_value(self):
        signed_headers = ["host", "x-sdk-date"]
        signature = "test_signature"
        self.sign_v11._set_credential_scope(self.now)
        result = self.sign_v11._get_auth_header_value("test_key", signed_headers, signature)
        expected = f"V11-HMAC-SHA256 Credential=test_key/{self.now.strftime('%Y%m%d')}/test_region/apic, SignedHeaders=host;x-sdk-date, Signature=test_signature"
        self.assertEqual(result, expected)

    def test_get_real_use_secret(self):
        with patch.object(self.sign_v11, '_hkdf', return_value="test_secret_key") as mock_hkdf:
            result = self.sign_v11._get_real_use_secret("test_key", "test_secret")
            mock_hkdf.assert_called_once_with("test_key", "test_secret", "")
            self.assertEqual(result, "test_secret_key")

    def test_hkdf(self):
        result = self.sign_v11._hkdf("test_key", "test_secret", "test_scope")
        self.assertEqual(len(result), 64)

    def test_generate_auth(self):
        canonical_request = "test_request"
        signed_headers = ["host", "x-sdk-date"]

        with patch.object(self.sign_v11, '_get_string_to_sign', return_value="test_string_to_sign"), \
                patch.object(self.sign_v11, '_get_real_use_secret', return_value="test_real_secret"), \
                patch.object(self.mock_signer, 'sign_string_to_sign', return_value="test_signature"), \
                patch.object(self.sign_v11, '_get_auth_header_value', return_value="test_auth_header"):
            result = self.sign_v11.generate_auth(canonical_request, self.now, signed_headers)

            self.sign_v11._get_string_to_sign.assert_called_once_with(canonical_request, self.now)
            self.sign_v11._get_real_use_secret.assert_called_once_with(self.mock_signer.Key, self.mock_signer.Secret)
            self.mock_signer.sign_string_to_sign.assert_called_once_with("test_real_secret", "test_string_to_sign")
            self.sign_v11._get_auth_header_value.assert_called_once_with(
                self.mock_signer.Key, signed_headers, "test_signature"
            )
            self.assertEqual(result, "test_auth_header")

    def test_generate_auth_with_none_signer(self):
        sign_v11 = signer_v11.SignV11(None)
        with self.assertRaises(ValueError):
            sign_v11.generate_auth("test_request", self.now, ["host"])

    def test_get_string_to_sign_py2(self):
        if sys.version_info.major < 3:
            self.sign_v11._set_credential_scope(self.now)
            result = self.sign_v11._get_string_to_sign(b"test_request", self.now)
            expected = f"V11-HMAC-SHA256\n{self.now.strftime(signer_v11.DATE_FORMAT)}\n{self.now.strftime('%Y%m%d')}/test_region/apic\ntest_hash"
            self.assertEqual(result, expected)

    def test_get_string_to_sign_py3(self):
        if sys.version_info.major >= 3:
            self.sign_v11._set_credential_scope(self.now)
            result = self.sign_v11._get_string_to_sign("test_request", self.now)
            expected = f"V11-HMAC-SHA256\n{self.now.strftime(signer_v11.DATE_FORMAT)}\n{self.now.strftime('%Y%m%d')}/test_region/apic\ntest_hash"
            self.assertEqual(result, expected)


if __name__ == '__main__':
    unittest.main()
