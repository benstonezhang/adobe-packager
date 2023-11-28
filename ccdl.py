#!/usr/bin/env python3
"""
This is the Adobe Offline Package downloader.

CHANGELOG
(0.3.0)
+ Refine code, split to modules
+ Add cache support

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
import signal

from ccdl.apps import download_adobe_app
from ccdl.net import set_cache_dir, set_header_auth
from ccdl.prod import get_products, get_platforms
from ccdl.utils import question_y

VERSION_STR = '0.3.0'


def show_version():
    ye = int((32 - len(VERSION_STR)) / 2)
    print('=================================')
    print('=    Adobe Package Generator    =')
    print('{} {} {}\n'.format('=' * ye, VERSION_STR, '=' * (31 - len(VERSION_STR) - ye)))


def handler(signum, param):
    print('\nUser break, exit')
    exit(0)


if __name__ == '__main__':
    show_version()

    parser = argparse.ArgumentParser()
    parser.add_argument('-u', '--url_version',
                        help="Get app info from v4/v5/v6 url (eg. v6)", action='store')
    parser.add_argument('-o', '--os',
                        help='Set the target Operation System', action='store')
    parser.add_argument('-a', '--arch',
                        help='Set the architecture to download', action='store')
    parser.add_argument('-l', '--language',
                        help='Language code (eg. en_US) or ALL', action='store')
    parser.add_argument('-s', '--sap_code',
                        help='SAP code for desired product (eg. PHSP)', action='store')
    parser.add_argument('-v', '--app_version',
                        help='Version of desired product (eg. 21.0.3)', action='store')
    parser.add_argument('-z', '--auth',
                        help='Add a bearer_token to to authenticate your account, e.g. downloading Xd', action='store')
    parser.add_argument('-c', '--cache',
                        help="Cache folder for product artifacts", action='store')
    parser.add_argument('-t', '--target',
                        help='Pack application artifacts as installer in target directory', action='store')
    parser.add_argument('-i', '--icon',
                        help='Icon file of installer, else use Creative Cloud icon', action='store')
    parser.add_argument('-q', '--no_repeat_prompt',
                        help="Don't prompt for additional downloads", action='store_true')
    args = parser.parse_args()

    if args.icon and not os.path.isfile(args.icon):
        print('Icon file not found: ' + args.icon)
        exit(1)

    if args.cache:
        set_cache_dir(args.cache)
    if args.auth:
        set_header_auth(args.auth)

    all_platforms, allowed_platforms = get_platforms(args.os, args.arch)
    products, sap_codes = get_products(all_platforms, allowed_platforms, args)
    signal.signal(signal.SIGINT, handler)

    while True:
        download_adobe_app(products, sap_codes, allowed_platforms, args)
        if args.no_repeat_prompt or not question_y('\nCreate another package'):
            break
