# Miro - an RSS based video player application
# Copyright (C) 2005, 2006, 2007, 2008, 2009, 2010, 2011
# Participatory Culture Foundation
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301 USA
#
# In addition, as a special exception, the copyright holders give
# permission to link the code of portions of this program with the OpenSSL
# library.
#
# You must obey the GNU General Public License in all respects for all of
# the code used other than OpenSSL. If you modify file(s) with this
# exception, you may extend this exception to your version of the file(s),
# but you are not obligated to do so. If you do not wish to do so, delete
# this exception statement from your version. If you delete this exception
# statement from all source files in the program, then also delete it here.

"""Contains the locations of special windows folders like "My
Documents".
"""

import ctypes
import os
# from miro import u3info

GetShortPathName = ctypes.windll.kernel32.GetShortPathNameW

_special_folder_CSIDLs = {
    "Fonts": 0x0014,
    "AppData": 0x001a,
    "My Music": 0x000d,
    "My Pictures": 0x0027,
    "My Videos": 0x000e,
    "My Documents": 0x0005,
    "Desktop": 0x0000,
    "Common AppData": 0x0023,
    "System": 0x0025
}

def get_short_path_name(name):
    """Given a path, returns the shortened path name.
    """
    buf = ctypes.c_wchar_p(name)
    buf2 = ctypes.create_unicode_buffer(1024)

    if GetShortPathName(buf, buf2, 1024):
        return buf2.value
    else:
        return buf.value

def get_special_folder(name):
    """Get the location of a special folder.  name should be one of
    the following: 'AppData', 'My Music', 'My Pictures', 'My Videos',
    'My Documents', 'Desktop'.

    The path to the folder will be returned, or None if the lookup
    fails
    """
    try:
        csidl = _special_folder_CSIDLs[name]
    except KeyError:
        # FIXME - this will silently fail if the dev did a typo
        # for the path name.  e.g. My Musc
        return None

    buf = ctypes.create_unicode_buffer(260)
    SHGetSpecialFolderPath = ctypes.windll.shell32.SHGetSpecialFolderPathW
    if SHGetSpecialFolderPath(None, buf, csidl, False):
        return buf.value
    else:
        return None

common_app_data_directory = get_special_folder("Common AppData")
app_data_directory = get_special_folder("AppData")

base_movies_directory = get_special_folder('My Videos')
non_video_directory = get_special_folder('Desktop')
# The "My Videos" folder isn't guaranteed to be listed. If it isn't
# there, we do this hack.
if base_movies_directory is None:
    base_movies_directory = os.path.join(
        get_special_folder('My Documents'), 'My Videos')
