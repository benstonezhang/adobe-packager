import json
import os
import random
import shutil
import string
import time
from xml.etree import ElementTree as ET

import requests
from requests.exceptions import ReadTimeout, ConnectionError
from tqdm.auto import tqdm

from ccdl.utils import check_archive

ADOBE_PRODUCTS_XML_URL = 'https://prod-rel-ffc-ccm.oobesaas.adobe.com/adobe-ffc-external/core/v{url_version}/products/' \
                         'all?_type=xml&channel=ccm&channel=sti&platform={installPlatform}&productType=Desktop'
ADOBE_APPLICATION_JSON_URL = 'https://cdn-ffc.oobesaas.adobe.com/core/v3/applications'

ADOBE_REQ_HEADERS = {
    'X-Adobe-App-Id': 'accc-apps-panel-desktop',
    'User-Agent': 'Adobe Application Manager 2.0',
    'X-Api-Key': 'CC_HD_ESD_1_0',
    'Cookie': 'fg=' + ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(26)) + '======'
}

ADOBE_DL_HEADERS = {
    'User-Agent': 'Creative Cloud'
}

cdn = None
cache_dir = None
session = requests.sessions.Session()
session_timeout = 15
session_retry_count = 10
session_retry_delay = 3


def set_cache_dir(path):
    global cache_dir
    cache_dir = path


def set_header_auth(auth):
    ADOBE_REQ_HEADERS['Authorization'] = auth


def set_cdn(url):
    global cdn
    cdn = url


def get_cache_products_xml(url_version, allowed_platforms):
    if cache_dir:
        path = os.path.join(cache_dir, '_products', str(url_version), '_'.join(allowed_platforms) + '.xml')
        os.makedirs(path[:path.rfind('/')], exist_ok=True)
        return path


def get_cache_product_json(build_guid):
    if cache_dir:
        path = os.path.join(cache_dir, '_applications', build_guid + '.json')
        os.makedirs(path[:path.rfind('/')], exist_ok=True)
        return path


def get_cache_product_file(path):
    if cache_dir:
        path = cache_dir + path
        os.makedirs(path[:path.rfind('/')], exist_ok=True)
        return path


def get_adobe_products_url(url_version, allowed_platforms):
    return ADOBE_PRODUCTS_XML_URL.format(url_version=url_version, installPlatform=','.join(allowed_platforms))


def get_block_size(total_size_in_bytes):
    if total_size_in_bytes >> 28:
        block_size = 0x400000
    elif total_size_in_bytes >> 24:
        block_size = 0x80000
    elif total_size_in_bytes >> 20:
        block_size = 0x10000
    elif total_size_in_bytes >> 16:
        block_size = 0x2000
    else:
        block_size = 0x400
    return block_size


def fetch_url_as_text(url, headers=ADOBE_REQ_HEADERS):
    """Retrieve from a url as a string."""
    print('Fetch: ' + url)
    for _ in range(0, session_retry_count):
        try:
            response = session.get(url, headers=headers, timeout=session_timeout)
            response.encoding = 'utf-8'
            return response.text
        except (ConnectionError, ReadTimeout):
            time.sleep(session_retry_delay)
    print('Connection error, give up')
    exit(1)


def fetch_url_head(url, headers):
    for _ in range(0, session_retry_count):
        try:
            return session.head(url, stream=True, headers=headers, timeout=session_timeout)
        except (ConnectionError, ReadTimeout):
            time.sleep(session_retry_delay)
    print('Connection error, give up')
    exit(1)


def fetch_url_get_progress(url, path, headers):
    print('Fetch: ' + url + '\n   --> ' + path)
    for _ in range(0, session_retry_count):
        progress_bar = None
        try:
            response = session.get(url, stream=True, headers=headers, timeout=session_timeout)
            total_size_in_bytes = int(response.headers.get('content-length', 0))
            block_size = get_block_size(total_size_in_bytes)
            if total_size_in_bytes != 0:
                progress_bar = tqdm(total=total_size_in_bytes, unit='iB', unit_scale=True)
                with open(path, 'wb') as file:
                    for data in response.iter_content(block_size):
                        file.write(data)
                        progress_bar.update(len(data))
                progress_bar.close()
                if progress_bar.n < total_size_in_bytes:
                    print("Error, expect {} bytes, received {} bytes.".format(total_size_in_bytes, progress_bar.n))
                    exit(1)
            else:
                with open(path, 'wb') as file:
                    for data in response.iter_content(block_size):
                        file.write(data)
                        print('.', end='', flush=True)
                    print('')
            return

        except (ConnectionError, ReadTimeout):
            if progress_bar:
                progress_bar.close()
            time.sleep(session_retry_delay)
    print('Connection error, give up')
    exit(1)


def fetch_url_as_file(url, path, headers=ADOBE_REQ_HEADERS):
    """Retrieve from a url and save to file"""
    response = fetch_url_head(url, headers)
    total_size_in_bytes = int(response.headers.get('content-length', 0))

    if os.path.isfile(path):
        if total_size_in_bytes == 0 or os.path.getsize(path) == total_size_in_bytes:
            return
        print('remove outdated file: ' + path)
        os.remove(path)

    fetch_url_get_progress(url, path, headers)

    if check_archive(path) is False:
        print('Remove corrupt file and exit: ' + path)
        os.remove(path)
        exit(1)


def parse_xml(text, path=None, corrupt_exit=False):
    try:
        return ET.fromstring(text)
    except Exception as e:
        print('XML parse failed: ' + str(e))
        if path and os.path.exists(path):
            os.remove(path)
    if corrupt_exit:
        print('Corrupt products xml received, exit')
        exit(1)


def fetch_products_xml(url_version, allowed_platforms):
    cache_xml = get_cache_products_xml(url_version, allowed_platforms)
    if cache_xml and os.path.exists(cache_xml):
        print('Read products xml from ' + cache_xml)
        with open(cache_xml, 'r') as f:
            products_xml_text = f.read()
        products_xml = parse_xml(products_xml_text, cache_xml)
        if products_xml:
            return products_xml

    products_url = get_adobe_products_url(url_version, allowed_platforms)
    print('Downloading products xml')
    if cache_xml:
        fetch_url_as_file(products_url, cache_xml)
        with open(cache_xml, 'r') as f:
            products_xml_text = f.read()
        return parse_xml(products_xml_text, cache_xml, corrupt_exit=True)

    return parse_xml(fetch_url_as_text(products_url), corrupt_exit=True)


def fetch_app_xml(path):
    cache_xml = get_cache_product_file(path)
    if cache_xml and os.path.exists(cache_xml):
        print('Read application xml from ' + cache_xml)
        with open(cache_xml, 'r') as f:
            app_xml_text = f.read()
        app_xml = parse_xml(app_xml_text, cache_xml)
        if app_xml:
            return app_xml

    print('Downloading application xml')
    if cache_xml:
        fetch_url_as_file(cdn + path, cache_xml)
        with open(cache_xml, 'r') as f:
            app_xml_text = f.read()
        return parse_xml(app_xml_text, cache_xml, corrupt_exit=True)

    return parse_xml(fetch_url_as_text(cdn + path), corrupt_exit=True)


def parse_json(text, path=None, corrupt_exit=False):
    try:
        return json.loads(text)
    except Exception as e:
        print('JSON parse failed:' + str(e))
        if path and os.path.exists(path):
            os.remove(path)
    if corrupt_exit:
        print('Corrupt JSON received, exit')
        exit(1)


def fetch_application_json(build_guid):
    """Retrieve JSON."""
    headers = ADOBE_REQ_HEADERS.copy()
    headers['x-adobe-build-guid'] = build_guid
    file_path = get_cache_product_json(build_guid)
    if file_path and os.path.exists(file_path):
        with open(file_path, 'rb') as f:
            json_text = f.read()
        json_obj = parse_json(json_text, file_path)
        if json_obj:
            return json_obj

    if file_path:
        fetch_url_as_file(ADOBE_APPLICATION_JSON_URL, file_path, headers)
        with open(file_path, 'rb') as f:
            json_text = f.read()
        return parse_json(json_text, file_path, corrupt_exit=True)

    return parse_json(fetch_url_as_text(ADOBE_APPLICATION_JSON_URL, headers), corrupt_exit=True)


def fetch_file(path, app_dir, sap_code, version, name=None):
    """Download a file"""
    if path[:4] != 'http':
        url = cdn + path
    else:
        url = path
        path = path[path.find('/', path.find('//') + 3):]

    if not name:
        name = path.split('/')[-1].split('?')[0]
    print('[{}_{}] Retrieve {}'.format(sap_code, version, name))

    cache_file_path = get_cache_product_file(path)
    fetch_url_as_file(url, cache_file_path)

    if app_dir:
        file_path = os.path.join(app_dir, name)
        if os.path.isfile(file_path) and os.path.getsize(file_path) == os.path.getsize(cache_file_path):
            print('[{}_{}] {} already exists, skipping'.format(sap_code, version, name))
        else:
            shutil.copyfile(cache_file_path, file_path)
