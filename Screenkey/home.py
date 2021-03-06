#!/usr/bin/env python3

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk
from gi.repository import Pango

import json
import cairo
import subprocess
from threading import Timer

from labelmanager import LabelManager


class Home(Gtk.Window):
    def __init__(self, cnf, logger):
        Gtk.Window.__init__(self, Gtk.WindowType.POPUP)

        self.logger = logger
        self.cnf = cnf

        self.enabled = True

        self.timer_hide = None
        self.timer_min = None
        self.labelmngr = None

        self.width, self.height = self.get_size()
        self.set_active_monitor(self.cnf['screen'])
        self.font = Pango.FontDescription()

        self.makeWidgets()
        self.customizeWindow()
        self.start_labelmanager()
        self.on_label_change("Screencast your keys")
        self.show_all()


    def quit(self, *args):
        self.labelmngr.stop()
        Gtk.main_quit()


    def makeWidgets(self):
        self.label = Gtk.Label()
        self.add(self.label)

        self.label.set_padding(20, 0)
        self.label.set_justify(Gtk.Justification.CENTER)
        self.label.set_ellipsize(Pango.EllipsizeMode.START)
        self.label_set_apperance()


    def label_set_apperance(self):
        self.font.set_family(self.cnf['font_family'])
        self.font.set_weight(self.cnf['font_weight'])
        self.font.set_size(Pango.SCALE * self.cnf['font_size'])

        self.label.modify_font(self.font)
        self.label.override_color(
            Gtk.StateFlags.NORMAL,
            Gdk.RGBA(*self.cnf['foreground'])
        )


    def customizeWindow(self):
        self.set_gravity(Gdk.Gravity.CENTER)
        self.set_keep_above(True)
        self.set_accept_focus(False)
        self.set_focus_on_map(False)

        screen = self.get_screen()
        visual = screen.get_rgba_visual()

        if screen.is_composited() and visual is not None:
            # print("Supports trasparency")
            self.set_visual(visual)
            self.set_app_paintable(True)
            self.connect("draw", self.cario_draw)

        # self.connect("configure-event", self.on_configure)
        # screen.connect(
        #     "monitors-changed",
        #     lambda *a: self.set_active_monitor(self.monitor)
        # )
        # screen.connect("size-changed", self.set_geometry)
        self.set_geometry()


    def cario_draw(self, widget, cr):
        cr.set_source_rgba(*self.cnf['background'])
        cr.set_operator(cairo.OPERATOR_SOURCE)
        cr.paint()
        cr.set_operator(cairo.OPERATOR_OVER)


    def set_active_monitor(self, monitor):
        screen = self.get_screen()
        self.monitor = 0 if monitor >= screen.get_n_monitors() else 0
        self.set_geometry()


    def set_geometry(self, geometry=None):
        if geometry:
            self.home.parse_geometry(geometry)
            return

        geometry = self.get_screen().get_monitor_geometry(self.monitor)
        area_geometry = [geometry.x, geometry.y, geometry.width, geometry.height]

        window_height = self.cnf['font_size'] * area_geometry[3] // 200
        self.resize(area_geometry[2], window_height)

        if self.cnf['position'] == 'top':
            window_y = area_geometry[1] + area_geometry[3] // 10
        elif self.cnf['position'] == 'center':
            window_y = area_geometry[1] + area_geometry[3] // 2 - window_height // 2
        else:
            window_y = area_geometry[1] + area_geometry[3] * 9 // 10 - window_height
        self.move(area_geometry[0], window_y)


    def _timeout(self, time, func, obj=None):
        if obj: obj.cancel()
        if time <= 0: return
        obj = Timer(time, func)
        obj.start()
        return obj


    def on_label_change(self, markup):
        r, attr, text, *z = Pango.parse_markup(markup, -1, '\000')
        self.label.set_text(text)
        self.label.set_attributes(attr)

        if not self.get_property('visible'):
            # self.set_geometry() # if enter is pressed and not traslated
            self.show()

        self.timer_hide = self._timeout(
            self.cnf['timeout'],
            self.on_timeout_main,
            self.timer_hide
        )

        self.timer_min = self._timeout(
            self.cnf['recent_thr'],
            self.on_timeout_min,
            self.timer_min
        )



    def on_timeout_main(self):
        self.label.set_text('')
        self.labelmngr.clear()
        if not self.cnf['persist']:
            self.hide()


    def on_timeout_min(self):
        attr = Pango.Attribute()
        # attr_lst.change(Pango.Underline.NONE)
        # attr_lst.change(attr)
        # attr_lst = self.label.get_attributes()
        # self.label.set_attributes(attr_lst)


    def start_labelmanager(self):
        self.labelmngr = LabelManager(
            self.on_label_change,
            logger     = self.logger,
            key_mode   = self.cnf['key_mode'],
            bak_mode   = self.cnf['bak_mode'],
            mods_mode  = self.cnf['mods_mode'],
            mods_only  = self.cnf['mods_only'],
            multiline  = self.cnf['multiline'],
            vis_shift  = self.cnf['vis_shift'],
            vis_space  = self.cnf['vis_space'],
            recent_thr = self.cnf['recent_thr'],
            compr_cnt  = self.cnf['compr_cnt'],
            ignore     = self.cnf['ignore'],
            pango_ctx  = self.label.get_pango_context()
        )
        self.labelmngr.start()


    def on_change_mode(self):
        if not self.enabled:
            return

        if self.labelmngr:
            self.labelmngr.stop()
        self.logger.debug("Restart LabelManager")
        self.start_labelmanager()
