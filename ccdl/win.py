def get_platforms(target_arch):
    if target_arch == 'any':
        return ['win64', 'win32']
    elif target_arch == 'x86_64' or target_arch == 'x64':
        return ['win64', 'win32']
    elif target_arch == 'x86':
        return ['win32']
    else:
        print('Invalid argument "{}" for {}'.format(target_arch, 'architecture'))


def create_installer(app_path, icon_path):
    print('Not implement')
