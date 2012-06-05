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

""".drawing -- Contains classes used to draw on
widgets.
"""

import cairo
import gobject
import gtk

import wrappermap
from .base import Widget, Bin
from .layoutmanager import LayoutManager

def css_to_color(css_string):
    parts = (css_string[1:3], css_string[3:5], css_string[5:7])
    return tuple((int(value, 16) / 255.0) for value in parts)

class ImageSurface:
    def __init__(self, image):
        format = cairo.FORMAT_RGB24
        if image.pixbuf.get_has_alpha():
            format = cairo.FORMAT_ARGB32
        self.image = cairo.ImageSurface(
            format, int(image.width), int(image.height))
        context = cairo.Context(self.image)
        gdkcontext = gtk.gdk.CairoContext(context)
        gdkcontext.set_source_pixbuf(image.pixbuf, 0, 0)
        gdkcontext.paint()
        self.pattern = cairo.SurfacePattern(self.image)
        self.pattern.set_extend(cairo.EXTEND_REPEAT)
        self.width = image.width
        self.height = image.height

    def get_size(self):
        return self.width, self.height

    def _align_pattern(self, x, y):
        """Line up our image pattern so that it's top-left corner is x, y."""
        m = cairo.Matrix()
        m.translate(-x, -y)
        self.pattern.set_matrix(m)

    def draw(self, context, x, y, width, height, fraction=1.0):
        self._align_pattern(x, y)
        cairo_context = context.context
        cairo_context.save()
        cairo_context.set_source(self.pattern)
        cairo_context.new_path()
        cairo_context.rectangle(x, y, width, height)
        if fraction >= 1.0:
            cairo_context.fill()
        else:
            cairo_context.clip()
            cairo_context.paint_with_alpha(fraction)
        cairo_context.restore()

    def draw_rect(self, context, dest_x, dest_y, source_x, source_y,
            width, height, fraction=1.0):

        self._align_pattern(dest_x-source_x, dest_y-source_y)
        cairo_context = context.context
        cairo_context.save()
        cairo_context.set_source(self.pattern)
        cairo_context.new_path()
        cairo_context.rectangle(dest_x, dest_y, width, height)
        if fraction >= 1.0:
            cairo_context.fill()
        else:
            cairo_context.clip()
            cairo_context.paint_with_alpha(fraction)
        cairo_context.restore()

class DrawingStyle(object):
    def __init__(self, widget, use_base_color=False, state=None):
        if state is None:
            state = widget._widget.state
        self.use_custom_style = widget.use_custom_style
        self.style = widget._widget.style
        self.text_color = widget.convert_gtk_color(self.style.text[state])
        if use_base_color:
            self.bg_color = widget.convert_gtk_color(self.style.base[state])
        else:
            self.bg_color = widget.convert_gtk_color(self.style.bg[state])

class DrawingContext(object):
    """DrawingContext.  This basically just wraps a Cairo context and adds a
    couple convenience methods.
    """

    def __init__(self, window, drawing_area, expose_area):
        self.window = window
        self.context = window.cairo_create()
        self.context.rectangle(expose_area.x, expose_area.y, 
                expose_area.width, expose_area.height)
        self.context.clip()
        self.width = drawing_area.width
        self.height = drawing_area.height
        self.context.translate(drawing_area.x, drawing_area.y)

    def __getattr__(self, name):
        return getattr(self.context, name)

    def set_color(self, (red, green, blue), alpha=1.0):
        self.context.set_source_rgba(red, green, blue, alpha)

    def set_shadow(self, color, opacity, offset, blur_radius):
        pass

    def gradient_fill(self, gradient):
        old_source = self.context.get_source()
        self.context.set_source(gradient.pattern)
        self.context.fill()
        self.context.set_source(old_source)

    def gradient_fill_preserve(self, gradient):
        old_source = self.context.get_source()
        self.context.set_source(gradient.pattern)
        self.context.fill_preserve()
        self.context.set_source(old_source)

class Gradient(object):
    def __init__(self, x1, y1, x2, y2):
        self.pattern = cairo.LinearGradient(x1, y1, x2, y2)

    def set_start_color(self, (red, green, blue)):
        self.pattern.add_color_stop_rgb(0, red, green, blue)

    def set_end_color(self, (red, green, blue)):
        self.pattern.add_color_stop_rgb(1, red, green, blue)

class CustomDrawingMixin(object):
    def do_expose_event(self, event):
        wrapper = wrappermap.wrapper(self)
        if self.flags() & gtk.NO_WINDOW:
            drawing_area = self.allocation
        else:
            drawing_area = gtk.gdk.Rectangle(0, 0, 
                    self.allocation.width, self.allocation.height)
        context = DrawingContext(event.window, drawing_area, event.area)
        context.style = DrawingStyle(wrapper)
        if self.flags() & gtk.CAN_FOCUS:
            focus_space = (self.style_get_property('focus-padding') +
                    self.style_get_property('focus-line-width'))
            if not wrapper.squish_width:
                context.width -= focus_space * 2
                translate_x = focus_space
            else:
                translate_x = 0
            if not wrapper.squish_height:
                context.height -= focus_space * 2
                translate_y = focus_space
            else:
                translate_y = 0
            context.translate(translate_x, translate_y)
        wrapper.layout_manager.update_cairo_context(context.context)
        self.draw(wrapper, context)

    def draw(self, wrapper, context):
        wrapper.layout_manager.reset()
        wrapper.draw(context, wrapper.layout_manager)

    def do_size_request(self, requesition):
        wrapper = wrappermap.wrapper(self)
        width, height = wrapper.size_request(wrapper.layout_manager)
        requesition.width = width
        requesition.height = height
        if self.flags() & gtk.CAN_FOCUS:
            focus_space = (self.style_get_property('focus-padding') +
                    self.style_get_property('focus-line-width'))
            if not wrapper.squish_width:
                requesition.width += focus_space * 2
            if not wrapper.squish_height:
                requesition.height += focus_space * 2

class MiroDrawingArea(CustomDrawingMixin, gtk.Widget):
    def __init__(self):
        gtk.Widget.__init__(self)
        CustomDrawingMixin.__init__(self)
        self.set_flags(gtk.NO_WINDOW)

class BackgroundWidget(CustomDrawingMixin, gtk.Bin):
    def do_size_request(self, requesition):
        CustomDrawingMixin.do_size_request(self, requesition)
        if self.get_child():
            child_width, child_height = self.get_child().size_request()
            requesition.width = max(child_width, requesition.width)
            requesition.height = max(child_height, requesition.height)

    def do_expose_event(self, event):
        CustomDrawingMixin.do_expose_event(self, event)
        if self.get_child():
            self.propagate_expose(self.get_child(), event)

    def do_size_allocate(self, allocation):
        gtk.Bin.do_size_allocate(self, allocation)
        if self.get_child():
            self.get_child().size_allocate(allocation)

gobject.type_register(MiroDrawingArea)
gobject.type_register(BackgroundWidget)

class Drawable:
    def __init__(self):
        self.squish_width = self.squish_height = False

    def set_squish_width(self, setting):
        self.squish_width = setting

    def set_squish_height(self, setting):
        self.squish_height = setting

    def set_widget(self, drawing_widget):
        if self.is_opaque() and 0:
            box = gtk.EventBox()
            box.add(drawing_widget)
            Widget.set_widget(self, box)
        else:
            Widget.set_widget(self, drawing_widget)
        self.layout_manager = LayoutManager(self._widget)

    def size_request(self, layout_manager):
        return 0, 0

    def draw(self, context, layout_manager):
        pass

    def is_opaque(self):
        return False

class DrawingArea(Drawable, Widget):
    def __init__(self):
        Widget.__init__(self)
        Drawable.__init__(self)
        self.set_widget(MiroDrawingArea())

class Background(Drawable, Bin):
    def __init__(self):
        Bin.__init__(self)
        Drawable.__init__(self)
        self.set_widget(BackgroundWidget())
