import os
import random
import shutil
import string
import sys

import requests

try:
    from tqdm.auto import tqdm
except ImportError:
    print("Trying to Install required module: tqdm\n")
    os.system('pip3 install --user tqdm')
    try:
        from tqdm.auto import tqdm
    except ImportError:
        sys.exit('Please install module tqdm from http://pypi.python.org/pypi/tqdm or run: pip3 install tqdm.')

ADOBE_PRODUCTS_XML_URL = 'https://prod-rel-ffc-ccm.oobesaas.adobe.com/adobe-ffc-external/core/v{urlVersion}/products/' \
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

session = requests.sessions.Session()
cdn = None
cache_dir = None


def get_adobe_products_file(url_version, allowed_platforms):
    if cache_dir:
        path = os.path.join(cache_dir, '_products', str(url_version), '.'.join(allowed_platforms) + '.xml')
        os.makedirs(path[:path.rfind('/')], exist_ok=True)
        return path


def get_adobe_product_json(build_guid):
    if cache_dir:
        path = os.path.join(cache_dir, '_builds', build_guid + '.json')
        os.makedirs(path[:path.rfind('/')], exist_ok=True)
        return path


def get_adobe_product_file(path):
    if cache_dir:
        path = cache_dir + path
        os.makedirs(path[:path.rfind('/')], exist_ok=True)
        return path


def get_adobe_products_url(url_version, allowed_platforms):
    return ADOBE_PRODUCTS_XML_URL.format(urlVersion=url_version, installPlatform=','.join(allowed_platforms))


def set_header_auth(auth):
    if auth:
        ADOBE_REQ_HEADERS['Authorization'] = auth


def set_cdn(url):
    global cdn
    cdn = url


def set_cache_dir(path):
    global cache_dir
    cache_dir = path


def fetch_url_as_string(url, headers=ADOBE_REQ_HEADERS):
    """Retrieve from a url as a string."""
    print('Fetch: ' + url)
    req = session.get(url, headers=headers)
    req.encoding = 'utf-8'
    return req.text


def fetch_url_as_file(url, path, headers=ADOBE_REQ_HEADERS):
    """Retrieve from a url and save to file"""
    response = session.head(url, stream=True, headers=headers)
    total_size_in_bytes = int(response.headers.get('content-length', 0))

    if os.path.isfile(path):
        if total_size_in_bytes == 0 or os.path.getsize(path) == total_size_in_bytes:
            return
        print('remove outdated file: ' + path)
        os.remove(path)

    print('Fetch: ' + url)
    response = session.get(url, stream=True, headers=headers)
    if total_size_in_bytes != 0:
        if total_size_in_bytes >> 28:
            block_size = 0x1000000
        elif total_size_in_bytes >> 24:
            block_size = 0x100000
        elif total_size_in_bytes >> 20:
            block_size = 0x10000
        elif total_size_in_bytes >> 16:
            block_size = 0x1000
        else:
            block_size = 0x400

        progress_bar = tqdm(total=total_size_in_bytes, unit='iB', unit_scale=True)
        with open(path, 'wb') as file:
            for data in response.iter_content(block_size):
                progress_bar.update(len(data))
                file.write(data)
        progress_bar.close()
        if progress_bar.n != total_size_in_bytes:
            print("ERROR, something went wrong")
            exit(1)
    else:
        with open(path, 'wb') as file:
            for data in response.iter_content(4096):
                file.write(data)


def fetch_products_xml(url_version, allowed_platforms):
    adobe_xml = get_adobe_products_file(url_version, allowed_platforms)
    if adobe_xml and os.path.exists(adobe_xml):
        print('Read products xml from ' + adobe_xml)
        with open(adobe_xml, 'r') as f:
            return f.read()

    adobe_url = get_adobe_products_url(url_version, allowed_platforms)
    print('Downloading products xml')
    if adobe_xml:
        fetch_url_as_file(adobe_url, adobe_xml)
        with open(adobe_xml, 'r') as f:
            return f.read()

    return fetch_url_as_string(adobe_url)


def fetch_app_xml(path):
    file_path = get_adobe_product_file(path)
    if file_path and os.path.exists(file_path):
        with open(file_path, 'r') as f:
            return f.read()

    if file_path:
        fetch_url_as_file(cdn + path, file_path)
        with open(file_path, 'r') as f:
            return f.read()

    return fetch_url_as_string(cdn + path)


def fetch_application_json(build_guid):
    """Retrieve JSON."""
    headers = ADOBE_REQ_HEADERS.copy()
    headers['x-adobe-build-guid'] = build_guid
    file_path = get_adobe_product_json(build_guid)
    if file_path and os.path.exists(file_path):
        with open(file_path, 'rb') as f:
            return f.read()

    if file_path:
        fetch_url_as_file(ADOBE_APPLICATION_JSON_URL, file_path, headers)
        with open(file_path, 'rb') as f:
            return f.read()

    return fetch_url_as_string(ADOBE_APPLICATION_JSON_URL, headers)


def fetch_file(path, product_dir, sap_code, version, skip_existing=False, skip_create_app=False, name=None):
    """Download a file"""
    if not name:
        name = path.split('/')[-1].split('?')[0]
    print('[{}_{}] Downloading {}'.format(sap_code, version, name))

    url = cdn + path
    cache_file_path = get_adobe_product_file(path)
    fetch_url_as_file(url, cache_file_path)

    file_path = os.path.join(product_dir, name)
    if skip_existing and os.path.isfile(file_path) and os.path.getsize(file_path) == os.path.getsize(cache_file_path):
        print('[{}_{}] {} already exists, skipping'.format(sap_code, version, name))
    elif skip_create_app is False:
        shutil.copyfile(cache_file_path, file_path)
