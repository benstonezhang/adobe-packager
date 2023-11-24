#!/usr/bin/env python3
"""
This is the Adobe Offline Package downloader.

CHANGELOG
(0.2.0)
+ Added v5 & v6 URL (Support Photoshop BETA)
+ Added full support for Adobe Acrobat and partial support for XD (Need bearer_token)
+ Rewrote the code for parsing and downloading dependencies
+ Automatically uppercase SAP code and format language code

(0.1.4-hotfix1)
+ Updated URL (newer downloads work now)

(0.1.4)
+ Added M1 support. Defaults to yes when running on an M1 processor.
+ Added option to make another package after end.
+ Default picks picks newest version if one isn't specified
+ Default picks PhotoShop if nothing is entered, since it was used as the example.
+ Added Platform to version listing.

(0.1.3)
+ Went back to getting old URL.
+ Only show Versions actually Downloadable
+ Shows all Versions available

(0.1.2-hotfix1)
+ updated script to work with new api (newer downloads work now)
+ added workaround for broken installer on big sur
+ made everything even more messy and disgusting
"""
import argparse
import json
import locale
import os
import platform
import signal

import cc_osx
import cc_prod
import cc_utils
import cc_win

VERSION_STR = '0.2.0'


def download_acrobat(app_info, cdn):
    """Download APRO"""
    manifest = cc_prod.fetch_products_xml(cdn + app_info['buildGuid'])
    download_url = manifest.find('asset_list/asset/asset_path').text
    dest = cc_utils.get_download_path(args.destination)
    sap_code = app_info['sapCode']
    version = app_info['productVersion']
    name = '{}_{}_{}.dmg'.format(sap_code, version, app_info['apPlatform'])
    print('')
    print('sapCode: ' + sap_code)
    print('version: ' + version)
    print('installLanguage: ' + 'ALL')
    print('dest: ' + os.path.join(dest, name))

    print('\nDownloading...')

    print('[{}_{}] Selected 1 package'.format(sap_code, version))
    cc_prod.fetch_file(download_url, dest, sap_code, version, args.skipExisting, name)

    print('\nInstaller successfully downloaded. Open ' + os.path.join(dest, name) + \
          ' and run Acrobat/Acrobat DC Installer.pkg to install.')
    return


def show_version():
    ye = int((32 - len(VERSION_STR)) / 2)
    print('=================================')
    print('=    Adobe Package Generator    =')
    print('{} {} {}\n'.format('=' * ye, VERSION_STR, '=' * (31 - len(VERSION_STR) - ye)))


def get_platforms():
    target_arch = args.arch
    if target_arch is not None:
        target_arch = target_arch.lower()
    target_os = args.os
    if target_os is None:
        target_os = platform.system().lower()
    if target_os == 'darwin':
        return cc_osx.get_platforms(target_arch)
    elif target_os == 'windows':
        return cc_win.get_platforms(target_arch)
    print('Unsupported OS platform: ' + target_os)
    exit(1)


def create_app_skeleton(install_app_path):
    target_os = platform.system().lower()
    if target_os == 'darwin':
        cc_osx.create_app_skeleton(install_app_path, args.icon)
    elif target_os == 'windows':
        cc_win.create_app_skeleton(install_app_path, args.icon)


def download_adobe_app(products, cdn, sap_codes, allowed_platforms):
    """Run Main exicution."""
    sap_code = args.sapCode
    if not sap_code:
        for s, d in sap_codes.items():
            print('[{}]{}{}'.format(s, (10 - len(s)) * ' ', d))

        while sap_code is None:
            val = input('Please enter the SAP Code of the desired product (eg. PHSP for Photoshop): ').upper() \
                  or 'PHSP'
            if products.get(val):
                sap_code = val
            else:
                print('{} is not a valid SAP Code. Please use a value from the list above.'.format(val))

    product = products.get(sap_code)
    version_products = product['versions']
    version = None
    if args.version:
        if version_products.get(args.version):
            print('Using provided version: ' + args.version)
            version = args.version
        else:
            print('Provided version not found: ' + args.version)
    print('')

    if not version:
        last_v = None
        for v in reversed(version_products.values()):
            if v['buildGuid'] and v['apPlatform'] in allowed_platforms:
                print('{} Platform: {} - {}'.format(product['displayName'], v['apPlatform'], v['productVersion']))
                last_v = v['productVersion']

        while version is None:
            val = input('Please enter the desired version. Nothing for ' + last_v + ': ') or last_v
            if version_products.get(val):
                version = val
            else:
                print('{} is not a valid version. Please use a value from the list above.'.format(val))
    print('')

    if sap_code == 'APRO':
        download_acrobat(version_products[version], cdn)
        return

    app_locales = version_products[version]['locale']
    install_locales = app_locales.copy()
    install_locales.append('ALL')

    # Detecting Current set default Os language. Fixed.
    default_locale = locale.getlocale()[0]
    if not default_locale:
        default_locale = 'en_US'

    os_lang = None
    if args.osLanguage:
        os_lang = args.osLanguage
    elif default_locale:
        os_lang = default_locale

    if os_lang in app_locales:
        default_lang = os_lang
    else:
        default_lang = 'en_US'

    install_language = None
    if args.installLanguage:
        if args.installLanguage in install_locales:
            print('Using provided language: ' + args.installLanguage)
            install_language = args.installLanguage
        else:
            print('Provided language not available: ' + args.installLanguage)

    if not install_language:
        print('Available languages: {}'.format(', '.join(install_locales)))
        while install_language is None:
            val = input(
                f'Please enter the desired install language, or nothing for [{default_lang}]: ') or default_lang
            if len(val) == 5:
                val = val[0:2].lower() + val[2] + val[3:5].upper()
            elif len(val) == 3:
                val = val.upper()
            if val in install_locales:
                install_language = val
            else:
                print('{} is not available. Please use a value from the list above.'.format(val))
    if os_lang != install_language:
        if install_language != 'ALL':
            while os_lang not in app_locales:
                print('Could not detect your default Language for OS.')
                os_lang = input(
                    f'Please enter the your OS Language, or nothing for [{install_language}]: ') or install_language
                if os_lang not in app_locales:
                    print('{} is not available. Please use a value from the list above.'.format(os_lang))

    dest = cc_utils.get_download_path(args.destination)
    print('')

    prod_info = version_products[version]
    prods_to_download = []
    dependencies = prod_info['dependencies']
    for d in dependencies:
        first_arch = first_guid = build_guid = None
        for p in products[d['sapCode']]['versions']:
            if products[d['sapCode']]['versions'][p]['baseVersion'] == d['version']:
                if not first_guid:
                    first_guid = products[d['sapCode']]['versions'][p]['buildGuid']
                    first_arch = products[d['sapCode']]['versions'][p]['apPlatform']
                if products[d['sapCode']]['versions'][p]['apPlatform'] in allowed_platforms:
                    build_guid = products[d['sapCode']]['versions'][p]['buildGuid']
                    break
        if not build_guid:
            build_guid = first_guid
        prods_to_download.append({'sapCode': d['sapCode'], 'version': d['version'], 'buildGuid': build_guid})

    prods_to_download.insert(
        0,
        {'sapCode': prod_info['sapCode'], 'version': prod_info['productVersion'], 'buildGuid': prod_info['buildGuid']})
    ap_platform = prod_info['apPlatform']
    install_app_name = 'Install {}_{}-{}-{}.app'.format(sap_code, version, install_language, ap_platform)
    install_app_path = os.path.join(dest, install_app_name)
    print('sapCode: ' + sap_code)
    print('version: ' + version)
    print('installLanguage: ' + install_language)
    print('dest: ' + install_app_path)
    print(prods_to_download)

    print('\nCreating {}'.format(install_app_name))

    create_app_skeleton(os.path.join(dest, install_app_path))

    products_dir = os.path.join(install_app_path, 'Contents', 'Resources', 'products')

    print('Preparing...')

    for p in prods_to_download:
        s, v = p['sapCode'], p['version']
        product_dir = os.path.join(products_dir, s)
        app_json_path = os.path.join(product_dir, 'application.json')

        print('[{}_{}] Downloading application.json'.format(s, v))
        app_json = cc_prod.fetch_application_json(p['buildGuid'])
        p['application_json'] = app_json

        print('[{}_{}] Creating folder for product'.format(s, v))
        os.makedirs(product_dir, exist_ok=True)

        print('[{}_{}] Saving application.json'.format(s, v))
        with open(app_json_path, 'w') as file:
            json.dump(app_json, file, separators=(',', ':'))

        print('')

    print('Downloading...')

    for p in prods_to_download:
        s, v = p['sapCode'], p['version']
        app_json = p['application_json']
        product_dir = os.path.join(products_dir, s)

        print('[{}_{}] Parsing available packages'.format(s, v))
        core_pkg_count = 0
        non_core_pkg_count = 0
        packages = app_json['Packages']['Package']
        download_urls = []
        for pkg in packages:
            if pkg.get('Type') and pkg['Type'] == 'core':
                core_pkg_count += 1
                download_urls.append(cdn + pkg['Path'])
            else:
                # TODO: actually parse `Condition` and check it properly (and maybe look for & add support for conditions other than installLanguage)
                if install_language == "ALL":
                    non_core_pkg_count += 1
                    download_urls.append(cdn + pkg['Path'])
                else:
                    if (not pkg.get('Condition')) or install_language in pkg['Condition'] \
                            or os_lang in pkg['Condition']:
                        non_core_pkg_count += 1
                        download_urls.append(cdn + pkg['Path'])
        print('[{}_{}] Selected {} core packages and {} non-core packages'.format(
            s, v, core_pkg_count, non_core_pkg_count))

        for url in download_urls:
            cc_prod.fetch_file(url, product_dir, s, v, args.skipExisting)

    print('Generating driver.xml')

    driver = cc_prod.DRIVER_XML.format(
        name=product['displayName'],
        sapCode=prod_info['sapCode'],
        version=prod_info['productVersion'],
        installPlatform=ap_platform,
        dependencies='\n'.join([cc_prod.DRIVER_XML_DEPENDENCY.format(
            sapCode=d['sapCode'],
            version=d['version']
        ) for d in prod_info['dependencies']]),
        language=install_language
    )

    with open(os.path.join(products_dir, 'driver.xml'), 'w') as f:
        f.write(driver)
        f.close()

    print('\nPackage successfully created. Run {} to install.'.format(install_app_path))
    return


def handler(signum, param):
    print('\nUser break, exit')
    exit(0)


if __name__ == '__main__':
    show_version()

    parser = argparse.ArgumentParser()
    parser.add_argument('--os',
                        help='Operation System', action='store')
    parser.add_argument('-l', '--installLanguage',
                        help='Language code (eg. en_US)', action='store')
    parser.add_argument('-o', '--osLanguage',
                        help='OS Language code (eg. en_US)', action='store')
    parser.add_argument('-s', '--sapCode',
                        help='SAP code for desired product (eg. PHSP)', action='store')
    parser.add_argument('-v', '--version',
                        help='Version of desired product (eg. 21.0.3)', action='store')
    parser.add_argument('-d', '--destination',
                        help='Directory to download installation files to', action='store')
    parser.add_argument('-a', '--arch',
                        help='Set the architecture to download', action='store')
    parser.add_argument('-u', '--urlVersion',
                        help="Get app info from v4/v5/v6 url (eg. v6)", action='store')
    parser.add_argument('-A', '--auth',
                        help='Add a bearer_token to to authenticate your account, e.g. downloading Xd', action='store')
    parser.add_argument('-i', '--icon',
                        help='Icon file of installer app, else use Creative Cloud icon', action='store')
    parser.add_argument('--noRepeatPrompt',
                        help="Don't prompt for additional downloads", action='store_true')
    parser.add_argument('--skipExisting',
                        help="Skip existing files, e.g. resuming failed downloads", action='store_true')
    parser.add_argument('--cache',
                        help="Cache folder for products xml", action='store')
    args = parser.parse_args()

    if args.icon and not os.path.isfile(args.icon):
        print('Icon file not found: ' + args.icon)
        exit(1)

    if args.cache:
        os.makedirs(args.cache, exist_ok=True)

    allowed_platforms = get_platforms()
    products, cdn, sap_codes = cc_prod.get_products(allowed_platforms, args)
    signal.signal(signal.SIGINT, handler)

    while True:
        download_adobe_app(products, cdn, sap_codes, allowed_platforms)
        if args.noRepeatPrompt or not cc_utils.question_y('\nCreate another package'):
            break
