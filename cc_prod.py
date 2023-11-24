import json
import os
import random
import string
from collections import OrderedDict
from xml.etree import ElementTree as ET

import requests

from cc_utils import get_progress_bar

session = requests.sessions.Session()

ADOBE_PRODUCTS_XML_URL = 'https://prod-rel-ffc-ccm.oobesaas.adobe.com/adobe-ffc-external/core/v{urlVersion}/products/all?_type=xml&channel=ccm&channel=sti&platform={installPlatform}&productType=Desktop'
ADOBE_APPLICATION_JSON_URL = 'https://cdn-ffc.oobesaas.adobe.com/core/v3/applications'

DRIVER_XML = '''<DriverInfo>
    <ProductInfo>
        <Name>Adobe {name}</Name>
        <SAPCode>{sapCode}</SAPCode>
        <CodexVersion>{version}</CodexVersion>
        <Platform>{installPlatform}</Platform>
        <EsdDirectory>./{sapCode}</EsdDirectory>
        <Dependencies>{dependencies}</Dependencies>
    </ProductInfo>
    <RequestInfo>
        <InstallDir>/Applications</InstallDir>
        <InstallLanguage>{language}</InstallLanguage>
    </RequestInfo>
</DriverInfo>
'''

DRIVER_XML_DEPENDENCY = '''
            <Dependency>
                <SAPCode>{sapCode}</SAPCode>
                <BaseVersion>{version}</BaseVersion>
                <EsdDirectory>./{sapCode}</EsdDirectory>
            </Dependency>
'''

ADOBE_REQ_HEADERS = {
    'X-Adobe-App-Id': 'accc-apps-panel-desktop',
    'User-Agent': 'Adobe Application Manager 2.0',
    'X-Api-Key': 'CC_HD_ESD_1_0',
    'Cookie': 'fg=' + ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(26)) + '======'
}

ADOBE_DL_HEADERS = {
    'User-Agent': 'Creative Cloud'
}


def fetch_url(url, headers=ADOBE_REQ_HEADERS):
    """Retrieve a from a url as a string."""
    req = session.get(url, headers=headers)
    req.encoding = 'utf-8'
    return req.text


def load_products_xml(file_path):
    """First stage of parsing the XML from file."""
    print('Read products xml from ' + file_path)
    with open(file_path, 'r') as f:
        products_xml_text = f.read()
    return ET.fromstring(products_xml_text)


def fetch_products_xml(url_version, allowed_platforms, file_path=None):
    """First stage of parsing the XML from network."""
    adobe_url = ADOBE_PRODUCTS_XML_URL.format(urlVersion=url_version, installPlatform=','.join(allowed_platforms))
    print('Downloading products xml from: ' + adobe_url)
    products_xml_text = fetch_url(adobe_url)
    if file_path:
        print('Save products xml to ' + file_path)
        with open(file_path, 'w') as f:
            f.write(products_xml_text)
    return ET.fromstring(products_xml_text)


def parse_products_xml(products_xml, url_version, allowed_platforms):
    """2nd stage of parsing the XML."""
    if url_version == 6:
        prefix = 'channels/'
    else:
        prefix = ''

    cdn = products_xml.find(prefix + 'channel/cdn/secure').text
    products = {}
    parent_map = {c: p for p in products_xml.iter() for c in p}
    for p in products_xml.findall(prefix + 'channel/products/product'):
        sap = p.get('id')
        hidden = parent_map[parent_map[p]].get('name') != 'ccm'
        display_name = p.find('displayName').text
        product_version = p.get('version')
        if not products.get(sap):
            products[sap] = {
                'hidden': hidden,
                'displayName': display_name,
                'sapCode': sap,
                'versions': OrderedDict()
            }

        for pf in p.findall('platforms/platform'):
            base_version = pf.find('languageSet').get('baseVersion')
            build_guid = pf.find('languageSet').get('buildGuid')
            app_platform = pf.get('id')
            dependencies = list(pf.findall('languageSet/dependencies/dependency'))
            if product_version in products[sap]['versions']:
                if products[sap]['versions'][product_version]['apPlatform'] in allowed_platforms:
                    break  # There's no single-arch binary if macuniversal is available

            if sap == 'APRO':
                base_version = product_version
                if url_version == 4 or url_version == 5:
                    product_version = pf.find('languageSet/nglLicensingInfo/appVersion').text
                if url_version == 6:
                    for b in products_xml.findall('builds/build'):
                        if b.get("id") == sap and b.get("version") == base_version:
                            product_version = b.find('nglLicensingInfo/appVersion').text
                            break
                build_guid = pf.find('languageSet/urls/manifestURL').text
                # This is actually manifest URL

            products[sap]['versions'][product_version] = {
                'sapCode': sap,
                'baseVersion': base_version,
                'productVersion': product_version,
                'apPlatform': app_platform,
                'dependencies': [{'sapCode': d.find('sapCode').text, 'version': d.find('baseVersion').text}
                                 for d in dependencies],
                'buildGuid': build_guid,
                'locale': [lc.attrib.get('name') for lc in pf.findall('languageSet/locales/locale')],
            }

    return products, cdn


def fetch_application_json(build_guid):
    """Retrieve JSON."""
    headers = ADOBE_REQ_HEADERS.copy()
    headers['x-adobe-build-guid'] = build_guid
    return json.loads(fetch_url(ADOBE_APPLICATION_JSON_URL, headers))


def fetch_file(url, product_dir, sap_code, version, skip_existing=False, name=None):
    """Download a file"""
    if not name:
        name = url.split('/')[-1].split('?')[0]
    print('Url is: ' + url)
    print('[{}_{}] Downloading {}'.format(sap_code, version, name))

    file_path = os.path.join(product_dir, name)
    response = session.head(url, stream=True, headers=ADOBE_DL_HEADERS)
    total_size_in_bytes = int(response.headers.get('content-length', 0))

    if skip_existing and os.path.isfile(file_path) and os.path.getsize(file_path) == total_size_in_bytes:
        print('[{}_{}] {} already exists, skipping'.format(sap_code, version, name))
    else:
        response = session.get(url, stream=True, headers=ADOBE_REQ_HEADERS)
        total_size_in_bytes = int(response.headers.get('content-length', 0))
        block_size = 1024  # 1 Kibibyte
        progress_bar = get_progress_bar(total_size_in_bytes)
        with open(file_path, 'wb') as file:
            for data in response.iter_content(block_size):
                progress_bar.update(len(data))
                file.write(data)
        progress_bar.close()
        if total_size_in_bytes != 0 and progress_bar.n != total_size_in_bytes:
            print("ERROR, something went wrong")


def get_url_version(url_version):
    if url_version:
        if url_version.lower() == "v4" or url_version == "4":
            url_version = 4
        elif url_version.lower() == "v5" or url_version == "5":
            url_version = 5
        elif url_version.lower() == "v6" or url_version == "6":
            url_version = 6
        else:
            print('Invalid argument "{}" for {}'.format(url_version, 'URL version'))
            url_version = None

    while not url_version:
        val = input('Please enter the URL version(v4/v5/v6) for downloading products.xml, default is the latest: ') \
              or 'v6'
        if val == 'v4' or val == '4':
            url_version = 4
        elif val == 'v5' or val == '5':
            url_version = 5
        elif val == 'v6' or val == '6':
            url_version = 6
        else:
            print('Invalid URL version: {}'.format(val))

    return url_version


def get_products(allowed_platforms, args):
    if args.auth:
        ADOBE_REQ_HEADERS['Authorization'] = args.auth

    url_version = get_url_version(args.urlVersion)

    products_xml_file = None
    products_xml = None
    if args.cache:
        products_xml_file = os.path.join(args.cache,
                                         'products_' + str(url_version) + '_' + '.'.join(allowed_platforms) + '.xml')
        if os.path.exists(products_xml_file):
            products_xml = load_products_xml(products_xml_file)

    if products_xml is None:
        products_xml = fetch_products_xml(url_version, allowed_platforms, products_xml_file)

    print('Parsing products.xml')
    products, cdn = parse_products_xml(products_xml, url_version, allowed_platforms)

    print('CDN: ' + cdn)
    sap_codes = {}
    for p in products.values():
        if not p['hidden']:
            versions = p['versions']
            last_v = None
            for v in reversed(versions.values()):
                if v['buildGuid'] and v['apPlatform'] in allowed_platforms:
                    last_v = v['productVersion']
            if last_v:
                sap_codes[p['sapCode']] = p['displayName']
    print(str(len(sap_codes)) + ' products found:')

    if args.sapCode and products.get(args.sapCode.upper()) is None:
        print('Provided SAP Code not found in products: ' + args.sapCode)
        args.sapCode = None

    return products, cdn, sap_codes
