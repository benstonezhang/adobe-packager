import os
import shutil
import stat
from subprocess import PIPE, Popen

from ccdl.utils import DRIVER_XML_NAME

ADOBE_HDBOX_SETUP = '/Library/Application Support/Adobe/Adobe Desktop Common/HDBox/Setup'
ADOBE_CC_MAC_ICON_PATH = '/Library/Application Support/Adobe/Adobe Desktop Common/HDBox/Install.app/Contents/' + \
                         'Resources/CreativeCloudInstaller.icns'
MAC_VOLUME_ICON_PATH = '/System/Library/CoreServices/CoreTypes.bundle/Contents/Resources/CDAudioVolumeIcon.icns'
APPLICATIONS_PATH = '/Applications'

INSTALL_APP_APPLE_SCRIPT = '''const app = Application.currentApplication()
app.includeStandardAdditions = true

ObjC.import('Cocoa')
ObjC.import('stdio')
ObjC.import('stdlib')

ObjC.registerSubclass({
  name: 'HandleDataAction',
  methods: {
      'outData:': {
          types: ['void', ['id']],
          implementation: function(sender) {
              const data = sender.object.availableData
              if (data.length !== '0') {
                  const output = $.NSString.alloc.initWithDataEncoding(data, $.NSUTF8StringEncoding).js
                  const res = parseOutput(output)
                  if (res) {
                      switch (res.type) {
                          case 'progress':
                              Progress.additionalDescription = `Progress: ${res.data}%`
                              Progress.completedUnitCount = res.data
                              break
                          case 'exit':
                              if (res.data === 0) {
                                  $.puts(JSON.stringify({ title: 'Installation succeeded' }))
                              } else {
                                  $.puts(JSON.stringify({ title: `Failed with error code ${res.data}` }))
                              }
                              $.exit(0)
                              break
                      }
                  }
                  sender.object.waitForDataInBackgroundAndNotify
              } else {
                  $.NSNotificationCenter.defaultCenter.removeObserver(this)
              }
          }
      }
  }
})

function parseOutput(output) {
  let matches

  matches = output.match(/Progress: ([0-9]{1,3})%/)
  if (matches) {
      return {
          type: 'progress',
          data: parseInt(matches[1], 10)
      }
  }

  matches = output.match(/Exit Code: ([0-9]{1,3})/)
  if (matches) {
      return {
          type: 'exit',
          data: parseInt(matches[1], 10)
      }
  }

  return false
}

function shellescape(a) {
  var ret = [];

  a.forEach(function(s) {
    if (/[^A-Za-z0-9_\\/:=-]/.test(s)) {
      s = "'"+s.replace(/'/g,"'\\\\''")+"'";
      s = s.replace(/^(?:'')+/g, '') // unduplicate single-quote at the beginning
        .replace(/\\\\\'''/g, "\\\\'" ); // remove non-escaped single-quote if there are enclosed between 2 escaped
    }
    ret.push(s);
  });

  return ret.join(' ');
}


function run() {
  const appPath = app.pathTo(this).toString()
  const driverPath = appPath + '/Contents/Resources/products/driver.xml'
  const hyperDrivePath = '/Library/Application Support/Adobe/Adobe Desktop Common/HDBox/Setup'

  // The JXA Objective-C bridge is completely broken in Big Sur
  if (!$.NSProcessInfo && parseFloat(app.doShellScript('sw_vers -productVersion')) >= 11.0) {
      app.displayAlert('GUI unavailable in Big Sur', {
          message: 'JXA is currently broken in Big Sur.\\nInstall in Terminal instead?',
          buttons: ['Cancel', 'Install in Terminal'],
          defaultButton: 'Install in Terminal',
          cancelButton: 'Cancel'
      })
      const cmd = shellescape([ 'sudo', hyperDrivePath, '--install=1', '--driverXML=' + driverPath ])
      app.displayDialog('Run this command in Terminal to install (press \\'OK\\' to copy to clipboard)', { defaultAnswer: cmd })
      app.setTheClipboardTo(cmd)
      return
  }

  let args = $.NSProcessInfo.processInfo.arguments
  const argv = []
  const argc = args.count
  for (var i = 0; i < argc; i++) {
      argv.push(ObjC.unwrap(args.objectAtIndex(i)))
  }
  delete args

  const installFlag = argv.indexOf('-y') > -1

  if (!installFlag) {
      app.displayAlert('Adobe Package Installer', {
          message: 'Start installation now?',
          buttons: ['Cancel', 'Install'],
          defaultButton: 'Install',
          cancelButton: 'Cancel'
      })

      const output = app.doShellScript(`"${appPath}/Contents/MacOS/applet" -y`, { administratorPrivileges: true })
      const alert = JSON.parse(output)
      alert.params ? app.displayAlert(alert.title, alert.params) : app.displayAlert(alert.title)
      return
  }

  const stdout = $.NSPipe.pipe
  const task = $.NSTask.alloc.init

  task.executableURL = $.NSURL.alloc.initFileURLWithPath(hyperDrivePath)
  task.arguments = $(['--install=1', '--driverXML=' + driverPath])
  task.standardOutput = stdout

  const dataAction = $.HandleDataAction.alloc.init
  $.NSNotificationCenter.defaultCenter.addObserverSelectorNameObject(dataAction, 'outData:', $.NSFileHandleDataAvailableNotification, $.initialOutputFile)

  stdout.fileHandleForReading.waitForDataInBackgroundAndNotify

  let err = $.NSError.alloc.initWithDomainCodeUserInfo('', 0, '')
  const ret = task.launchAndReturnError(err)
  if (!ret) {
      $.puts(JSON.stringify({
          title: 'Error',
          params: {
              message: 'Failed to launch task: ' + err.localizedDescription.UTF8String
          }
      }))
      $.exit(0)
  }

  Progress.description =  "Installing packages..."
  Progress.additionalDescription = "Preparing..."
  Progress.totalUnitCount = 100

  task.waitUntilExit
}
'''

SCRIPT_NAME = 'install.sh'
INSTALLER_SCRIPT = '''#!/bin/sh
echo 'Please input root password for sudo to install'
cwd=$(dirname "$0")
sudo '{hdbox_setup}' --install=1 --driverXML="$cwd/{driver_xml_name}"
echo Done
'''.format(hdbox_setup=ADOBE_HDBOX_SETUP, driver_xml_name=DRIVER_XML_NAME)


def get_platforms(target_arch=None):
    if not target_arch:
        return ['macuniversal', 'macarm64', 'osx10-64', 'osx10']
    elif target_arch == 'universal':
        return ['macuniversal']
    elif target_arch == 'arm64' or target_arch == 'arm':
        print('Note: If the Adobe program is NOT listed here, there is no native M1 version. Use the non native '
              'version with Rosetta 2 until an M1 version is available.')
        return ['macuniversal', 'macarm64']
    elif target_arch == 'x86_64' or target_arch == 'x64':
        return ['macuniversal', 'osx10-64', 'osx10']
    else:
        print('Invalid argument "{}" for {}'.format(target_arch, 'architecture'))


def create_mac_installer(app_name, dest, use_gui=False, icon_path=None):
    if use_gui:
        app_path = os.path.join(dest, app_name + '.app')
        with Popen(['/usr/bin/osacompile', '-l', 'JavaScript', '-o', app_path], stdin=PIPE) as p:
            p.communicate(INSTALL_APP_APPLE_SCRIPT.encode('utf-8'))
        if not icon_path:
            icon_path = ADOBE_CC_MAC_ICON_PATH if os.path.isfile(ADOBE_CC_MAC_ICON_PATH) else MAC_VOLUME_ICON_PATH
        shutil.copyfile(icon_path, os.path.join(app_path, 'Contents', 'Resources', 'applet.icns'))
        return APPLICATIONS_PATH, app_path, os.path.join(app_path, 'Contents', 'Resources', 'products')
    else:
        app_path = os.path.join(dest, app_name)
        os.makedirs(app_path, exist_ok=True)
        script = os.path.join(app_path, SCRIPT_NAME)
        with open(script, 'w') as f:
            f.write(INSTALLER_SCRIPT)
        os.chmod(script, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
        return APPLICATIONS_PATH, app_path, app_path
