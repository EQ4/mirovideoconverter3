import math

from Foundation import *
from AppKit import *
#from Quartz import *
from objc import YES, NO, nil

from .base import SimpleBin, FlippedView

def make_color((red, green, blue)):
    return NSColor.colorWithDeviceRed_green_blue_alpha_(red, green, blue,
                                                        1.0)


class SolidBackground(SimpleBin):
    def __init__(self,  color=None):
        SimpleBin.__init__(self)
        self.view = FlippedView.alloc().init()
        if color is not None:
            self.set_background_color(color)

    def set_background_color(self, color):
        self.view.setBackgroundColor_(make_color(color))


class ImageSurface(object):
    """See https://develop.participatoryculture.org/index.php/WidgetAPI for a description of the API for this class."""
    def __init__(self, image):
        """Create a new ImageSurface."""
        self.image = image.copy()
        self.width = image.width
        self.height = image.height

    def get_size(self):
        return self.width, self.height

    def draw(self, context, x, y, width, height, fraction=1.0):
        if self.width == 0 or self.height == 0:
            return
        current_context = NSGraphicsContext.currentContext()
        current_context.setShouldAntialias_(YES)
        current_context.setImageInterpolation_(NSImageInterpolationHigh)
        current_context.saveGraphicsState()
        flip_context(y + height)
        dest_rect = NSMakeRect(x, 0, width, height)
        if self.width >= width and self.height >= height:
            # drawing to area smaller than our image
            source_rect = NSMakeRect(0, 0, width, height)
            self.image.drawInRect_fromRect_operation_fraction_(
                dest_rect, source_rect, NSCompositeSourceOver, fraction)
        else:
            # drawing to area larger than our image.  Need to tile it.
            NSColor.colorWithPatternImage_(self.image).set()
            current_context.setPatternPhase_(
                    self._calc_pattern_phase(context, x, y))
            NSBezierPath.fillRect_(dest_rect)
        current_context.restoreGraphicsState()

    def draw_rect(self, context, dest_x, dest_y, source_x, source_y, width,
            height, fraction=1.0):
        if width == 0 or height == 0:
            return
        current_context = NSGraphicsContext.currentContext()
        current_context.setShouldAntialias_(YES)
        current_context.setImageInterpolation_(NSImageInterpolationHigh)
        current_context.saveGraphicsState()
        flip_context(dest_y + height)
        dest_y = 0
        dest_rect = NSMakeRect(dest_x, dest_y, width, height)
        source_rect = NSMakeRect(source_x, self.height-source_y-height,
                                 width, height)
        self.image.drawInRect_fromRect_operation_fraction_(
                dest_rect, source_rect, NSCompositeSourceOver, fraction)
        current_context.restoreGraphicsState()

    def _calc_pattern_phase(self, context, x, y):
        """Calculate the pattern phase to draw tiled images.

        When we draw with a pattern, we want the image in the pattern to start
        at the top-left of where we're drawing to.  This function does the
        dirty work necessary.

        :returns: NSPoint to send to setPatternPhase_
        """
        # convert to view coords
        view_point = NSPoint(context.origin.x + x, context.origin.y + y)
        # convert to window coords, which is setPatternPhase_ uses
        return context.view.convertPoint_toView_(view_point, nil)

def convert_cocoa_color(color):
    rgb = color.colorUsingColorSpaceName_(NSDeviceRGBColorSpace)
    return (rgb.redComponent(), rgb.greenComponent(), rgb.blueComponent())

def convert_widget_color(color, alpha=1.0):
    return NSColor.colorWithDeviceRed_green_blue_alpha_(color[0], color[1], 
                                                        color[2], alpha)
def flip_context(height):
    """Make the current context's coordinates flipped.

    This is useful for drawing images, since they use the normal cocoa
    coordinates and we use flipped versions.

    :param height: height of the current area we are drawing to.
    """
    xform = NSAffineTransform.transform()
    xform.translateXBy_yBy_(0, height)
    xform.scaleXBy_yBy_(1.0, -1.0)
    xform.concat()

class DrawingStyle(object):
    """See https://develop.participatoryculture.org/index.php/WidgetAPI for a description of the API for this class."""
    def __init__(self, bg_color=None, text_color=None):
        self.use_custom_style = True
        if text_color is None:
            self.text_color = self.default_text_color
        else:
            self.text_color = convert_cocoa_color(text_color)
        if bg_color is None:
            self.bg_color = self.default_bg_color
        else:
            self.bg_color = convert_cocoa_color(bg_color)

    default_text_color = convert_cocoa_color(NSColor.textColor())
    default_bg_color = convert_cocoa_color(NSColor.textBackgroundColor())

class DrawingContext:
    """See https://develop.participatoryculture.org/index.php/WidgetAPI for a description of the API for this class."""
    def __init__(self, view, drawing_area, rect):
        self.view = view
        self.path = NSBezierPath.bezierPath()
        self.color = NSColor.blackColor()
        self.width = drawing_area.size.width
        self.height = drawing_area.size.height
        self.origin = drawing_area.origin
        if drawing_area.origin != NSZeroPoint:
            xform = NSAffineTransform.transform()
            xform.translateXBy_yBy_(drawing_area.origin.x, 
                    drawing_area.origin.y)
            xform.concat()

    def move_to(self, x, y):
        self.path.moveToPoint_(NSPoint(x, y))

    def rel_move_to(self, dx, dy):
        self.path.relativeMoveToPoint_(NSPoint(dx, dy))

    def line_to(self, x, y):
        self.path.lineToPoint_(NSPoint(x, y))

    def rel_line_to(self, dx, dy):
        self.path.relativeLineToPoint_(NSPoint(dx, dy))

    def curve_to(self, x1, y1, x2, y2, x3, y3):
        self.path.curveToPoint_controlPoint1_controlPoint2_(
                NSPoint(x3, y3), NSPoint(x1, y1), NSPoint(x2, y2))

    def rel_curve_to(self, dx1, dy1, dx2, dy2, dx3, dy3):
        self.path.relativeCurveToPoint_controlPoint1_controlPoint2_(
                NSPoint(dx3, dy3), NSPoint(dx1, dy1), NSPoint(dx2, dy2))

    def arc(self, x, y, radius, angle1, angle2):
        angle1 = (angle1 * 360) / (2 * math.pi)
        angle2 = (angle2 * 360) / (2 * math.pi)
        center = NSPoint(x, y)
        self.path.appendBezierPathWithArcWithCenter_radius_startAngle_endAngle_(center, radius, angle1, angle2)

    def arc_negative(self, x, y, radius, angle1, angle2):
        angle1 = (angle1 * 360) / (2 * math.pi)
        angle2 = (angle2 * 360) / (2 * math.pi)
        center = NSPoint(x, y)
        self.path.appendBezierPathWithArcWithCenter_radius_startAngle_endAngle_clockwise_(center, radius, angle1, angle2, YES)

    def rectangle(self, x, y, width, height):
        rect = NSMakeRect(x, y, width, height)
        self.path.appendBezierPathWithRect_(rect)

    def set_color(self, color, alpha=1.0):
        self.color = convert_widget_color(color, alpha)
        self.color.set()
        
    def set_shadow(self, color, opacity, offset, blur_radius):
        shadow = NSShadow.alloc().init()
        # shadow offset is always in the cocoa coordinates, so we need to
        # reverse the y part
        shadow.setShadowOffset_(NSPoint(offset[0], -offset[1]))
        shadow.setShadowBlurRadius_(blur_radius)
        shadow.setShadowColor_(convert_widget_color(color, opacity))
        shadow.set()

    def set_line_width(self, width):
        self.path.setLineWidth_(width)

    def stroke(self):
        self.path.stroke()
        self.path.removeAllPoints()

    def stroke_preserve(self):
        self.path.stroke()

    def fill(self):
        self.path.fill()
        self.path.removeAllPoints()

    def fill_preserve(self):
        self.path.fill()

    def clip(self):
        self.path.addClip()
        self.path.removeAllPoints()

    def save(self):
        NSGraphicsContext.currentContext().saveGraphicsState()

    def restore(self):
        NSGraphicsContext.currentContext().restoreGraphicsState()

    def gradient_fill(self, gradient):
        self.gradient_fill_preserve(gradient)
        self.path.removeAllPoints()

    def gradient_fill_preserve(self, gradient):
        context = NSGraphicsContext.currentContext()
        context.saveGraphicsState()
        self.path.addClip()
        gradient.draw()
        context.restoreGraphicsState()

class Gradient(object):
    """See https://develop.participatoryculture.org/index.php/WidgetAPI for a description of the API for this class."""
    def __init__(self, x1, y1, x2, y2):
        self.x1, self.y1, self.x2, self.y2 = x1, y1, x2, y2
        self.start_color = None
        self.end_color = None

    def set_start_color(self, (red, green, blue)):
        self.start_color = (red, green, blue)

    def set_end_color(self, (red, green, blue)):
        self.end_color = (red, green, blue)
        
    def draw(self):
        start_color = convert_widget_color(self.start_color)
        end_color = convert_widget_color(self.end_color)
        nsgradient = NSGradient.alloc().initWithStartingColor_endingColor_(start_color, end_color)
        start_point = NSPoint(self.x1, self.y1)
        end_point = NSPoint(self.x2, self.y2)
        nsgradient.drawFromPoint_toPoint_options_(start_point, end_point, 0)

class DrawingMixin(object):
    def calc_size_request(self):
        return self.size_request(self.view.layout_manager)

    # squish width / squish height only make sense on GTK
    def set_squish_width(self, setting):
        pass

    def set_squish_height(self, setting):
        pass

    # Default implementations for methods that subclasses override.

    def is_opaque(self):
        return False

    def size_request(self, layout_manager):
        return 0, 0

    def draw(self, context, layout_manager):
        pass

    def viewport_repositioned(self):
        # since this is a Mixin class, we want to make sure that our other
        # classes see the viewport_repositioned() call.
        super(DrawingMixin, self).viewport_repositioned()
        self.queue_redraw()
