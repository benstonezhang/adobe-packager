import os
import platform
from collections import OrderedDict

from ccdl.mac import get_platforms as get_mac_platforms
from ccdl.net import set_cdn, fetch_products_xml
from ccdl.win import get_platforms as get_win_platforms

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


def parse_products_xml(products_xml, url_version, allowed_platforms):
    """Parsing the XML."""
    prefix = 'channels/' if url_version == 6 else ''
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
        val = input('Please enter the URL version(v4/v5/v6) for downloading products xml, default is the latest: ') \
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


def get_platforms(target_os=None, target_arch=None):
    target_os = (platform.system() if target_os is None else target_os).lower()
    target_arch = (platform.machine() if target_arch is None else target_arch).lower()

    if target_os == 'darwin':
        return get_mac_platforms('any'), get_mac_platforms(target_arch)
    elif target_os == 'windows':
        return get_win_platforms('any'), get_win_platforms(target_arch)
    else:
        print('Unsupported OS platform: ' + target_os)
        exit(1)


def get_products(all_platforms, allowed_platforms, args):
    url_version = get_url_version(args.url_version)
    products_xml = fetch_products_xml(url_version, all_platforms)

    print('Parsing products xml ... ')
    products, cdn = parse_products_xml(products_xml, url_version, allowed_platforms)
    set_cdn(cdn)

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
    print('total ' + str(len(sap_codes)) + ' products found. CDN: ' + cdn)

    if args.sap_code and products.get(args.sap_code.upper()) is None:
        print('Provided SAP Code not found in products: ' + args.sapCode)
        args.sapCode = None

    return products, sap_codes


def save_driver_xml(app_dir, product, prod_info, ap_platform, install_language):
    print('Generating driver.xml')
    driver = DRIVER_XML.format(
        name=product['displayName'],
        sapCode=prod_info['sapCode'],
        version=prod_info['productVersion'],
        installPlatform=ap_platform,
        dependencies='\n'.join([DRIVER_XML_DEPENDENCY.format(sapCode=d['sapCode'], version=d['version'])
                                for d in prod_info['dependencies']]),
        language=install_language)
    with open(os.path.join(app_dir, 'driver.xml'), 'w') as f:
        f.write(driver)
