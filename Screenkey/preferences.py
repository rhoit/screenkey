#!/usr/bin/env python3

import os

import gi
gi.require_version('Gtk', '3.0')

from gi.repository import Gtk, Gdk

import gettext
gettext.install('screenkey')
_ = gettext.gettext

options = {
    'bak_mode'   : 'baked',
    'bg_color'   : "000000FF",
    'compr_cnt'  : 3,
    'font_color' : "FFFF00FF",
    'font_desc'  : 'Sans Bold',
    'font_size'  : 12,
    'geometry'   : None,
    'ignore'     : [],
    'key_mode'   : 'composed',
    'mods_mode'  : 'normal',
    'mods_only'  : False,
    'multiline'  : False,
    'no_systray' : False,
    'opacity'    : 0.8,
    'persist'    : False,
    'position'   : 'bottom',
    'screen'     : 0,
    'timeout'    : 2.5,
    'vis_shift'  : False,
    'vis_space'  : True,
}


class Preferences(Gtk.Window):
    __instance__ = None

    def __new__(cls, *args, **kargs):
        """Override the __new__ method to make singleton"""
        if cls.__instance__ is None:
            cls.__instance__ = Gtk.Window.__new__(cls)
            cls.__instance__.singleton_init(*args, **kargs)
        return cls.__instance__


    def singleton_init(self, cnf):
        Gtk.Window.__init__(self, title="Preferences")

        self.cnf = cnf

        self.set_border_width(10)
        self.makeWidgets()

        # self.connect("response", self.on_preferences_changed)
        # self.connect("delete-event", self.on_preferences_changed)
        self.connect('key_release_event', self.on_key_release)
        self.connect('delete-event', lambda *a: self.on_destroy(*a))

        self.set_position(Gtk.WindowPosition.CENTER)
        # self.set_default_size(250, 200)



    def makeWidgets(self):
        layout = Gtk.Grid()
        self.add(layout)
        layout.set_row_spacing(5)
        layout.set_column_spacing(5)

        self.notebook = Gtk.Notebook()
        layout.attach(self.notebook, left=0, top=0, width=2, height=2)

        # self.notebook.append_page(self.makeWidget_plugins(), Gtk.Label(label="Plugins"))
        # self.notebook.append_page(self.makeWidget_gloss(), Gtk.Label(label="Gloss"))
        self.notebook.append_page(self.makeWidget_system(), Gtk.Label(label="Fonts"))
        # self.notebook.append_page(self.makeWidget_search(), Gtk.Label(label="Search"))

        layout.attach(self.makeWidget_buttons(), left=0, top=4, width=2, height=1)


    def makeWidget_system(self):
        layout = Gtk.Grid()

        chk_persist = Gtk.CheckButton(_("Persistent window"))
        chk_persist.set_active(self.cnf['persist'])
        chk_persist.connect("toggled", self.on_cbox_persist_changed)

        label = Gtk.Label(_("Timeout"))

        sb = Gtk.SpinButton(digits=1)
        sb.set_increments(0.5, 1.0)
        sb.set_range(0.5, 10.0)
        sb.set_numeric(True)
        sb.set_update_policy(Gtk.SpinButtonUpdatePolicy.IF_VALID)
        sb.set_value(self.cnf['timeout'])
        sb.connect("value-changed", self.on_sb_time_changed)

        label = Gtk.Label(_("seconds"))

        label = Gtk.Label(_("Screen"))
        model = Gtk.ListStore(str)
        # scr = self.get_screen()
        # for n in range(scr.get_n_monitors()):
        #     model.append([ '%d: %s'%(n, scr.get_monitor_plug_name(n))])

        cbox = Gtk.ComboBox.new_with_model(model)
        # cbox.set_active(self.monitor)
        cbox.connect("changed", self.on_cbox_screen_changed)

        label = Gtk.Label(_("Position"))
        model = Gtk.ListStore(str)
        # for key, value in enumerate(POSITIONS):
        #     model.append("%s: %s"%(key, value))
        return layout


    def makeWidget_theme(self):
        layout = Gtk.Grid()

        label = Gtk.Label()
        layout.attach(label, left=0, top=1, width=1, height=1)
        label.set_markup("<b>Font</b>")

        self.font_button = Gtk.FontButton()
        layout.attach(self.font_button, left=1, top=1, width=1, height=1)
        # self.font_button.set_font_name(self.cnf['font_name'])
        # self.font_button.connect('font-set', self._change_font)
        # self.font_button.connect("font-set", self.on_btn_font)

        label = Gtk.Label(_("Background"))
        # bg_button = Gtk.ColorButton()
        # bg_button.set(self.options['background']))
        # bg_button.connect("color-set", on_font_color_changed)

        label = Gtk.Label(_("Foreground"))
        # fg_button = Gtk.ColorButton()
        # fg_button.set(self.options['foreground']))
        # fg_button.connect("color-set", on_bg_color_changed)

        label = Gtk.Label(_("Opacity"))
        opacity = Gtk.Adjustment(
            self.options['opacity'],
            0.1,
            1.0,
            0.1,
            0,
            0
        )
        opacity.connect("value-changed", on_adj_opacity_changed)
        adj_scale = Gtk.HScale(adj_opacity)
        return layout


    def makeWidget_modes(self):
        layout = Gtk.VBox()

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
        return layout


    def _change_font(self, widget):
        f_obj = widget.get_font_desc()
        # TODO: change in css to apply fonts


    def _chooser_changed(self, appchooserbutton):
        i = appchooserbutton.get_active()
        appchooserbutton.selected_item = i


    def makeWidget_buttons(self):
        layout = Gtk.HBox()
        # layout.set_row_spacing(5)
        # layout.set_column_spacing(5)


        self.b_cancel = Gtk.Button.new_with_mnemonic("_Cancel")
        layout.add(self.b_cancel)
        self.b_cancel.connect("clicked", lambda *a: self.on_destroy(*a))

        self.b_apply = Gtk.Button.new_with_mnemonic("_Apply")
        layout.add(self.b_apply)
        self.b_apply.connect("clicked", lambda *a: self.on_destroy(*a))

        self.b_ok = Gtk.Button.new_with_mnemonic("_Refresh")
        layout.add(self.b_ok)

        return layout


    def makeWidget_settings(self):
        layout = Gtk.HBox()

        self.font_button = Gtk.FontButton()
        layout.add(self.font_button)
        self.font_button.set_font_name(def_FONT)
        self.font_button.connect('font-set', self._change_font)

        return layout


    def _apply_click(self, widget):
        pass
        # f_obj = widget.get_font_desc()
        # self.viewer.textview.modify_font(f_obj)
        # ff, fs = f_obj.get_family(), int(f_obj.get_size()/1000)
        # font = ff + ' ' + str(fs)

        # conf = open("mysettings.conf").read()
        # global def_FONT
        # nconf = conf.replace(def_FONT, font)
        # open("mysettings.conf", 'w').write(nconf)
        # def_FONT = font


    def cb_file_add(self):
        for obj in self.parent.TAB_LST:
            *a, label = obj.SRC.split('/')
            self.gloss_file.append_text(label)

            self.gloss_file.set_active(self.parent.notebook.get_current_page())


    def _add_button(self, widget=None):
        pass


    def on_destroy(self, event, *args):
        """Override the default handler for the delete-event signal"""
        self.hide()
        return True


    def on_sb_time_changed(self, widget):
        self.options.timeout = widget.get_value()
        self.logger.debug("Timeout value changed: %f." % self.options.timeout)


    def on_cbox_sizes_changed(self, widget):
        index = widget.get_active()
        self.options.font_size = FONT_SIZES.keys()[index]
        self.update_geometry()
        self.logger.debug("Window size changed: %s." % self.options.font_size)


    def on_cbox_modes_changed(self, widget):
        index = widget.get_active()
        self.options.key_mode = KEY_MODES.keys()[index]
        self.on_change_mode()
        self.logger.debug("Key mode changed: %s." % self.options.key_mode)


    def on_cbox_bak_changed(self, widget):
        index = widget.get_active()
        self.options.bak_mode = BAK_MODES.keys()[index]
        self.on_change_mode()
        self.logger.debug("Bak mode changed: %s." % self.options.bak_mode)


    def on_cbox_mods_changed(self, widget):
        index = widget.get_active()
        self.options.mods_mode = MODS_MODES.keys()[index]
        self.on_change_mode()
        self.logger.debug("Mods mode changed: %s." % self.options.mods_mode)


    def on_cbox_modsonly_changed(self, widget):
        self.options.mods_only = widget.get_active()
        self.on_change_mode()
        self.logger.debug("Modifiers only changed: %s." % self.options.mods_only)


    def on_cbox_visshift_changed(self, widget):
        self.options.vis_shift = widget.get_active()
        self.on_change_mode()
        self.logger.debug("Visible Shift changed: %s." % self.options.vis_shift)


    def on_cbox_visspace_changed(self, widget):
        self.options.vis_space = widget.get_active()
        self.on_change_mode()
        self.logger.debug("Show Whitespace changed: %s." % self.options.vis_space)


    def on_cbox_position_changed(self, widget):
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


    def on_cbox_screen_changed(self, widget):
        self.options.screen = widget.get_active()
        self.set_active_monitor(self.options.screen)
        self.logger.debug("Screen changed: %d." % self.options.screen)


    def on_cbox_persist_changed(self, widget):
        self.options.persist = widget.get_active()
        if not self.get_property('visible'):
            self.show()
        else:
            self.on_label_change(self.label.get_text())
        self.logger.debug("Persistent changed: %s." % self.options.persist)


    def on_sb_compr_changed(self, widget):
        self.options.compr_cnt = widget.get_value_as_int()
        self.on_change_mode()
        self.logger.debug("Compress repeats value changed: %d." % self.options.compr_cnt)


    def on_cbox_compr_changed(self, widget):
        compr_enabled = widget.get_active()
        self.sb_compr.set_sensitive(compr_enabled)
        self.options.compr_cnt = self.sb_compr.get_value_as_int() if compr_enabled else 0
        self.on_change_mode()
        self.logger.debug("Compress repeats value changed: %d." % self.options.compr_cnt)


    def on_btn_sel_geom(self, widget):
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


    def on_btn_reset_geom(self, widget):
        self.options.geometry = None
        if self.options.position == 'fixed':
            self.options.position = 'bottom'
            self.cbox_positions.set_active(POSITIONS.keys().index(self.options.position))
        self.update_geometry()
        widget.set_sensitive(False)


    def on_adj_opacity_changed(self, widget):
        self.options.opacity = widget.get_value()
        self.update_colors()


    def on_font_color_changed(self, widget):
        self.options.font_color = widget.get_color().to_string()
        self.update_colors()


    def on_bg_color_changed(self, widget):
        self.options.bg_color = widget.get_color().to_string()
        self.update_colors()


    def on_btn_font(self, widget):
        self.options.font_desc = widget.get_font_name()
        self.font = pango.FontDescription(self.options.font_desc)
        self.update_label()


    def on_key_release(self, widget, event):
        if event.keyval == 65307:  self.hide()
        elif Gdk.ModifierType.MOD1_MASK & event.state:
            if ord('1') <= event.keyval <= ord('9'):
                self.notebook.set_current_page(event.keyval - ord('1'))

    def on_preferences_changed(self, widget=None):
        self.store_state(self.cnf)
        self.prefs.hide()
        return True



def main(cnf):
    win = Settings(cnf)
    win.set_position(Gtk.WindowPosition.CENTER)
    win.show_all()
    return win


def sample():
    import sys
    sys.path.append(sys.path[0]+'/../')

    root = Preferences(options)
    root.show_all()
    # in isolation testing, make Esc quit Gtk mainloop
    root.hide = Gtk.main_quit


if __name__ == '__main__':
    sample()
    Gtk.main()
