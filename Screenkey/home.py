#!/usr/bin/env python3

import os, sys

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk
from gi.repository import GLib, Pango

import inputlistener
import keysyms
import xlib
from labelmanager import LabelManager

from threading import Timer
import json
import subprocess
import traceback

class Home(Gtk.Window):
    STATE_FILE = os.path.join(GLib.get_user_config_dir(), 'screenkey.json')

    def __init__(self, logger, options, show_settings=False):
        Gtk.Window.__init__(self, Gtk.WindowType.POPUP)

        self.timer_hide = None
        self.timer_min = None
        self.logger = logger

        # TODO load_state later
        self.options = options # self.load_state()

        self.set_keep_above(True)
        self.set_accept_focus(False)
        self.set_focus_on_map(False)

        self.label = Gtk.Label()
        self.label.set_attributes(Pango.AttrList())
        self.label.set_ellipsize(Pango.EllipsizeMode.START)
        self.label.set_justify(Gtk.Justification.CENTER)
        self.label.show()
        self.add(self.label)

        self.set_gravity(Gdk.Gravity.CENTER)
        self.connect("configure-event", self.on_configure)
        scr = self.get_screen()
        scr.connect("size-changed", self.on_configure)
        scr.connect("monitors-changed", self.on_monitors_changed)
        self.set_active_monitor(self.options['screen'])

        self.font = Pango.FontDescription(self.options['font_desc'])
        self.update_colors()
        self.update_label()

        self.labelmngr = None
        self.enabled = True
        self.on_change_mode()

        self.make_menu()
        # self.about = self.make_about_dialog()
        # self.make_preferences_dialog()

        if not self.options['no_systray']:
            self.make_systray()

        self.connect("delete-event", self.quit)
        if show_settings:
            self.on_preferences_dialog()
        if self.options['persist']:
            self.show()


    def quit(self, widget, data=None):
        self.labelmngr.stop()
        Gtk.main_quit()


    def load_state(self):
        """Load stored options"""
        options = None
        try:
            with open(self.STATE_FILE, 'r') as f:
                options = Options(json.load(f))
                self.logger.debug("Options loaded.")
        except IOError:
            self.logger.debug("file %s does not exists." % self.STATE_FILE)
        except ValueError:
            self.logger.debug("file %s is invalid." % self.STATE_FILE)

        return options


    def store_state(self, options):
        """Store options"""
        try:
            with open(self.STATE_FILE, 'w') as f:
                json.dump(options, f)
                self.logger.debug("Options saved.")
        except IOError:
            self.logger.debug("Cannot open %s." % self.STATE_FILE)


    def set_active_monitor(self, monitor):
        scr = self.get_screen()
        if monitor >= scr.get_n_monitors():
            self.monitor = 0
        else:
            self.monitor = monitor
        self.update_geometry()


    def on_monitors_changed(self, *_):
        self.set_active_monitor(self.monitor)


    def override_font_attributes(self, attr, text):
        window_width, window_height = self.get_size()
        lines = text.count('\n') + 1
        try:
            attr.insert(Pango.AttrSizeAbsolute((50 * window_height // lines // 100) * 1000, 0, -1))
            attr.insert(Pango.AttrFamily(self.font.get_family(), 0, -1))
            attr.insert(Pango.AttrWeight(self.font.get_weight(), 0, -1))
        except:
            traceback.print_exception(*sys.exc_info())



    def update_label(self):
        attr = self.label.get_attributes()
        text = self.label.get_text()
        self.override_font_attributes(attr, text)
        self.label.set_attributes(attr)


    def update_colors(self):
        try:
            self.label.modify_fg(Gtk.StateFlags.NORMAL, Gtk.gdk.color_parse(self.options['font_color']))
            # self.label.get_style_context().set_background_color(Gtk.StateFlags.NORMAL)
            self.modify_bg(Gtk.StateFlags.NORMAL, Gtk.gdk.color_parse(self.options['bg_color']))
            self.set_opacity(self.options.opacity)
        except:
            traceback.print_exception(*sys.exc_info())


    def on_configure(self, *_):
        window_x, window_y = self.get_position()
        window_width, window_height = self.get_size()

        mask = Gtk.gdk.Pixmap(None, window_width, window_height, 1)
        gc = Gtk.gdk.GC(mask)
        gc.set_foreground(Gtk.gdk.Color(pixel=0))
        mask.draw_rectangle(gc, True, 0, 0, window_width, window_height)
        self.input_shape_combine_mask(mask, 0, 0)

        # set some proportional inner padding
        self.label.set_padding(window_width // 100, 0)

        self.update_label()


    def update_geometry(self, configure=False):
        if self.options['position'] == 'fixed' and self.options.geometry is not None:
            self.move(*self.options.geometry[0:2])
            self.resize(*self.options.geometry[2:4])
            return

        if self.options['geometry'] is not None:
            area_geometry = self.options.geometry
        else:
            geometry = self.get_screen().get_monitor_geometry(self.monitor)
            area_geometry = [geometry.x, geometry.y, geometry.width, geometry.height]

        if self.options['font_size'] == 'large':
            window_height = 24 * area_geometry[3] // 100
        elif self.options['font_size'] == 'medium':
            window_height = 12 * area_geometry[3] // 100
        else:
            window_height = 8 * area_geometry[3] // 100
        self.resize(area_geometry[2], window_height)

        if self.options['position'] == 'top':
            window_y = area_geometry[1] + area_geometry[3] // 10
        elif self.options['position'] == 'center':
            window_y = area_geometry[1] + area_geometry[3] // 2 - window_height // 2
        else:
            window_y = area_geometry[1] + area_geometry[3] * 9 // 10 - window_height
        self.move(area_geometry[0], window_y)


    def on_statusicon_popup(self, widget, button, timestamp, data=None):
        if button == 3 and data:
            data.show()
            data.popup(None, None, Gtk.status_icon_position_menu,
                       3, timestamp, widget)


    def show(self):
        self.update_geometry()
        super().show()


    def on_label_change(self, markup):
        r, attr, text, *z = Pango.parse_markup(markup, -1, '\000')
        self.override_font_attributes(attr, text)
        self.label.set_text(text)
        self.label.set_attributes(attr)

        if not self.get_property('visible'):
            self.show()
        if self.timer_hide:
            self.timer_hide.cancel()
        if self.options['timeout'] > 0:
            self.timer_hide = Timer(self.options['timeout'], self.on_timeout_main)
            self.timer_hide.start()
        if self.timer_min:
            self.timer_min.cancel()
        self.timer_min = Timer(self.options['recent_thr'] * 2, self.on_timeout_min)
        self.timer_min.start()


    def on_timeout_main(self):
        if not self.options['persist']:
            self.hide()
        self.label.set_text('')
        self.labelmngr.clear()


    def on_timeout_min(self):
        attr = self.label.get_attributes()
        attr.change(Pango.AttrUnderline(Pango.UNDERLINE_NONE, 0, -1))
        self.label.set_attributes(attr)


    def restart_labelmanager(self):
        self.logger.debug("Restarting LabelManager.")
        if self.labelmngr:
            self.labelmngr.stop()
        self.labelmngr = LabelManager(
            self.on_label_change,
            logger     = self.logger,
            key_mode   = self.options['key_mode'],
            bak_mode   = self.options['bak_mode'],
            mods_mode  = self.options['mods_mode'],
            mods_only  = self.options['mods_only'],
            multiline  = self.options['multiline'],
            vis_shift  = self.options['vis_shift'],
            vis_space  = self.options['vis_space'],
            recent_thr = self.options['recent_thr'],
            compr_cnt  = self.options['compr_cnt'],
            ignore     = self.options['ignore'],
            pango_ctx  = self.label.get_pango_context())
        self.labelmngr.start()


    def on_change_mode(self):
        if not self.enabled:
            return
        self.restart_labelmanager()


    def on_show_keys(self, widget, data=None):
        self.enabled = widget.get_active()
        if self.enabled:
            self.logger.debug("Screenkey enabled.")
            self.restart_labelmanager()
        else:
            self.logger.debug("Screenkey disabled.")
            self.labelmngr.stop()


    def on_preferences_dialog(self, widget=None, data=None):
        self.prefs.show()


    def on_preferences_changed(self, widget=None, data=None):
        self.store_state(self.options)
        self.prefs.hide()
        return True


    def make_preferences_dialog(self):
        # TODO: switch to something declarative or at least clean-up the following mess
        self.prefs = prefs = Gtk.Dialog(
            title = 'screenkey',
            parent = self,
            flags = Gtk.DialogFlags.DESTROY_WITH_PARENT,
            buttons = (Gtk.STOCK_CLOSE, Gtk.ResponseType.CLOSE)
        )

        prefs.connect("response", self.on_preferences_changed)
        prefs.connect("delete-event", self.on_preferences_changed)

        def on_sb_time_changed(widget, data=None):
            self.options.timeout = widget.get_value()
            self.logger.debug("Timeout value changed: %f." % self.options.timeout)

        def on_cbox_sizes_changed(widget, data=None):
            index = widget.get_active()
            self.options.font_size = FONT_SIZES.keys()[index]
            self.update_geometry()
            self.logger.debug("Window size changed: %s." % self.options.font_size)

        def on_cbox_modes_changed(widget, data=None):
            index = widget.get_active()
            self.options.key_mode = KEY_MODES.keys()[index]
            self.on_change_mode()
            self.logger.debug("Key mode changed: %s." % self.options.key_mode)

        def on_cbox_bak_changed(widget, data=None):
            index = widget.get_active()
            self.options.bak_mode = BAK_MODES.keys()[index]
            self.on_change_mode()
            self.logger.debug("Bak mode changed: %s." % self.options.bak_mode)

        def on_cbox_mods_changed(widget, data=None):
            index = widget.get_active()
            self.options.mods_mode = MODS_MODES.keys()[index]
            self.on_change_mode()
            self.logger.debug("Mods mode changed: %s." % self.options.mods_mode)

        def on_cbox_modsonly_changed(widget, data=None):
            self.options.mods_only = widget.get_active()
            self.on_change_mode()
            self.logger.debug("Modifiers only changed: %s." % self.options.mods_only)

        def on_cbox_visshift_changed(widget, data=None):
            self.options.vis_shift = widget.get_active()
            self.on_change_mode()
            self.logger.debug("Visible Shift changed: %s." % self.options.vis_shift)

        def on_cbox_visspace_changed(widget, data=None):
            self.options.vis_space = widget.get_active()
            self.on_change_mode()
            self.logger.debug("Show Whitespace changed: %s." % self.options.vis_space)

        def on_cbox_position_changed(widget, data=None):
            index = widget.get_active()
            new_position = POSITIONS.keys()[index]
            if new_position == 'fixed':
                new_geom = on_btn_sel_geom(widget)
                if not new_geom:
                    self.cbox_positions.set_active(POSITIONS.keys().index(self.options.position))
                    return
            elif self.options.position == 'fixed':
                # automatically clear geometry
                self.options.geometry = None
            self.options.position = new_position
            self.update_geometry()
            self.logger.debug("Window position changed: %s." % self.options.position)

        def on_cbox_screen_changed(widget, data=None):
            self.options.screen = widget.get_active()
            self.set_active_monitor(self.options.screen)
            self.logger.debug("Screen changed: %d." % self.options.screen)

        def on_cbox_persist_changed(widget, data=None):
            self.options.persist = widget.get_active()
            if not self.get_property('visible'):
                self.show()
            else:
                self.on_label_change(self.label.get_text())
            self.logger.debug("Persistent changed: %s." % self.options.persist)

        def on_sb_compr_changed(widget, data=None):
            self.options.compr_cnt = widget.get_value_as_int()
            self.on_change_mode()
            self.logger.debug("Compress repeats value changed: %d." % self.options.compr_cnt)

        def on_cbox_compr_changed(widget, data=None):
            compr_enabled = widget.get_active()
            self.sb_compr.set_sensitive(compr_enabled)
            self.options.compr_cnt = self.sb_compr.get_value_as_int() if compr_enabled else 0
            self.on_change_mode()
            self.logger.debug("Compress repeats value changed: %d." % self.options.compr_cnt)

        def on_btn_sel_geom(widget, data=None):
            try:
                ret = subprocess.check_output(['slop', '-f', '%x %y %w %h'])
            except subprocess.CalledProcessError:
                return False
            except OSError:
                msg = Gtk.MessageDialog(
                    parent  = self,
                    type    = Gtk.MESSAGE_ERROR,
                    buttons = Gtk.BUTTONS_OK,
                    message_format="Error running \"slop\""
                )
                msg.format_secondary_markup(
                    "\"slop\" is required for interactive selection. "
                    "See <a href=\"https://github.com/naelstrof/slop\">"
                    "https://github.com/naelstrof/slop</a>"
                )
                msg.run()
                msg.destroy()
                return False

            self.options.geometry = map(int, ret.split(' '))
            self.update_geometry()
            self.btn_reset_geom.set_sensitive(True)
            return True

        def on_btn_reset_geom(widget, data=None):
            self.options.geometry = None
            if self.options.position == 'fixed':
                self.options.position = 'bottom'
                self.cbox_positions.set_active(POSITIONS.keys().index(self.options.position))
            self.update_geometry()
            widget.set_sensitive(False)

        def on_adj_opacity_changed(widget, data=None):
            self.options.opacity = widget.get_value()
            self.update_colors()

        def on_font_color_changed(widget, data=None):
            self.options.font_color = widget.get_color().to_string()
            self.update_colors()

        def on_bg_color_changed(widget, data=None):
            self.options.bg_color = widget.get_color().to_string()
            self.update_colors()

        def on_btn_font(widget, data=None):
            self.options.font_desc = widget.get_font_name()
            self.font = pango.FontDescription(self.options.font_desc)
            self.update_label()

        frm_main = Gtk.Frame.new(_("Preferences"))
        frm_main.set_border_width(6)

        frm_time = Gtk.Frame.new("<b>%s</b>" % _("Time"))
        frm_time.set_border_width(4)
        frm_time.get_label_widget().set_use_markup(True)
        frm_time.set_shadow_type(Gtk.ShadowType.NONE)

        vbox_time = Gtk.VBox(spacing=6)
        hbox_time = Gtk.HBox()
        lbl_time1 = Gtk.Label(_("Display for"))
        lbl_time2 = Gtk.Label(_("seconds"))
        sb_time = Gtk.SpinButton(digits=1)
        sb_time.set_increments(0.5, 1.0)
        sb_time.set_range(0.5, 10.0)
        sb_time.set_numeric(True)
        sb_time.set_update_policy(Gtk.SpinButtonUpdatePolicy.IF_VALID)
        sb_time.set_value(self.options['timeout'])
        sb_time.connect("value-changed", on_sb_time_changed)

        hbox_time.pack_start(lbl_time1, expand=False, fill=False, padding=6)
        hbox_time.pack_start(sb_time, expand=False, fill=False, padding=4)
        hbox_time.pack_start(lbl_time2, expand=False, fill=False, padding=4)
        vbox_time.pack_start(hbox_time, expand=False, fill=False, padding=0)

        chk_persist = Gtk.CheckButton(_("Persistent window"))
        chk_persist.connect("toggled", on_cbox_persist_changed)
        chk_persist.set_active(self.options['persist'])
        vbox_time.pack_start(chk_persist, expand=False, fill=False, padding=0)

        frm_time.add(vbox_time)
        frm_time.show_all()

        frm_position = Gtk.Frame.new("<b>%s</b>" % _("Position"))
        frm_position.set_border_width(4)
        frm_position.get_label_widget().set_use_markup(True)
        frm_position.set_shadow_type(Gtk.ShadowType.NONE)
        vbox_position = Gtk.VBox(spacing=6)

        lbl_screen = Gtk.Label(_("Screen"))
        screen_model = Gtk.ListStore(str)
        # scr = self.get_screen()
        # for n in range(scr.get_n_monitors()):
        #     screen_model.append([ '%d: %s'%(n, scr.get_monitor_plug_name(n))])

        cbox_screen = Gtk.ComboBox.new_with_model(screen_model)
        cbox_screen.set_active(self.monitor)
        cbox_screen.connect("changed", on_cbox_screen_changed)

        hbox0_position = Gtk.HBox()
        hbox0_position.pack_start(lbl_screen, expand=False, fill=False, padding=6)
        hbox0_position.pack_start(cbox_screen, expand=False, fill=False, padding=4)
        vbox_position.pack_start(hbox0_position, expand=False, fill=False, padding=0)

        lbl_positions = Gtk.Label(_("Position"))
        positions_model = Gtk.ListStore(str)
        # for key, value in enumerate(POSITIONS):
        #     positions_model.append("%s: %s"%(key, value))

        self.cbox_positions = Gtk.ComboBox.new_with_model(positions_model)
        # self.cbox_positions.set_name('position')
        # self.cbox_positions.set_active(POSITIONS.keys().index(self.options.position))
        # self.cbox_positions.connect("changed", on_cbox_position_changed)

        self.btn_reset_geom = Gtk.Button(_("Reset"))
        self.btn_reset_geom.connect("clicked", on_btn_reset_geom)
        self.btn_reset_geom.set_sensitive(self.options['geometry'] is not None)

        hbox1_position = Gtk.HBox()
        hbox1_position.pack_start(lbl_positions, expand=False, fill=False, padding=6)
        hbox1_position.pack_start(self.cbox_positions, expand=False, fill=False, padding=4)
        hbox1_position.pack_start(self.btn_reset_geom, expand=False, fill=False, padding=4)
        vbox_position.pack_start(hbox1_position,  expand=False, fill=False, padding=0)

        btn_sel_geom = Gtk.Button(_("Select window/region"))
        btn_sel_geom.connect("clicked", on_btn_sel_geom)
        vbox_position.pack_start(btn_sel_geom, expand=False, fill=False, padding=0)

        frm_aspect = Gtk.Frame.new("<b>%s</b>" % _("Aspect"))
        frm_aspect.set_border_width(4)
        frm_aspect.get_label_widget().set_use_markup(True)
        frm_aspect.set_shadow_type(Gtk.ShadowType.NONE)
        vbox_aspect = Gtk.VBox(spacing=6)

        frm_position.add(vbox_position)

        hbox0_font = Gtk.HBox()
        lbl_font = Gtk.Label(_("Font"))
        btn_font = Gtk.FontButton(self.options['font_desc'])
        btn_font.set_use_size(False)
        btn_font.set_show_size(False)
        btn_font.connect("font-set", on_btn_font)
        hbox0_font.pack_start(lbl_font, expand=False, fill=False, padding=6)
        hbox0_font.pack_start(btn_font, expand=False, fill=False, padding=4)

        hbox2_aspect = Gtk.HBox()

        lbl_sizes = Gtk.Label(_("Size"))
        size_model = Gtk.ListStore(str)

        # cbox_sizes.set_name('size')

        # for key, value in enumerate(FONT_SIZES):
        #     cbox_sizes.insert_text(key, value)

        # cbox_sizes.set_active(FONT_SIZES.keys().index(self.options.font_size))
        # cbox_sizes.connect("changed", on_cbox_sizes_changed)
        cbox_sizes = Gtk.ComboBox.new_with_model(size_model)

        hbox2_aspect.pack_start(lbl_sizes, expand=False, fill=False, padding=6)
        hbox2_aspect.pack_start(cbox_sizes, expand=False, fill=False, padding=4)

        hbox3_font_color = Gtk.HBox()

        lbl_font_color = Gtk.Label(_("Font color"))
        # btn_font_color = Gtk.ColorButton(color=Gtk.gdk.color_parse(self.options['font_color']))
        # btn_font_color.connect("color-set", on_font_color_changed)
        # btn_bg_color = Gtk.ColorButton(color=Gtk.gdk.color_parse(self.options.bg_color))
        # btn_bg_color.connect("color-set", on_bg_color_changed)

        # hbox3_font_color.pack_start(lbl_font_color, expand=False, fill=False, padding=6)
        # hbox3_font_color.pack_start(btn_font_color, expand=False, fill=False, padding=4)
        # hbox3_font_color.pack_start(btn_bg_color, expand=False, fill=False, padding=4)

        hbox4_aspect = Gtk.HBox()

        lbl_opacity = Gtk.Label(_("Opacity"))
        adj_opacity = Gtk.Adjustment(self.options['opacity'], 0.1, 1.0, 0.1, 0, 0)
        adj_opacity.connect("value-changed", on_adj_opacity_changed)
        adj_scale = Gtk.HScale(adj_opacity)

        hbox4_aspect.pack_start(lbl_opacity, expand=False, fill=False, padding=6)
        hbox4_aspect.pack_start(adj_scale, expand=True, fill=True, padding=4)

        vbox_aspect.pack_start(hbox0_font)
        vbox_aspect.pack_start(hbox2_aspect)
        vbox_aspect.pack_start(hbox3_font_color)
        vbox_aspect.pack_start(hbox4_aspect)

        frm_aspect.add(vbox_aspect)

        frm_kbd = Gtk.Frame("<b>%s</b>" % _("Keys"))
        frm_kbd.set_border_width(4)
        frm_kbd.get_label_widget().set_use_markup(True)
        frm_kbd.set_shadow_type(Gtk.SHADOW_NONE)
        vbox_kbd = Gtk.VBox(spacing=6)

        hbox_kbd = Gtk.HBox()
        lbl_kbd = Gtk.Label(_("Keyboard mode"))
        cbox_modes = Gtk.combo_box_new_text()
        cbox_modes.set_name('mode')
        for key, value in enumerate(KEY_MODES):
            cbox_modes.insert_text(key, value)
        cbox_modes.set_active(KEY_MODES.keys().index(self.options.key_mode))
        cbox_modes.connect("changed", on_cbox_modes_changed)
        hbox_kbd.pack_start(lbl_kbd, expand=False, fill=False, padding=6)
        hbox_kbd.pack_start(cbox_modes, expand=False, fill=False, padding=4)
        vbox_kbd.pack_start(hbox_kbd)

        hbox_kbd = Gtk.HBox()
        lbl_kbd = Gtk.Label(_("Backspace mode"))
        cbox_modes = Gtk.combo_box_new_text()
        for key, value in enumerate(BAK_MODES):
            cbox_modes.insert_text(key, value)
        cbox_modes.set_active(BAK_MODES.keys().index(self.options.bak_mode))
        cbox_modes.connect("changed", on_cbox_bak_changed)
        hbox_kbd.pack_start(lbl_kbd, expand=False, fill=False, padding=6)
        hbox_kbd.pack_start(cbox_modes, expand=False, fill=False, padding=4)
        vbox_kbd.pack_start(hbox_kbd)

        hbox_kbd = Gtk.HBox()
        lbl_kbd = Gtk.Label(_("Modifiers mode"))
        cbox_modes = Gtk.combo_box_new_text()
        for key, value in enumerate(MODS_MODES):
            cbox_modes.insert_text(key, value)
        cbox_modes.set_active(MODS_MODES.keys().index(self.options.mods_mode))
        cbox_modes.connect("changed", on_cbox_mods_changed)
        hbox_kbd.pack_start(lbl_kbd, expand=False, fill=False, padding=6)
        hbox_kbd.pack_start(cbox_modes, expand=False, fill=False, padding=4)
        vbox_kbd.pack_start(hbox_kbd)

        chk_kbd = Gtk.CheckButton(_("Show Modifier sequences only"))
        chk_kbd.connect("toggled", on_cbox_modsonly_changed)
        chk_kbd.set_active(self.options.mods_only)
        vbox_kbd.pack_start(chk_kbd)

        chk_kbd = Gtk.CheckButton(_("Always show Shift"))
        chk_kbd.connect("toggled", on_cbox_visshift_changed)
        chk_kbd.set_active(self.options.vis_shift)
        vbox_kbd.pack_start(chk_kbd)

        chk_vspace = Gtk.CheckButton(_("Show Whitespace characters"))
        chk_vspace.set_active(self.options.vis_space)
        chk_vspace.connect("toggled", on_cbox_visspace_changed)
        vbox_kbd.pack_start(chk_vspace)

        hbox_compr = Gtk.HBox()
        chk_compr = Gtk.CheckButton(_("Compress repeats after"))
        chk_compr.set_active(self.options.compr_cnt > 0)
        chk_compr.connect("toggled", on_cbox_compr_changed)
        self.sb_compr = sb_compr = Gtk.SpinButton(digits=0)
        sb_compr.set_increments(1, 1)
        sb_compr.set_range(1, 100)
        sb_compr.set_numeric(True)
        sb_compr.set_update_policy(Gtk.UPDATE_IF_VALID)
        sb_compr.set_value(self.options.compr_cnt or 3)
        sb_compr.connect("value-changed", on_sb_compr_changed)
        hbox_compr.pack_start(chk_compr, expand=False, fill=False)
        hbox_compr.pack_start(sb_compr, expand=False, fill=False, padding=4)
        vbox_kbd.pack_start(hbox_compr)

        frm_kbd.add(vbox_kbd)

        hbox_main = Gtk.HBox()
        vbox_main = Gtk.VBox()
        vbox_main.pack_start(frm_time, False, False, 6)
        vbox_main.pack_start(frm_position, False, False, 6)
        vbox_main.pack_start(frm_aspect, False, False, 6)
        hbox_main.pack_start(vbox_main)
        vbox_main = Gtk.VBox()
        vbox_main.pack_start(frm_kbd, False, False, 6)
        hbox_main.pack_start(vbox_main)
        frm_main.add(hbox_main)

        prefs.vbox.pack_start(frm_main)
        prefs.set_destroy_with_parent(True)
        prefs.set_resizable(False)
        prefs.set_has_separator(False)
        prefs.set_default_response(Gtk.RESPONSE_CLOSE)
        prefs.vbox.show_all()


    def make_menu(self):
        self.menu = menu = Gtk.Menu()

        show_item = Gtk.CheckMenuItem(_("Show keys"))
        show_item.set_active(True)
        show_item.connect("toggled", self.on_show_keys)
        show_item.show()
        menu.append(show_item)

        preferences_item = Gtk.ImageMenuItem(Gtk.STOCK_PREFERENCES)
        preferences_item.connect("activate", self.on_preferences_dialog)
        preferences_item.show()
        menu.append(preferences_item)

        about_item = Gtk.ImageMenuItem(Gtk.STOCK_ABOUT)
        about_item.connect("activate", self.on_about_dialog)
        about_item.show()
        menu.append(about_item)

        separator_item = Gtk.SeparatorMenuItem()
        separator_item.show()
        menu.append(separator_item)

        image = Gtk.ImageMenuItem(Gtk.STOCK_QUIT)
        image.connect("activate", self.quit)
        image.show()
        menu.append(image)
        menu.show()


    def make_systray(self):
        try:
            import appindicator
            self.systray = appindicator.Indicator(
                APP_NAME, 'indicator-messages', appindicator.CATEGORY_APPLICATION_STATUS)
            self.systray.set_status(appindicator.STATUS_ACTIVE)
            self.systray.set_attention_icon("indicator-messages-new")
            self.systray.set_icon("preferences-desktop-keyboard-shortcuts")
            self.systray.set_menu(self.menu)
            self.logger.debug("Using AppIndicator.")
        except ImportError:
            self.systray = Gtk.StatusIcon()
            self.systray.set_from_icon_name("preferences-desktop-keyboard-shortcuts")
            self.systray.connect("popup-menu", self.on_statusicon_popup, self.menu)
            self.logger.debug("Using StatusIcon.")


    def make_about_dialog(self):
        about = Gtk.AboutDialog()
        about.set_program_name(APP_NAME)
        about.set_version(VERSION)
        about.set_copyright("""
        Copyright(c) 2010-2012: Pablo Seminario <pabluk@gmail.com>
        Copyright(c) 2015-2016: wave++ "Yuri D'Elia" <wavexx@thregr.org>
        """)
        about.set_comments(APP_DESC)
        about.set_documenters(
            ["José María Quiroga <pepelandia@gmail.com>"]
        )
        about.set_website(APP_URL)
        about.set_icon_name('preferences-desktop-keyboard-shortcuts')
        about.set_logo_icon_name('preferences-desktop-keyboard-shortcuts')
        about.connect("response", about.hide_on_delete)
        about.connect("delete-event", about.hide_on_delete)


    def on_about_dialog(self, widget, data=None):
        self.about.show()



def run():
    Gtk.main()

# if __name__ == '__main__':
#     run()
