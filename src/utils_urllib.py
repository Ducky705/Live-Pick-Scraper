
import json
import urllib.request
import urllib.error
import urllib.parse
import ssl
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Bypass SSL verification if needed (simulating requests.verify=False if arg passed, though we default to secure)
# For this environment, we might need standard context
ctx = ssl.create_default_context()
# ctx.check_hostname = False
# ctx.verify_mode = ssl.CERT_NONE

class Response:
    def __init__(self, status, data, headers):
        self.status_code = status
        self._data = data
        self.headers = headers
        self.text = data.decode('utf-8') if data else ""
        
    def json(self):
        return json.loads(self.text)
        
    def raise_for_status(self):
        if 400 <= self.status_code < 600:
            raise Exception(f"HTTP Error {self.status_code}: {self.text}")

def request(method: str, url: str, headers: Dict[str, str] = None, json_data: Any = None, timeout: int = 30) -> Response:
    if headers is None:
        headers = {}
        
    data = None
    if json_data is not None:
        data = json.dumps(json_data).encode('utf-8')
        headers['Content-Type'] = 'application/json'
        
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as f:
            resp_data = f.read()
            return Response(f.status, resp_data, f.headers)
    except urllib.error.HTTPError as e:
        error_data = e.read()
        return Response(e.code, error_data, e.headers)
    except Exception as e:
        logger.error(f"Request Failed: {e}")
        raise e

def post(url, **kwargs):
    return request("POST", url, headers=kwargs.get("headers"), json_data=kwargs.get("json"), timeout=kwargs.get("timeout", 30))

def get(url, **kwargs):
    return request("GET", url, headers=kwargs.get("headers"), timeout=kwargs.get("timeout", 30))
