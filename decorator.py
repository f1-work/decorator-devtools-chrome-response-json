import functools
import json

import trio

from selenium import webdriver
from selenium.webdriver import DesiredCapabilities
from selenium.webdriver.chrome.options import Options as ChromeOptions


def get_response_json(pattern, timeout=10, max_results=1):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            _class = args[0]
            _class._finish_request_id = []
            _class._response_json = []

            async def start_listening():
                def log_filter(log_):
                    return (log_['method'] == 'Network.responseReceived'
                            and 'json' in log_['params']['response']['mimeType']
                            and log_['params']['type'] == 'XHR'
                            )
                with trio.move_on_after(timeout):
                    while True:
                        await trio.sleep(0.1)
                        logs_raw = _class.driver.get_log('performance')
                        logs = [json.loads(lr['message'])['message'] for lr in logs_raw]
                        for log in filter(log_filter, logs):
                            request_id = log['params']['requestId']
                            resp_url = log['params']['response']['url']
                            if (pattern in resp_url) and (request_id not in _class._finish_request_id):
                                result = _class.driver.execute_cdp_cmd('Network.getResponseBody', {'requestId': request_id})
                                _class._finish_request_id.append(request_id)
                                _class._response_json.append(result)
                            if len(_class._response_json) == max_results:
                                return

            async def main():
                    async with trio.open_nursery() as nursery:
                        nursery.start_soon(start_listening)
                        func(*args, **kwargs)
                        return
            trio.run(main)
            return
        return wrapper
    return decorator

class ForTest:
    def __init__(self):
        chrome_options = ChromeOptions()
        chrome_options.headless = False
        capabilities = DesiredCapabilities.CHROME
        capabilities['goog:loggingPrefs'] = {'performance': 'ALL'}
        self.driver = webdriver.Chrome(
    desired_capabilities=capabilities,
    options=chrome_options,
    executable_path="chromedriver.exe")

    @get_response_json(pattern="mail", timeout=10, max_results=100)
    def for_decorate(self):
        self.driver.get("https://mail.ru/")


if __name__ == "__main__":
    test = ForTest()
    test.for_decorate()
    print(len(test._response_json))
    # print(test._response_json)