
"""textlayout.py -- Contains the LayoutManager class.  It handles laying text,
buttons, getting font metrics and other tasks that are required to size
things.
"""
import math

from AppKit import *
from Foundation import *
from objc import YES, NO, nil

INFINITE = 1000000 # size of an "infinite" dimension

class MiroLayoutManager(NSLayoutManager):
    """Overide NSLayoutManager to draw better underlines."""

    def drawUnderlineForGlyphRange_underlineType_baselineOffset_lineFragmentRect_lineFragmentGlyphRange_containerOrigin_(self, glyph_range, typ, offset, line_rect, line_glyph_range, container_origin):
        container, _ = self.textContainerForGlyphAtIndex_effectiveRange_(glyph_range.location, None)
        rect = self.boundingRectForGlyphRange_inTextContainer_(glyph_range, container)
        x = container_origin.x + rect.origin.x
        y = (container_origin.y + rect.origin.y + rect.size.height - offset)
        underline_height, offset = self.calc_underline_extents(glyph_range)
        y = math.ceil(y + offset) + underline_height / 2.0
        path = NSBezierPath.bezierPath()
        path.setLineWidth_(underline_height)
        path.moveToPoint_(NSPoint(x, y))
        path.relativeLineToPoint_(NSPoint(rect.size.width, 0))
        path.stroke()

    def calc_underline_extents(self, line_glyph_range):
        index = self.characterIndexForGlyphAtIndex_(line_glyph_range.location)
        font, _ = self.textStorage().attribute_atIndex_effectiveRange_(NSFontAttributeName, index, None)
        # we use a couple of magic numbers that seems to work okay.  I (BDK)
        # got it from some old mozilla code.
        height = font.ascender() - font.descender()
        height = max(1.0, round(0.05 * height))
        offset = max(1.0, round(0.1 * height))
        return height, offset

class TextBoxPool(object):
    """Handles a pool of TextBox objects.  We monitor the TextBox objects and
    when those objects die, we reclaim them for the pool.

    Creating TextBoxes is fairly expensive and NSLayoutManager do a lot of
    caching, so it's useful to keep them around rather than destroying them.
    """

    def __init__(self):
        self.used_text_boxes = []
        self.available_text_boxes = []

    def get(self):
        """Get a NSLayoutManager, either from the pool or by creating a new
        one.
        """
        try:
            rv = self.available_text_boxes.pop()
        except IndexError:
            rv = TextBox()
        self.used_text_boxes.append(rv)
        return rv

    def reclaim_textboxes(self):
        """Move used TextBoxes back to the available pool.  This should be
        called after the code using text boxes is done using all of them.
        """
        self.available_text_boxes.extend(self.used_text_boxes)
        self.used_text_boxes[:] = []

text_box_pool = TextBoxPool()

class Font(object):
    line_height_sizer = NSLayoutManager.alloc().init()

    def __init__(self, nsfont):
        self.nsfont = nsfont

    def ascent(self):
        return self.nsfont.ascender()

    def descent(self):
        return -self.nsfont.descender()

    def line_height(self):
        return Font.line_height_sizer.defaultLineHeightForFont_(self.nsfont)

class FontPool(object):
    def __init__(self):
        self._cached_fonts = {}

    def get(self, scale_factor, bold, italic, family):
        cache_key = (scale_factor, bold, italic, family)
        try:
            return self._cached_fonts[cache_key]
        except KeyError:
            font = self._create(scale_factor, bold, italic, family)
            self._cached_fonts[cache_key] = font
            return font

    def _create(self, scale_factor, bold, italic, family):
        size = round(scale_factor * NSFont.systemFontSize())
        if family is None:
            if bold:
                nsfont = NSFont.boldSystemFontOfSize_(size)
            else:
                nsfont = NSFont.systemFontOfSize_(size)
        else:
            if bold:
                nsfont = NSFont.fontWithName_size_(family + " Bold", size)
            else:
                nsfont = NSFont.fontWithName_size_(family, size)
        return Font(nsfont)

class LayoutManager(object):
    font_pool = FontPool()
    default_font = font_pool.get(1.0, False, False, None)

    def __init__(self):
        self.current_font = self.default_font
        self.set_text_color((0, 0, 0))
        self.set_text_shadow(None)

    def font(self, scale_factor, bold=False, italic=False, family=None):
        return self.font_pool.get(scale_factor, bold, italic, family)

    def set_font(self, scale_factor, bold=False, italic=False, family=None):
        self.current_font = self.font(scale_factor, bold, italic, family)

    def set_text_color(self, color):
        self.text_color = color

    def set_text_shadow(self, shadow):
        self.shadow = shadow

    def textbox(self, text, underline=False):
        text_box = text_box_pool.get()
        color = NSColor.colorWithDeviceRed_green_blue_alpha_(self.text_color[0], self.text_color[1], self.text_color[2], 1.0)
        text_box.reset(text, self.current_font, color, self.shadow, underline)
        return text_box

    def button(self, text, pressed=False, disabled=False, style='normal'):
        if style == 'webby':
            return StyledButton(text, self.current_font, pressed, disabled)
        else:
            return NativeButton(text, self.current_font, pressed, disabled)

    def reset(self):
        text_box_pool.reclaim_textboxes()
        self.current_font = self.default_font
        self.text_color = (0, 0, 0)
        self.shadow = None

class TextBox(object):
    def __init__(self):
        self.layout_manager = MiroLayoutManager.alloc().init()
        container = NSTextContainer.alloc().init()
        container.setLineFragmentPadding_(0)
        self.layout_manager.addTextContainer_(container)
        self.layout_manager.setUsesFontLeading_(NO)
        self.text_storage = NSTextStorage.alloc().init()
        self.text_storage.addLayoutManager_(self.layout_manager)
        self.text_container = self.layout_manager.textContainers()[0]

    def reset(self, text, font, color, shadow, underline):
        """Reset the text box so it's ready to be used by a new owner."""
        self.text_storage.deleteCharactersInRange_(NSRange(0, 
            self.text_storage.length()))
        self.text_container.setContainerSize_(NSSize(INFINITE, INFINITE))
        self.paragraph_style = NSMutableParagraphStyle.alloc().init()
        self.font = font
        self.color = color
        self.shadow = shadow
        self.width = None
        self.set_text(text, underline=underline)

    def make_attr_string(self, text, color, font, underline):
        attributes = NSMutableDictionary.alloc().init()
        if color is not None:
            nscolor = NSColor.colorWithDeviceRed_green_blue_alpha_(color[0], color[1], color[2], 1.0)
            attributes.setObject_forKey_(nscolor, NSForegroundColorAttributeName)
        else:
            attributes.setObject_forKey_(self.color, NSForegroundColorAttributeName)
        if font is not None:
            attributes.setObject_forKey_(font.nsfont, NSFontAttributeName)
        else:
            attributes.setObject_forKey_(self.font.nsfont, NSFontAttributeName)
        if underline:
            attributes.setObject_forKey_(NSUnderlineStyleSingle, NSUnderlineStyleAttributeName)
        attributes.setObject_forKey_(self.paragraph_style.copy(), NSParagraphStyleAttributeName)
        if text is None:
            text = ""
        return NSAttributedString.alloc().initWithString_attributes_(text, attributes)

    def set_text(self, text, color=None, font=None, underline=False):
        string = self.make_attr_string(text, color, font, underline)
        self.text_storage.setAttributedString_(string)

    def append_text(self, text, color=None, font=None, underline=False):
        string = self.make_attr_string(text, color, font, underline)
        self.text_storage.appendAttributedString_(string)

    def set_width(self, width):
        if width is not None:
            self.text_container.setContainerSize_(NSSize(width, INFINITE))
        else:
            self.text_container.setContainerSize_(NSSize(INFINITE, INFINITE))
        self.width = width

    def update_paragraph_style(self):
        attr = NSParagraphStyleAttributeName
        value = self.paragraph_style.copy()
        rnge = NSMakeRange(0, self.text_storage.length())
        self.text_storage.addAttribute_value_range_(attr, value, rnge)

    def set_wrap_style(self, wrap):
        if wrap == 'word':
            self.paragraph_style.setLineBreakMode_(NSLineBreakByWordWrapping)
        elif wrap == 'char':
            self.paragraph_style.setLineBreakMode_(NSLineBreakByCharWrapping)
        elif wrap == 'truncated-char':
            self.paragraph_style.setLineBreakMode_(NSLineBreakByTruncatingTail)
        else:
            raise ValueError("Unknown wrap value: %s" % wrap)
        self.update_paragraph_style()

    def set_alignment(self, align):
        if align == 'left':
            self.paragraph_style.setAlignment_(NSLeftTextAlignment)
        elif align == 'right':
            self.paragraph_style.setAlignment_(NSRightTextAlignment)
        elif align == 'center':
            self.paragraph_style.setAlignment_(NSCenterTextAlignment)
        else:
            raise ValueError("Unknown align value: %s" % align)
        self.update_paragraph_style()

    def get_size(self):
        # The next line is there just to force cocoa to layout the text
        self.layout_manager.glyphRangeForTextContainer_(self.text_container)
        rect = self.layout_manager.usedRectForTextContainer_(self.text_container)
        return rect.size.width, rect.size.height

    def char_at(self, x, y):
        width, height = self.get_size()
        if 0 <= x < width and 0 <= y < height:
            index, _ = self.layout_manager.glyphIndexForPoint_inTextContainer_fractionOfDistanceThroughGlyph_(NSPoint(x, y), self.text_container, None)
            return index
        else:
            return None

    def draw(self, context, x, y, width, height):
        if self.shadow is not None:
            context.save()
            context.set_shadow(self.shadow.color, self.shadow.opacity, self.shadow.offset, self.shadow.blur_radius)
        self.width = width
        self.text_container.setContainerSize_(NSSize(width, height))
        glyph_range = self.layout_manager.glyphRangeForTextContainer_(self.text_container)
        self.layout_manager.drawGlyphsForGlyphRange_atPoint_(glyph_range, NSPoint(x, y))
        if self.shadow is not None:
            context.restore()
        context.path.removeAllPoints()
