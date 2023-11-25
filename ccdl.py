#!/usr/bin/env python3
"""
This is the Adobe Offline Package downloader.

CHANGELOG
(0.3.0)
+ Refine code, split to modules
* Add cache support

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
import os
import platform
import signal

from ccdl.apps import download_adobe_app
from ccdl.mac import get_platforms as get_mac_platforms
from ccdl.net import set_cache_dir
from ccdl.prod import get_products
from ccdl.utils import question_y
from ccdl.win import get_platforms as get_win_platforms

VERSION_STR = '0.2.0'


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
        return get_mac_platforms(target_arch)
    elif target_os == 'windows':
        return get_win_platforms(target_arch)

    print('Unsupported OS platform: ' + target_os)
    exit(1)


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
    parser.add_argument('--skipCreateApp',
                        help="Skip create installer app", action='store_true')
    args = parser.parse_args()

    if args.icon and not os.path.isfile(args.icon):
        print('Icon file not found: ' + args.icon)
        exit(1)

    if args.cache:
        set_cache_dir(args.cache)

    allowed_platforms = get_platforms()
    products, sap_codes = get_products(allowed_platforms, args)
    signal.signal(signal.SIGINT, handler)

    while True:
        download_adobe_app(products, sap_codes, allowed_platforms, args)
        if args.noRepeatPrompt or not question_y('\nCreate another package'):
            break
