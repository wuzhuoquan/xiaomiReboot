#!/usr/bin/python
# -*-coding:utf-8-*-
# Author: Five
# CreatDate: 2024/4/15 10:18
#


import hashlib
import json
import random
import re
import requests
import time
import urllib.parse


xmtime = int(time.time())
xmrand = int(random.random()*10000)
xmtype = 0
xmpwd = ''
ROUTE_IP = ""


class Xiaomi(object):
    def __init__(self, host):
        self.host_ip = host
        self.schema_host = "http://" + host
        self.key = self.get_xmkey()[0]
        self.deviceid = self.get_deviceid()

    def get_init_info(self):
        """
        获取机器初始化的信息，主要是为了拿 newEncryptMode 来判断是使用 sha256 还是 sha1 来加密密码
        :return:
        """
        url = self.schema_host + "/cgi-bin/luci/api/xqsystem/init_info"
        resp = requests.get(url)
        return resp.json()

    def get_xmkey(self):
        """
        获取加密密码的随机key
        :return:
        """
        url = self.schema_host + "/cgi-bin/luci/web"
        resp = requests.get(url)
        pattern_key =re.compile('key: \'(.*?)\'')
        xmkey = re.findall(pattern_key, resp.text)
        return xmkey

    def get_deviceid(self):
        """
        获取 deviceID
        :return:
        """
        url = self.schema_host + "/cgi-bin/luci/web"
        resp = requests.get(url)
        pattern_key = re.compile('var deviceId = \'(.*?)\'')
        deviceid = re.findall(pattern_key, resp.text)
        return deviceid

    def make_nonece(self):
        """
        合并生成加密key
        :return:
        """
        return "%s_%s_%s_%s" % (xmtype, self.deviceid, xmtime, xmrand)

    def encry_passwd(self):
        """
        加密密码，需要判断一下使用 sha256 还是 sha1 来加密的
        :return:
        """
        init_info = self.get_init_info()
        new_encrypt_mode = init_info.get("newEncryptMode")
        # 判断加密算法
        if new_encrypt_mode and int(new_encrypt_mode) == 1:
            sha_func = hashlib.sha256
        else:
            sha_func = hashlib.sha1
        xmnonce = self.make_nonece()
        xmsha1 = sha_func()
        w = (xmpwd + self.key).encode()
        xmsha1.update(w)
        xmsha2 = sha_func()
        xmsha2.update((xmnonce + xmsha1.hexdigest()).encode())
        return xmsha2.hexdigest()

    def login(self):
        # 登录
        url = self.schema_host + "/cgi-bin/luci/api/xqsystem/login"
        user_agent = 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/47.0.2508.0 Safari/537.36 OPR/34.0.2023.0 (Edition developer)'
        header = {'User-Agent': user_agent, 'Connection': 'keep-alive', 'Host': self.host_ip,
                  'Referer': self.schema_host + '/cgi-bin/luci/web', "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}
        values = {'username': 'admin', 'password': self.encry_passwd(), 'logtype': '2', 'nonce': self.make_nonece()}
        data = urllib.parse.urlencode(values)
        resp = requests.post(url, headers=header, data=data)
        resp_json = json.loads(resp.text)
        if resp_json.get("code") != 0:
            print("login failed")
            raise Exception("login failed")
        path = resp_json.get("url")
        return path

    def reboot(self):
        """
        登录之后获取返回的 path 里面的 stock 字段，然后封装 reboot api 调用重启
        :return:
        """
        path = self.login()
        path_list = path.split("/")
        reboot_path = "/".join(path_list[0:4] + ["api", "xqsystem", "reboot"])
        url = self.schema_host + reboot_path
        params = {"client": "web"}
        resp = requests.get(url, params=params)
        print(resp.status_code)
        print(resp.text)


if __name__ == '__main__':
    xiaomi = Xiaomi(ROUTE_IP)
    xiaomi.reboot()
