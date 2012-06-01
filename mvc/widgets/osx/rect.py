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

""".rect -- Simple Rectangle class."""

from Foundation import NSMakeRect, NSRectFromString

class Rect(object):
    @classmethod
    def from_string(cls, rect_string):
        if rect_string.startswith('{{'):
            return NSRectWrapper(NSRectFromString(rect_string))
        else:
            try:
                items = [int(i) for i in rect_string.split(',')]
                return Rect(*items)
            except:
                return None

    def __init__(self, x, y, width, height):
        self.nsrect = NSMakeRect(x, y, width, height)

    def get_x(self):
        return self.nsrect.origin.x
    def set_x(self, x):
        self.nsrect.origin.x = x
    x = property(get_x, set_x)

    def get_y(self):
        return self.nsrect.origin.y
    def set_y(self, y):
        self.nsrect.origin.x = y
    y = property(get_y, set_y)

    def get_width(self):
        return self.nsrect.size.width
    def set_width(self, width):
        self.nsrect.size.width = width
    width = property(get_width, set_width)

    def get_height(self):
        return self.nsrect.size.height
    def set_height(self, height):
        self.nsrect.size.height = height
    height = property(get_height, set_height)
    
    def __str__(self):
        return "%d,%d,%d,%d" % (self.nsrect.origin.x, self.nsrect.origin.y, self.nsrect.size.width, self.nsrect.size.height)

class NSRectWrapper(Rect):
    def __init__(self, nsrect):
        self.nsrect = nsrect
