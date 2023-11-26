ADOBE_PRODUCTS_PLATFORMS = ['win64', 'win32']


def get_all_platforms():
    return ADOBE_PRODUCTS_PLATFORMS


def get_platforms(target_arch):
    if target_arch is not None:
        if target_arch == 'x86_64' or target_arch == 'x64' or target_arch == 'win64':
            return ADOBE_PRODUCTS_PLATFORMS
        elif target_arch == 'x86' or target_arch == 'win32':
            return ADOBE_PRODUCTS_PLATFORMS[1:2]
        else:
            print('Invalid argument "{}" for {}'.format(target_arch, 'architecture'))
    return ADOBE_PRODUCTS_PLATFORMS


def create_app_skeleton(app_path, icon_path):
    pass
