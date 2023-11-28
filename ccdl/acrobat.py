import os

from ccdl.net import fetch_file, fetch_app_xml
from ccdl.utils import get_download_path


def download_acrobat(app_info, args):
    """Download APRO"""
    manifest = fetch_app_xml(app_info['buildGuid'])
    download_url = manifest.find('asset_list/asset/asset_path').text

    sap_code = app_info['sapCode']
    version = app_info['productVersion']
    name = '{}_{}_{}.dmg'.format(sap_code, version, app_info['apPlatform'])

    print('\nsapCode: ' + sap_code)
    print('version: ' + version)
    print('installLanguage: ' + 'ALL')
    app_path = get_download_path(args.target)
    if app_path:
        print('destination: ' + os.path.join(app_path, name))

    fetch_file(download_url, app_path, sap_code, version, name)
    if app_path:
        print('Installer successfully retrieved. Open ' + os.path.join(app_path, name) + \
              ' and run installer application.')
