import os

from ccdl.utils import DRIVER_XML_NAME

APPLICATIONS_PATH = 'C:\\Program Files\\Adobe'
ADOBE_HDBOX_SETUP = 'C:\\Program Files\\Common Files\\Adobe\\Adobe Desktop Common\\HDBox\\Setup.exe'
SCRIPT_NAME = 'install.cmd'
INSTALLER_SCRIPT = '''NET SESSION >nul 2>&1
IF %ERRORLEVEL% EQU 0 (
    cd /D "%~dp0"
    "{hdbox_setup}" --install=1 --driverXML={driver_xml_name}
    ECHO Done
) ELSE (
    ECHO Need Administrator privileges to run installer
    powershell -command Start-Process -FilePath cmd.exe -ArgumentList '/C "%~dp0install.cmd"' -Verb RunAs
)
'''.format(hdbox_setup=ADOBE_HDBOX_SETUP, driver_xml_name=DRIVER_XML_NAME, script_name=SCRIPT_NAME)


def get_platforms(target_arch=None):
    if not target_arch:
        return ['win64', 'win32']
    elif target_arch == 'x86_64' or target_arch == 'x64':
        return ['win64', 'win32']
    elif target_arch == 'x86':
        return ['win32']
    else:
        print('Invalid argument "{}" for {}'.format(target_arch, 'architecture'))


def create_win_installer(app_name, dest, use_gui=False, icon_path=None):
    if use_gui:
        print('GUI for installer on windows not supported.')
        exit(1)
    else:
        app_path = os.path.join(dest, app_name)
        os.makedirs(app_path, exist_ok=True)
        script = os.path.join(app_path, SCRIPT_NAME)
        with open(script, 'w') as f:
            f.write(INSTALLER_SCRIPT)
        return APPLICATIONS_PATH, app_path, app_path
