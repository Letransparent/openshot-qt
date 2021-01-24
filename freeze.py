"""
 @file
 @brief cx_Freeze script to build OpenShot package with dependencies (for Mac and Windows)
 @author Jonathan Thomas <jonathan@openshot.org>

 @section LICENSE

 Copyright (c) 2008-2016 OpenShot Studios, LLC
 (http://www.openshotstudios.com). This file is part of
 OpenShot Video Editor (http://www.openshot.org), an open-source project
 dedicated to delivering high quality video editing and animation solutions
 to the world.

 OpenShot Video Editor is free software: you can redistribute it and/or modify
 it under the terms of the GNU General Public License as published by
 the Free Software Foundation, either version 3 of the License, or
 (at your option) any later version.

 OpenShot Video Editor is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 GNU General Public License for more details.

 You should have received a copy of the GNU General Public License
 along with OpenShot Library.  If not, see <http://www.gnu.org/licenses/>.
 """

# Syntax to build redistributable package:  python3 freeze.py build
#
# Troubleshooting: If you encounter an error while attempting to freeze
# the PyQt5/uic/port_v2, remove the __init__.py in that folder. And if
# you are manually compiling PyQt5 on Windows, remove the -strip line
# from the Makefile. On Mac, just delete the port_v2 folder. Also, you
# might need to remove the QtTest.so from /usr/local/lib/python3.3/site-packages/PyQt5,
# if you get errors while freezing.
#
# Mac Syntax to Build App Bundle:
# 1) python3 freeze.py bdist_mac --qt-menu-nib="/usr/local/Cellar/qt5/5.4.2/plugins/platforms/" --iconfile=installer/openshot.icns --custom-info-plist=installer/Info.plist --bundle-name="OpenShot Video Editor"
# 2) change Contents/Info.plist to use launch-mac.sh as the Executable name
# 3) manually fix rsvg executable:
#    sudo dylibbundler -od -of -b -x ~/apps/rsvg/rsvg-convert -d ./rsvg-libs/ -p @executable_path/rsvg-libs/
# 4) Code sign and create the DMG (disk image)
#    a) cd ~/apps/openshot-qt-git/
#    b) bash installer/build-mac-dmg.sh
#
# Windows Syntax to Build MSI Installer
# NOTE: Python3.5 requires custom build of cx_Freeze (https://github.com/sekrause/cx_Freeze-wheels). Download, python setup.py build, python setup.py install
# 1) python3 freeze.py bdist_msi
# NOTE: Requires a tweak to cx_freeze: http://stackoverflow.com/questions/24195311/how-to-set-shortcut-working-directory-in-cx-freeze-msi-bundle
# 2) Sign MSI with private code signing key (optional)
#  NOTE: Install Windows 10 SDK first
#  signtool sign /v /f OSStudiosSPC.pfx "OpenShot Video Editor-2.0.0-win32.msi"

import inspect
import os
import sys
import fnmatch
from shutil import copytree, rmtree, copy
from cx_Freeze import setup, Executable
import cx_Freeze
from PyQt5.QtCore import QLibraryInfo
import shutil


print (str(cx_Freeze))

# Set '${ARCHLIB}' envvar to override system library path
ARCHLIB = os.getenv('ARCHLIB', "/usr/lib/x86_64-linux-gnu/")
if not ARCHLIB.endswith('/'):
    ARCHLIB += '/'

# Packages to include
python_packages = ["os",
                   "sys",
                   "PyQt5",
                   "openshot",
                   "time",
                   "uuid",
                   "idna",
                   "shutil",
                   "threading",
                   "subprocess",
                   "re",
                   "math",
                   "xml",
                   "logging",
                   "urllib",
                   "requests",
                   "zmq",
                   "webbrowser",
                   "json"
                   ]

# Modules to include
python_modules = ["idna.idnadata"]

# Determine absolute PATH of OpenShot folder
PATH = os.path.dirname(os.path.realpath(__file__))  # Primary openshot folder

# Make a copy of the src tree (temporary for naming reasons only)
if os.path.exists(os.path.join(PATH, "src")):
    print("Copying modules to openshot_qt directory: %s" % os.path.join(PATH, "openshot_qt"))
    # Only make a copy if the SRC directory is present (otherwise ignore this)
    copytree(os.path.join(PATH, "src"), os.path.join(PATH, "openshot_qt"))

    # Make a copy of the launch.py script (to name it more appropriately)
    copy(os.path.join(PATH, "src", "launch.py"), os.path.join(PATH, "openshot_qt", "launch-openshot"))

if os.path.exists(os.path.join(PATH, "openshot_qt")):
    # Append path to system path
    sys.path.append(os.path.join(PATH, "openshot_qt"))
    print("Loaded modules from openshot_qt directory: %s" % os.path.join(PATH, "openshot_qt"))

# Append possible build server paths

sys.path.insert(0, os.path.join(PATH, "build", "install-x86", "lib"))
sys.path.insert(0, os.path.join(PATH, "build", "install-x86", "bin"))

sys.path.insert(0, os.path.join(PATH, "build", "install-x64", "lib"))
sys.path.insert(0, os.path.join(PATH, "build", "install-x64", "bin"))


from classes import info
from classes.logger import log

log.info("Execution path: %s" % os.path.abspath(__file__))


# Find files matching patterns
def find_files(directory, patterns):
    """ Recursively find all files in a folder tree """
    for root, dirs, files in os.walk(directory):
        for basename in files:
            if ".pyc" not in basename and "__pycache__" not in basename:
                for pattern in patterns:
                    if fnmatch.fnmatch(basename, pattern):
                        filename = os.path.join(root, basename)
                        yield filename


# GUI applications require a different base on Windows
iconFile = "openshot-qt"
base = None
src_files = []
external_so_files = []
build_options = {}
build_exe_options = {}
exe_name = info.NAME

# Copy QT translations to local folder (to be packaged)
qt_local_path = os.path.join(PATH, "openshot_qt", "language")
qt_system_path = QLibraryInfo.location(QLibraryInfo.TranslationsPath)
if os.path.exists(qt_system_path):
    # Create local QT translation folder (if needed)
    if not os.path.exists(qt_local_path):
        os.mkdir(qt_local_path)
    # Loop through QT translation files and copy them
    for file in os.listdir(qt_system_path):
        # Copy QT translation files
        if (file.startswith("qt_") or file.startswith("qtbase_")) and file.endswith(".qm"):
            shutil.copyfile(os.path.join(qt_system_path, file), os.path.join(qt_local_path, file))

# Copy git log files into src files (if found)
for project in ["libopenshot-audio", "libopenshot", "openshot-qt"]:
    git_log_path = os.path.join(PATH, "build", "install-x64", "share", "%s.log" % project)
    if os.path.exists(git_log_path):
        src_files.append((git_log_path, "settings/%s.log" % project))
    else:
        git_log_path = os.path.join(PATH, "build", "install-x86", "share", "%s.log" % project)
        if os.path.exists(git_log_path):
            src_files.append((git_log_path, "settings/%s.log" % project))

if sys.platform == "win32":
    # Define alternate terminal-based executable
    extra_exe = {"base": None, "name": exe_name + "-cli.exe"}

    # Standard graphical Win32 launcher
    base = "Win32GUI"
    build_exe_options["include_msvcr"] = True
    exe_name += ".exe"

    # Append Windows ICON file
    iconFile += ".ico"

    # Append some additional files for Windows (this is a debug launcher)
    src_files.append((os.path.join(PATH, "installer", "launch-win.bat"), "launch-win.bat"))

    # Add additional package
    python_packages.append('idna')

    # Manually add zmq dependency (windows does not freeze it correctly)
    import zmq
    python_packages.remove('zmq')
    zmq_path = os.path.normpath(os.path.dirname(inspect.getfile(zmq)))
    for filename in find_files(zmq_path, ["*"]):
        src_files.append((filename, os.path.join("lib", "zmq", os.path.relpath(filename, start=zmq_path))))

    # Append all source files
    src_files.append((os.path.join(PATH, "installer", "qt.conf"), "qt.conf"))
    for filename in find_files("openshot_qt", ["*"]):
        src_files.append((filename, os.path.join(os.path.relpath(filename, start=os.path.join(PATH, "openshot_qt")))))

elif sys.platform == "linux":
    # Find libopenshot.so path (GitLab copies artifacts into local build/install folder)
    libopenshot_path = os.path.join(PATH, "build", "install-x64", "lib")
    if not os.path.exists(libopenshot_path):
        libopenshot_path = os.path.join(PATH, "build", "install-x86", "lib")
    if not os.path.exists(libopenshot_path):
        # Default to user install path
        libopenshot_path = "/usr/local/lib"

    # Find all related SO files
    for filename in find_files(libopenshot_path, ["*openshot*.so*"]):
        if '_' in filename or filename.count(".") == 2:
            external_so_files.append((filename, os.path.relpath(filename, start=libopenshot_path)))

    # Add libresvg (if found)
    resvg_path = "/usr/local/lib/libresvg.so"
    if os.path.exists(resvg_path):
        external_so_files.append((resvg_path, os.path.basename(resvg_path)))

    # Add QtWebEngineProcess (if found)
    web_process_path = ARCHLIB + "qt5/libexec/QtWebEngineProcess"
    if os.path.exists(web_process_path):
        external_so_files.append(
            (web_process_path, os.path.basename(web_process_path)))

    # Add QtWebEngineProcess Resources & Local
    qt5_path = "/usr/share/qt5/"
    for filename in find_files(os.path.join(qt5_path, "resources"), ["*"]):
        external_so_files.append((filename, os.path.relpath(filename, start=qt5_path)))
    for filename in find_files(os.path.join(qt5_path, "translations", "qtwebengine_locales"), ["*"]):
        external_so_files.append((filename, os.path.relpath(filename, start=qt5_path)))

    # Add Qt xcbglintegrations plugin
    xcbgl_path = ARCHLIB + "qt5/"
    for filename in find_files(os.path.join(xcbgl_path, "plugins", "xcbglintegrations"), ["*"]):
        external_so_files.append((filename, os.path.relpath(filename, start=xcbgl_path)))

    # Add libsoftokn3
    nss_path = ARCHLIB + "nss/"
    for filename in find_files(nss_path, ["*"]):
        external_so_files.append((filename, os.path.basename(filename)))

    # Append Linux ICON file
    iconFile += ".svg"
    src_files.append((os.path.join(PATH, "xdg", iconFile), iconFile))

    # Shorten name (since RPM can't have spaces)
    info.PRODUCT_NAME = "openshot-qt"

    # Add custom launcher script for frozen linux version
    src_files.append((os.path.join(PATH, "installer", "launch-linux.sh"), "launch-linux.sh"))

    # Get a list of all openshot.so dependencies (scan these libraries for their dependencies)
    pyqt5_mod_files = []
    from importlib import import_module
    for submod in ['Qt', 'QtSvg', 'QtWidgets', 'QtCore', 'QtGui', 'QtDBus']:
        mod_name  = "PyQt5.{}".format(submod)
        mod = import_module(mod_name)
        pyqt5_mod_files.append(inspect.getfile(mod))
    # Optional additions
    for mod_name in [
            'PyQt5.QtWebEngine',
            'PyQt5.QtWebEngineWidgets',
            'PyQt5.QtWebKit',
            'PyQt5.QtWebKitWidgets',
            ]:
        try:
            mod = import_module(mod_name)
            pyqt5_mod_files.append(inspect.getfile(mod))
        except ImportError as ex:
            log.warning("Skipping {}: {}".format(mod_name, ex))


    lib_list = pyqt5_mod_files
    for lib_name in [
            os.path.join(libopenshot_path, "libopenshot.so"),
            "/usr/local/lib/libresvg.so",
            ARCHLIB + "qt5/plugins/platforms/libqxcb.so"
            ]:
        if os.path.exists(lib_name):
            lib_list.append(lib_name)

    import subprocess
    for library in lib_list:
        p = subprocess.Popen(["ldd", library], stdout=subprocess.PIPE)
        out, err = p.communicate()
        depends = str(out).replace("\\t", "").replace("\\n", "\n").replace("\'", "").split("\n")

        # Loop through each line of output (which outputs dependencies - one per line)
        for line in depends:
            lineparts = line.split("=>")
            libname = lineparts[0].strip()

            if len(lineparts) <= 1:
                continue

            libdetails = lineparts[1].strip()
            libdetailsparts = libdetails.split("(")

            if len(libdetailsparts) <= 1:
                continue

            # Determine if dependency is usr installed (or system installed)
            # Or if the dependency matches one of the following exceptions
            # And ignore paths that start with /lib
            libpath = libdetailsparts[0].strip()
            libpath_file = os.path.basename(libpath)
            if (libpath
                and os.path.exists(libpath)
                and not libpath.startswith("/lib")
                and "libnvidia-glcore.so" not in libpath
                and libpath_file not in [
                    "libstdc++.so.6",
                    "libGL.so.1",
                    "libxcb.so.1",
                    "libX11.so.6",
                    "libX11-xcb.so.1",
                    "libasound.so.2",
                    "libgcc_s.so.1 ",
                    "libICE.so.6",
                    "libp11-kit.so.0",
                    "libSM.so.6",
                    # Next 5 are all part of glib2
                    "libglib-2.0.so.0",
                    "libgobject-2.0.so.0",
                    "libgio-2.0.so.0",
                    "libgmodule-2.0.so.0",
                    "libgthread-2.0.so.0",

                    "libdrm.so.2",
                    "libfreetype.so.6",
                    "libfontconfig.so.1",
                    "libcairo.so.2",
                    "libpango-1.0.so.0",
                    "libpangocairo-1.0.so.0",
                    "libpangoft2-1.0.so.0",
                    "libharfbuzz.so.0",
                    "libthai.so.0",
                    ]
               ) or libpath_file in [
                    "libgcrypt.so.11",
                    "libQt5DBus.so.5",
                    "libpng12.so.0",
                    "libbz2.so.1.0",
                    "libqxcb.so",
                    "libxcb-xinerama.so.0",
                    "libpcre.so.3",
                    "libselinux.so.1",
                    ]:
                external_so_files.append((libpath, libpath_file))
                # Any other lib deps that fail to meet the inclusion
                # criteria above will be silently skipped over

    # Append all source files
    src_files.append((os.path.join(PATH, "installer", "qt.conf"), "qt.conf"))
    for filename in find_files("openshot_qt", ["*"]):
        src_files.append((filename, os.path.join(os.path.relpath(filename, start=os.path.join(PATH, "openshot_qt")))))

elif sys.platform == "darwin":
    # Copy Mac specific files that cx_Freeze misses
   # Add libresvg (if found)
    resvg_path = "/usr/local/lib/librsvg-2.dylib"
    if os.path.exists(resvg_path):
        external_so_files.append((resvg_path, resvg_path.replace("/usr/local/lib/", "")))

    # Copy openshot.py Python bindings
    src_files.append((os.path.join(PATH, "installer", "launch-mac"), "launch-mac"))

    # Append Mac ICON file
    iconFile += ".hqx"
    src_files.append((os.path.join(PATH, "xdg", iconFile), iconFile))

    # Add QtWebEngineProcess (if found)
    qt_install_path = "/usr/local/qt5.15.X/qt5.15/5.15.0/clang_64/"
    qt_webengine_path = os.path.join(qt_install_path, "lib", "QtWebEngineCore.framework", "Versions", "5")
    web_process_path = os.path.join(qt_webengine_path, "Helpers", "QtWebEngineProcess.app", "Contents", "MacOS", "QtWebEngineProcess")
    web_core_path = os.path.join(qt_webengine_path, "QtWebEngineCore")
    external_so_files.append((web_process_path, os.path.basename(web_process_path)))
    external_so_files.append((web_core_path, os.path.basename(web_core_path)))

    # Add QtWebEngineProcess Resources & Local
    for filename in find_files(os.path.join(qt_webengine_path, "Resources"), ["*"]):
        external_so_files.append((filename, os.path.relpath(filename, start=os.path.join(qt_webengine_path, "Resources"))))
    for filename in find_files(os.path.join(qt_webengine_path, "Resources", "qtwebengine_locales"), ["*"]):
        external_so_files.append((filename, os.path.relpath(filename, start=os.path.join(qt_webengine_path, "Resources"))))
    for filename in find_files(os.path.join(qt_install_path, "plugins"), ["*"]):
        relative_filepath = os.path.relpath(filename, start=os.path.join(qt_install_path, "plugins"))
        plugin_name = os.path.dirname(relative_filepath)
        if plugin_name in ["imageformats", "platforms"]:
            external_so_files.append((filename, relative_filepath))

    # Append all source files
    src_files.append((os.path.join(PATH, "installer", "qt.conf"), "qt.conf"))
    for filename in find_files("openshot_qt", ["*"]):
        src_files.append((filename, os.path.join("lib", os.path.relpath(filename, start=os.path.join(PATH, "openshot_qt")))))

    # Exclude gif library which crashes on Mac
    build_exe_options["bin_excludes"] = ["/System/Library/Frameworks/ImageIO.framework/Versions/A/Resources/libGIF.dylib",
                                         "/usr/local/opt/giflib/lib/libgif.dylib"]

# Dependencies are automatically detected, but it might need fine tuning.
build_exe_options["packages"] = python_packages
build_exe_options["include_files"] = src_files + external_so_files
build_exe_options["includes"] = python_modules
build_exe_options["excludes"] = ["distutils", "numpy", "setuptools", "tkinter", "pydoc_data", "pycparser", "pkg_resources"]

# Set options
build_options["build_exe"] = build_exe_options

# Define launcher executable to create
exes = [Executable("openshot_qt/launch.py",
                   base=base,
                   icon=os.path.join(PATH, "xdg", iconFile),
                   shortcutName="%s" % info.PRODUCT_NAME,
                   shortcutDir="ProgramMenuFolder",
                   targetName=exe_name)]

try:
    # Include extra launcher configuration, if defined
    exes.append(Executable("openshot_qt/launch.py",
                base=extra_exe['base'],
                icon=os.path.join(PATH, "xdg", iconFile),
                targetName=extra_exe['name']))
except NameError:
    pass

# Create distutils setup object
setup(name=info.PRODUCT_NAME,
      version=info.VERSION,
      description=info.DESCRIPTION,
      author=info.COMPANY_NAME,
      options=build_options,
      executables=exes)


# Remove temporary folder (if SRC folder present)
if os.path.exists(os.path.join(PATH, "src")):
    rmtree(os.path.join(PATH, "openshot_qt"), True)

# Fix a few things on the frozen folder(s)
if sys.platform == "darwin":
    # Mac issues with frozen folder and *.app folder
    # We need to rewrite many dependency paths and library IDs
    from installer.fix_qt5_rpath import *
    build_path = os.path.join(PATH, "build")
    for frozen_path in os.listdir(build_path):
            if frozen_path.startswith("exe"):
                fix_rpath(os.path.join(build_path, frozen_path))
            elif frozen_path.endswith(".app"):
                fix_rpath(os.path.join(build_path, frozen_path, "Contents", "MacOS"))
                print_min_versions(os.path.join(build_path, frozen_path, "Contents", "MacOS"))
