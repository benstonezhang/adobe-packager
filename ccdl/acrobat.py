import os
from xml.etree import ElementTree as ET

from ccdl.net import fetch_file, fetch_app_xml
from ccdl.utils import get_download_path


def download_acrobat(app_info, args):
    """Download APRO"""
    manifest = ET.fromstring(fetch_app_xml(app_info['buildGuid']))
    download_url = manifest.find('asset_list/asset/asset_path').text
    dest = get_download_path(args.destination)
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
    fetch_file(download_url, dest, sap_code, version, args.skipExisting, name)

    print('\nInstaller successfully downloaded. Open ' + os.path.join(dest, name) + \
          ' and run Acrobat/Acrobat DC Installer.pkg to install.')
