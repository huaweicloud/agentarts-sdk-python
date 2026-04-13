from flask import Flask
from flask import request
from functools import wraps
import os
import re
from datetime import datetime
from datetime import timedelta
from apig_sdk import signer

app = Flask(__name__)


def requires_apigateway_signature():
    def wrapper(f):

        secrets = {
            # 认证用的ak和sk硬编码到代码中或者明文存储都有很大的安全风险，建议在配置文件或者环境变量中密文存放，使用时解密，确保安全；
            # 本示例以ak和sk保存在环境变量中为例，运行本示例前请先在本地环境中设置环境变量HUAWEICLOUD_SDK_AK1和HUAWEICLOUD_SDK_SK1、HUAWEICLOUD_SDK_AK2和HUAWEICLOUD_SDK_SK2。
            os.getenv('HUAWEICLOUD_SDK_AK1'): os.getenv('HUAWEICLOUD_SDK_SK1'),
            os.getenv('HUAWEICLOUD_SDK_AK2'): os.getenv('HUAWEICLOUD_SDK_SK2'),
        }
        authorizationPattern = re.compile(
            r'SDK-HMAC-SHA256\s+Access=([^,]+),\s?SignedHeaders=([^,]+),\s?Signature=(\w+)')
        BasicDateFormat = "%Y%m%dT%H%M%SZ"

        @wraps(f)
        def wrapped(*args, **kwargs):
            if "authorization" not in request.headers:
                return 'Authorization not found.', 401
            authorization = request.headers['authorization']
            m = authorizationPattern.match(authorization)
            if m is None:
                return 'Authorization format incorrect.', 401
            signingKey = m.group(1)
            if signingKey not in secrets:
                return 'Signing key not found.', 401
            signingSecret = secrets[signingKey]
            signedHeaders = m.group(2).split(";")
            r = signer.HttpRequest()
            r.method = request.method
            r.uri = request.path
            r.query = {}
            for k in request.query_string.decode('utf-8').split('&'):
                spl = k.split("=", 1)
                if spl[0] != "":
                    if len(spl) < 2:
                        r.query[spl[0]] = ""
                    else:
                        r.query[spl[0]] = spl[1]

            r.headers = {}
            needbody = True
            dateHeader = None
            for k in signedHeaders:
                if k not in request.headers:
                    return 'Signed header ' + k + ' not found', 401
                v = request.headers[k]
                if k.lower() == 'x-sdk-content-sha256' and v == 'UNSIGNED-PAYLOAD':
                    needbody = False
                if k.lower() == 'x-sdk-date':
                    dateHeader = v
                r.headers[k] = v
            if needbody:
                r.body = request.get_data()

            if dateHeader is None:
                return 'Header x-sdk-date not found.', 401
            t = datetime.strptime(dateHeader, BasicDateFormat)
            if abs(t - datetime.utcnow()) > timedelta(minutes=15):
                return 'Signature expired.', 401

            sig = signer.Signer()
            sig.Key = signingKey
            sig.Secret = signingSecret
            if not sig.Verify(r, m.group(3)):
                return 'Verify authroization failed.', 401
            return f(*args, **kwargs)

        return wrapped

    return wrapper


@app.route("/<id>", methods=['GET', 'POST', 'PUT', 'DELETE'])
@requires_apigateway_signature()
def hello(id):
    return "Hello World!"


if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=8080)
