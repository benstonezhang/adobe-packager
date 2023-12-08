import json
import locale
import os
import platform

from ccdl.acrobat import download_acrobat
from ccdl.mac import create_mac_installer as create_mac_installer
from ccdl.net import fetch_application_json, fetch_file
from ccdl.prod import save_driver_xml
from ccdl.utils import get_download_path
from ccdl.win import create_win_installer as create_win_installer


def create_installer(app_name, dest, target_os, use_gui, icon_path):
    target_os = (platform.system() if target_os is None else target_os).lower()
    if target_os == 'darwin':
        return create_mac_installer(app_name, dest, use_gui, icon_path)
    elif target_os == 'windows':
        return create_win_installer(app_name, dest, use_gui, icon_path)
    else:
        print('Unsupported target OS platform: ' + target_os)
        exit(1)


def download_adobe_app(products, sap_codes, allowed_platforms, args):
    """Run main execution"""
    sap_code = args.sap_code
    if not sap_code:
        print('')
        for s, d in sap_codes.items():
            print('  [{}]{}{}'.format(s, (10 - len(s)) * ' ', d))
        print('')

        while sap_code is None:
            val = input('Please enter the SAP Code of the desired product (eg. PHSP for Photoshop): ').upper() \
                  or 'PHSP'
            if products.get(val) and sap_codes.get(val):
                sap_code = val
            else:
                print('{} is not a valid SAP Code. Please use a value from the list above.'.format(val))

    product = products.get(sap_code)
    version_products = product['versions']
    version = None
    if args.app_version:
        if version_products.get(args.app_version):
            print('Using provided version: ' + args.app_version)
            version = args.app_version
        else:
            print('Provided version not found: ' + args.app_version)

    if not version:
        last_v = None
        for v in reversed(version_products.values()):
            if v['buildGuid'] and v['apPlatform'] in allowed_platforms:
                print('{} Platform: {} - {}'.format(product['displayName'], v['apPlatform'], v['productVersion']))
                last_v = v['productVersion']
        if last_v is None:
            print('')
            return

        while version is None:
            val = input('Please enter the desired version. Nothing for ' + last_v + ': ') or last_v
            if version_products.get(val):
                version = val
            else:
                print('{} is not a valid version. Please use a value from the list above.'.format(val))
    print('')

    if sap_code == 'APRO':
        download_acrobat(version_products[version], args)
        return

    app_locales = version_products[version]['locale']
    all_locales = app_locales.copy()
    all_locales.append('ALL')
    print('Available languages: {}'.format(', '.join(all_locales)))

    # Detecting current OS language.
    os_lang = locale.getlocale()[0]
    if not os_lang:
        os_lang = 'en_US'

    app_lang = args.language
    if app_lang in all_locales:
        print('Using provided language: ' + args.language)
    else:
        if app_lang is not None:
            print('Provided language not available: ' + args.language)
        app_lang = None

    while app_lang is None:
        val = input(f'Please enter the desired install language, or nothing for [{os_lang}]: ') or os_lang
        if len(val) == 5:
            val = val[0:2].lower() + val[2] + val[3:5].upper()
        elif len(val) == 3:
            val = val.upper()
        if val in all_locales:
            app_lang = val
        else:
            print('{} is not available. Please use a value from the list above.'.format(val))

    dest = get_download_path(args.target)

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
    print('sapCode: ' + sap_code)
    print('version: ' + version)
    print('install_language: ' + app_lang)
    print(prods_to_download)
    if args.target:
        install_app_name = 'Install_{}_{}-{}-{}'.format(sap_code, version, app_lang, ap_platform)
        print('\nCreating {}'.format(install_app_name))
        app_base_path, install_app_path, products_dir = create_installer(
            install_app_name, dest, args.os, args.gui, args.icon)
        print('destination: ' + install_app_path)

    print('Preparing...')
    for p in prods_to_download:
        s, v = p['sapCode'], p['version']

        print('[{}_{}] Retrieve application.json, guid={}'.format(s, v, p['buildGuid']))
        p['application_json'] = fetch_application_json(p['buildGuid'])

        if args.target is None:
            continue

        print('[{}_{}] Creating folder for product'.format(s, v))
        product_dir = os.path.join(products_dir, s)
        app_json_path = os.path.join(product_dir, 'application.json')
        os.makedirs(product_dir, exist_ok=True)

        print('[{}_{}] Saving application.json'.format(s, v))
        with open(app_json_path, 'w') as file:
            json.dump(p['application_json'], file, separators=(',', ':'))

    print('Downloading...')

    for p in prods_to_download:
        s, v = p['sapCode'], p['version']
        app_json = p['application_json']

        print('[{}_{}] Parsing available packages'.format(s, v))
        core_pkg_count = 0
        non_core_pkg_count = 0
        packages = app_json['Packages']['Package']
        download_paths = []
        for pkg in packages:
            if pkg.get('Type') and pkg['Type'] == 'core':
                core_pkg_count += 1
                download_paths.append(pkg['Path'])
            else:
                if app_lang == "ALL":
                    non_core_pkg_count += 1
                    download_paths.append(pkg['Path'])
                elif (not pkg.get('Condition')) or app_lang in pkg['Condition']:
                    non_core_pkg_count += 1
                    download_paths.append(pkg['Path'])
        print('[{}_{}] Selected {} core packages and {} non-core packages'.format(
            s, v, core_pkg_count, non_core_pkg_count))

        product_dir = os.path.join(products_dir, s) if args.target else None
        for path in download_paths:
            fetch_file(path, product_dir, s, v)

    print('Package retrieve finished.')

    if args.target:
        save_driver_xml(app_base_path, products_dir, product, prod_info, ap_platform, app_lang)
        print('\nPackage successfully created. Run {} to install.'.format(install_app_path))
