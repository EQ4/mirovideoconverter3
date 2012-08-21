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

"""menus.py -- Menu handling code."""

import logging
import struct

from objc import nil, NO, YES
import AppKit
from AppKit import *
from Foundation import *

from mvc.widgets import signals
from mvc.widgets import keyboard
# import these names directly into our namespace for easy access
from mvc.widgets.keyboard import Shortcut, MOD

# XXX hacks
def _(text):
    return text

MODIFIERS_MAP = {
    keyboard.MOD:   NSCommandKeyMask,
    keyboard.CMD:   NSCommandKeyMask,
    keyboard.SHIFT: NSShiftKeyMask,
    keyboard.CTRL:  NSControlKeyMask,
    keyboard.ALT:   NSAlternateKeyMask
}

if isinstance(NSBackspaceCharacter, int):
    backspace = NSBackspaceCharacter
else:
    backspace = ord(NSBackspaceCharacter)
    
KEYS_MAP = {
    keyboard.SPACE: " ",
    keyboard.ENTER: "\r",
    keyboard.BKSPACE: struct.pack("H", backspace),
    keyboard.DELETE: NSDeleteFunctionKey,
    keyboard.RIGHT_ARROW: NSRightArrowFunctionKey,
    keyboard.LEFT_ARROW: NSLeftArrowFunctionKey,
    keyboard.UP_ARROW: NSUpArrowFunctionKey,
    keyboard.DOWN_ARROW: NSDownArrowFunctionKey,
    '.': '.',
    ',': ','
}
# add function keys
for i in range(1, 13):
    portable_key = getattr(keyboard, "F%s" % i)
    osx_key = getattr(AppKit, "NSF%sFunctionKey" % i)
    KEYS_MAP[portable_key] = osx_key

REVERSE_MODIFIERS_MAP = dict((i[1], i[0]) for i in MODIFIERS_MAP.items())
REVERSE_KEYS_MAP = dict((i[1], i[0]) for i in KEYS_MAP.items() 
        if i[0] != keyboard.BKSPACE)
REVERSE_KEYS_MAP[u'\x7f'] = keyboard.BKSPACE
REVERSE_KEYS_MAP[u'\x1b'] = keyboard.ESCAPE

def make_modifier_mask(shortcut):
    mask = 0
    for modifier in shortcut.modifiers:
        mask |= MODIFIERS_MAP[modifier]
    return mask

VIEW_ITEM_MAP = {}

def _remove_mnemonic(label):
    """Remove the underscore used by GTK for mnemonics.
    
    We totally ignore them on OSX, since they are now deprecated.
    """
    return label.replace("_", "")

def handle_menu_activate(ns_menu_item):
    """Handle a menu item being activated.

    This gets called by our application delegate.
    """

    menu_item = ns_menu_item.representedObject()
    menu_item.emit("activate")
    menubar = menu_item._find_menubar()
    if menubar is not None:
        menubar.emit("activate", menu_item.name)

class MenuItemBase(signals.SignalEmitter):
    """Base class for MenuItem and Separator"""
    def __init__(self):
        signals.SignalEmitter.__init__(self)
        self.name = None
        self.parent = None

    def show(self):
        self._menu_item.setHidden_(False)

    def hide(self):
        self._menu_item.setHidden_(True)

    def enable(self):
        self._menu_item.setEnabled_(True)

    def disable(self):
        self._menu_item.setEnabled_(False)

    def remove_from_parent(self):
        """Remove this menu item from it's parent Menu."""
        if self.parent is not None:
            self.parent.remove(self)

class MenuItem(MenuItemBase):
    """See the GTK version of this method for the current docstring."""

    # map Miro action names to standard OSX actions.
    _STD_ACTION_MAP = {
        "HideMiro":         (NSApp(), 'hide:'),
        "HideOthers":       (NSApp(), 'hideOtherApplications:'),
        "ShowAll":          (NSApp(), 'unhideAllApplications:'),
        "Cut":              (nil,     'cut:'),
        "Copy":             (nil,     'copy:'),
        "Paste":            (nil,     'paste:'),
        "Delete":           (nil,     'delete:'),
        "SelectAll":        (nil,     'selectAll:'),
        "Zoom":             (nil,     'performZoom:'),
        "Minimize":         (nil,     'performMiniaturize:'),
        "BringAllToFront":  (nil,     'arrangeInFront:'),
        "CloseWindow":      (nil,     'performClose:'),
    }

    def __init__(self, label, name, shortcut=None):
        MenuItemBase.__init__(self)
        self.name = name
        self._menu_item = self._make_menu_item(label)
        self.create_signal('activate')
        self._setup_shortcut(shortcut)

    def _make_menu_item(self, label):
        menu_item = NSMenuItem.alloc().init()
        menu_item.setTitle_(_remove_mnemonic(label))
        # we set ourselves as the represented object for the menu item so we
        # can easily translate one to the other
        menu_item.setRepresentedObject_(self)
        if self.name in self._STD_ACTION_MAP:
            menu_item.setTarget_(self._STD_ACTION_MAP[self.name][0])
            menu_item.setAction_(self._STD_ACTION_MAP[self.name][1])
        else:
            menu_item.setTarget_(NSApp().delegate())
            menu_item.setAction_('handleMenuActivate:')
        return menu_item

    def _setup_shortcut(self, shortcut):
        if shortcut is None:
            key = ''
            modifier_mask = 0
        elif isinstance(shortcut.shortcut, str):
            key = shortcut.shortcut
            modifier_mask = make_modifier_mask(shortcut)
        elif shortcut.shortcut in KEYS_MAP:
            key = KEYS_MAP[shortcut.shortcut]
            modifier_mask = make_modifier_mask(shortcut)
        else:
            logging.warn("Don't know how to handle shortcut: %s", shortcut)
            return
        self._menu_item.setKeyEquivalent_(key)
        self._menu_item.setKeyEquivalentModifierMask_(modifier_mask)

    def _change_shortcut(self, shortcut):
        self._setup_shortcut(shortcut)

    def set_label(self, new_label):
        self._menu_item.setTitle_(new_label)

    def get_label(self):
        self._menu_item.title()

    def _find_menubar(self):
        """Remove this menu item from it's parent Menu."""
        menu_item = self
        while menu_item.parent is not None:
            menu_item = menu_item.parent
        if isinstance(menu_item, MenuBar):
            return menu_item
        else:
            return None

class CheckMenuItem(MenuItem):
    """See the GTK version of this method for the current docstring."""
    def set_state(self, active):
        if active is None:
            state = NSMixedState
        elif active:
            state = NSOnState
        else:
            state = NSOffState
        self._menu_item.setState_(state)

    def get_state(self):
        return self._menu_item.state() == NSOnState

    def do_activate(self):
        if self._menu_item.state() == NSOffState:
            self._menu_item.setState_(NSOnState)
        else:
            self._menu_item.setState_(NSOffState)

class RadioMenuItem(CheckMenuItem):
    """See the GTK version of this method for the current docstring."""
    def __init__(self, label, name, shortcut=None):
        CheckMenuItem.__init__(self, label, name, shortcut)
        # The leader of a radio group stores the list of all items in the
        # group
        self.group_leader = None
        self.others_in_group = set()

    def set_group(self, group_item):
        if self.group_leader is not None:
            raise ValueError("%s is already in a group" % self)
        if group_item.group_leader is None:
            group_leader = group_item
        else:
            group_leader = group_item.group_leader
        if group_leader.group_leader is not None:
            raise AssertionError("group_leader structure is wrong")
        self.group_leader = group_leader
        group_leader.others_in_group.add(self)

    def remove_from_group(self):
        """Remove this RadioMenuItem from its current group."""
        if self.group_leader is not None:
            # we have a group leader, remove ourself from their list.
            # Note that this code will work even if we're the last item in
            # others_in_group.
            self.group_leader.others_in_group.remove(self)
            self.group_leader = None
        elif len(self.others_in_group) > 1:
            # we're the group leader, hand off the leader to a different item
            first_item = iter(self.others_in_group).next()
            for other in self.others_in_group:
                if other is first_item:
                    other.others_in_group = self.others_in_group
                    other.others_in_group.remove(first_item)
                    other.group_leader = None
                else:
                    other.group_leader = first_item
            self.others_in_group = set()
        elif len(self.others_in_group) == 1:
            # we're the group leader, but there's only 1 other item.  unset
            # everything.
            for other in self.others_in_group:
                other.group_leader = None
            self.others_in_group = set()

    def _items_in_group(self):
        if self.group_leader is not None: # we have a group leader
            yield self.group_leader
            for other in self.group_leader.others_in_group:
                yield other
        elif self.others_in_group: # we're the group leader
            yield self
            for other in self.others_in_group:
                yield other
        else: # we don't have a group set
            yield self

    def do_activate(self):
        for item in self._items_in_group():
            if item is not self:
                item.set_state(False)
        CheckMenuItem.do_activate(self)

class Separator(MenuItemBase):
    """See the GTK version of this method for the current docstring."""
    def __init__(self):
        MenuItemBase.__init__(self)
        self._menu_item = NSMenuItem.separatorItem()

class MenuShell(signals.SignalEmitter):
    def __init__(self, nsmenu):
        signals.SignalEmitter.__init__(self)
        self._menu = nsmenu
        self.children = []
        self.parent = None

    def append(self, menu_item):
        """Add a menu item to the end of this menu."""
        self.children.append(menu_item)
        self._menu.addItem_(menu_item._menu_item)
        menu_item.parent = self

    def insert(self, index, menu_item):
        """Insert a menu item in the middle of this menu."""
        self.children.insert(index, menu_item)
        self._menu.insertItem_atIndex_(menu_item._menu_item, index)
        menu_item.parent = self

    def index(self, name):
        """Find the position of a child menu item."""
        for i, menu_item in enumerate(self.children):
            if menu_item.name == name:
                return i
        return -1

    def remove(self, menu_item):
        """Remove a child menu item.

        :raises ValueError: menu_item is not a child of this menu
        """
        self.children.remove(menu_item)
        self._menu.removeItem_(menu_item._menu_item)
        menu_item.parent = None

    def get_children(self):
        """Get the child menu items in order."""
        return list(self.children)

    def find(self, name):
        """Search for a menu or menu item

        This method recursively searches the entire menu structure for a Menu
        or MenuItem object with a given name.

        :raises KeyError: name not found
        """
        found = self._find(name)
        if found is None:
            raise KeyError(name)
        else:
            return found

    def _find(self, name):
        """Low-level helper-method for find().

        :returns: found menu item or None.
        """
        for menu_item in self.get_children():
            if menu_item.name == name:
                return menu_item
            if isinstance(menu_item, Menu):
                submenu_find = menu_item._find(name)
                if submenu_find is not None:
                    return submenu_find
        return None

class Menu(MenuShell):
    """See the GTK version of this method for the current docstring."""
    def __init__(self, label, name, child_items=None):
        MenuShell.__init__(self, NSMenu.alloc().init())
        self._menu.setTitle_(_remove_mnemonic(label))
        # we will enable/disable menu items manually
        self._menu.setAutoenablesItems_(False)
        self.name = name
        if child_items is not None:
            for item in child_items:
                self.append(item)
        self._menu_item = NSMenuItem.alloc().init()
        self._menu_item.setTitle_(_remove_mnemonic(label))
        self._menu_item.setSubmenu_(self._menu)
        # Hack to set the services menu
        if name == "ServicesMenu":
            NSApp().setServicesMenu_(self._menu_item)

    def show(self):
        self._menu_item.setHidden_(False)

    def hide(self):
        self._menu_item.setHidden_(True)

    def enable(self):
        self._menu_item.setEnabled_(True)

    def disable(self):
        self._menu_item.setEnabled_(False)

class AppMenu(MenuShell):
    """Wrapper for the application menu (AKA the Miro menu)

    We need to special case this because OSX automatically creates the menu
    item.
    """
    def __init__(self):
        MenuShell.__init__(self, NSApp().mainMenu().itemAtIndex_(0).submenu())
        self.name = "Miro Video Converter"

class MenuBar(MenuShell):
    """See the GTK version of this method for the current docstring."""
    def __init__(self):
        MenuShell.__init__(self, NSApp().mainMenu())
        self.create_signal('activate')
        self._add_app_menu()

    def _add_app_menu(self):
        """Add the app menu to this menu bar.

        We need to special case this because OSX automatically adds the
        NSMenuItem for the app menu, we just need to set up our wrappers.
        """
        self._app_menu = AppMenu()
        self.children.append(self._app_menu)
        self._app_menu.parent = self

    def add_initial_menus(self, menus):
        for menu in menus:
            self.append(menu)
        self._modify_initial_menus()

    def _extract_menu_item(self, name):
        """Helper method for changing the portable menu structure."""
        menu_item = self.find(name)
        menu_item.remove_from_parent()
        return menu_item

    def _modify_initial_menus(self):
        short_appname = "Miro Video Converter"    # XXX

        # Application menu
        miroMenuItems = [
            self._extract_menu_item("About"),
        ]

        miroMenuItems += [
            self._extract_menu_item("Quit")
        ]
        for item in miroMenuItems:
            self._app_menu.append(item)

        self._app_menu.find("EditPreferences").set_label(_("Preferences..."))
        self._app_menu.find("EditPreferences")._change_shortcut(
            Shortcut(",", MOD))
        self._app_menu.find("Quit").set_label(_("Quit %(appname)s",
                                       {"appname": short_appname}))

        # Help Menu
        #helpItem = self.find("Help")
        #helpItem.set_label(_("%(appname)s Help", {"appname": short_appname}))
        #helpItem._change_shortcut(Shortcut("?", MOD))

        self._update_present_menu()
        self._connect_to_signals()

    def do_activate(self, name):
        # We handle a couple OSX-specific actions here
        if name == "PresentActualSize":
            NSApp().delegate().present_movie('natural-size')
        elif name == "PresentDoubleSize":
            NSApp().delegate().present_movie('double-size')
        elif name == "PresentHalfSize":
            NSApp().delegate().present_movie('half-size')
        elif name == "ShowMain":
            app.widgetapp.window.nswindow.makeKeyAndOrderFront_(self)

    def _connect_to_signals(self):
        app.playback_manager.connect("will-play", self._on_playback_change)
        app.playback_manager.connect("will-stop", self._on_playback_change)

    def _on_playback_change(self, playback_manager, *args):
        self._update_present_menu()

    def _update_present_menu(self):
        if self._should_enable_present_menu():
            for menu_item in self.present_menu.get_children():
                menu_item.enable()
        else:
            for menu_item in self.present_menu.get_children():
                menu_item.disable()

    def _should_enable_present_menu(self):
        if (app.playback_manager.is_playing and
            not app.playback_manager.is_playing_audio):
            # we're currently playing video, allow the user to fullscreen
            return True
        selection_info = app.item_list_controller_manager.get_selection_info()
        if (selection_info.has_download and
            selection_info.has_file_type('video')):
            # A downloaded video is selected, allow the user to start playback
            # in fullscreen
            return True
        return False

#class ContextMenuHandler(NSObject):
#    def initWithCallback_(self, callback):
#        self = super(ContextMenuHandler, self).init()
#        self.callback = callback
#        return self
#
#    def handleMenuItem_(self, sender):
#        self.callback()
#
#class MiroContextMenu(NSMenu):
#    # Works exactly like NSMenu, except it keeps a reference to the menu
#    # handler objects.
#    def init(self):
#        self = super(MiroContextMenu, self).init()
#        self.handlers = set()
#        return self
#
#    def addItem_(self, item):
#        if isinstance(item.target(), ContextMenuHandler):
#            self.handlers.add(item.target())
#        return NSMenu.addItem_(self, item)
#
def make_context_menu(menu_items):
    nsmenu = MiroContextMenu.alloc().init()
    for item in menu_items:
        if item is None:
            nsitem = NSMenuItem.separatorItem()
        else:
            label, callback = item
            nsitem = NSMenuItem.alloc().init()
            if isinstance(label, tuple) and len(label) == 2:
                label, icon_path = label
                image = NSImage.alloc().initWithContentsOfFile_(icon_path)
                nsitem.setImage_(image)
            if callback is None:
                font_size = NSFont.systemFontSize()
                font = NSFont.fontWithName_size_("Lucida Sans Italic", font_size)
                if font is None:
                    font = NSFont.systemFontOfSize_(font_size)
                attributes = {NSFontAttributeName: font}
                attributed_label = NSAttributedString.alloc().initWithString_attributes_(label, attributes)
                nsitem.setAttributedTitle_(attributed_label)
            else:
                nsitem.setTitle_(label)
                if isinstance(callback, list):
                    submenu = make_context_menu(callback)
                    nsmenu.setSubmenu_forItem_(submenu, nsitem)
                else:
                    handler = ContextMenuHandler.alloc().initWithCallback_(callback)
                    nsitem.setTarget_(handler)
                    nsitem.setAction_('handleMenuItem:')
        nsmenu.addItem_(nsitem)
    return nsmenu

def translate_event_modifiers(event):
    mods = set()
    flags = event.modifierFlags()
    if flags & NSCommandKeyMask:
        mods.add(keyboard.CMD)
    if flags & NSControlKeyMask:
        mods.add(keyboard.CTRL)
    if flags & NSAlternateKeyMask:
        mods.add(keyboard.ALT)
    if flags & NSShiftKeyMask:
        mods.add(keyboard.SHIFT)
    return mods
