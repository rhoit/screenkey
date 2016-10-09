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


def geometry(string):
    size = re.match(r'^(\d+)x(\d+)(\+\d+\+\d+)?$', string)
    if size is None:
        raise TypeError
    wh = [int(size.group(1)), int(size.group(2))]
    if size.group(3) is None:
        xy = [0, 0]
    else:
        pos = re.match(r'^\+(\d+)\+(\d+)$', size.group(3))
        xy = [int(pos.group(1)), int(pos.group(2))]
    return xy + wh


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
        self.makeWidgets()

        self.on_change_mode()
        if self.cnf['persist']:
            self.show()

        self.show_all()


    def quit(self, *args):
        self.labelmngr.stop()
        Gtk.main_quit()


    def makeWidgets(self):
        self.label = Gtk.Label()
        self.add(self.label)

        self.label.set_ellipsize(Pango.EllipsizeMode.START)
        self.label.set_padding(self.width // 100, 0)
        self.label.set_justify(Gtk.Justification.CENTER)
        self.label_set_apperance()

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

        # screen.connect("size-changed", self.on_configure)
        # self.connect("configure-event", self.on_configure)
        self.set_active_monitor(self.cnf['screen'])
        screen.connect(
            "monitors-changed",
            lambda *a: self.set_active_monitor(self.monitor)
        )


    def cario_draw(self, widget, cr):
        cr.set_source_rgba(*self.cnf['background'])
        cr.set_operator(cairo.OPERATOR_SOURCE)
        cr.paint()
        cr.set_operator(cairo.OPERATOR_OVER)


    def set_active_monitor(self, monitor):
        scr = self.get_screen()
        if monitor >= scr.get_n_monitors():
            self.monitor = 0
        else:
            self.monitor = monitor
        self.update_geometry()


    def label_set_apperance(self):
        self.font = Pango.FontDescription()
        self.font.set_family(self.cnf['font_family'])
        self.font.set_weight(self.cnf['font_weight'])
        self.font.set_size(Pango.SCALE * self.cnf['font_size'])
        self.font.set_size(Pango.SCALE * self.cnf['font_size'])

        self.label.modify_font(self.font)
        self.label.override_color(
            Gtk.StateFlags.NORMAL,
            Gdk.RGBA(*self.cnf['foreground'])
        )


    def update_geometry(self, configure=False):
        if self.cnf['position'] == 'fixed' and self.cnf['geometry'] is not None:
            self.move(*self.cnf['geometry'][0:2])
            self.resize(*self.cnf['geometry'][2:4])
            return

        if self.cnf['geometry'] is not None:
            area_geometry = self.cnf['geometry']
        else:
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


    def show(self):
        self.update_geometry()
        super().show()


    def on_label_change(self, markup):
        r, attr, text, *z = Pango.parse_markup(markup, -1, '\000')
        self.label.set_text(text)
        # self.override_font_attributes(attr, text)
        # self.label.set_attributes(attr)

        if not self.get_property('visible'):
            self.show()
        if self.timer_hide:
            self.timer_hide.cancel()
        if self.cnf['timeout'] > 0:
            self.timer_hide = Timer(self.cnf['timeout'], self.on_timeout_main)
            self.timer_hide.start()
        if self.timer_min:
            self.timer_min.cancel()
        self.timer_min = Timer(self.cnf['recent_thr'] * 2, self.on_timeout_min)
        self.timer_min.start()


    def on_timeout_main(self):
        if not self.cnf['persist']:
            self.hide()
        self.label.set_text('')
        self.labelmngr.clear()


    def on_timeout_min(self):
        attr_lst = self.label.get_attributes()
        # attr = Pango.Attribute(Pango.Underline.NONE, 0, -1)
        # attr_lst.change(attr)
        # attr_lst.change(Pango.Underline.NONE)
        # self.label.set_attributes(attr_lst)


    def restart_labelmanager(self):
        self.logger.debug("Restart LabelManager")

        if self.labelmngr:
            self.labelmngr.stop()

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
        self.restart_labelmanager()
