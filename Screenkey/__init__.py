#!/usr/bin/env python3

import gettext
gettext.install('screenkey')
_ = gettext.gettext

APP_NAME = "Screenkey"
APP_DESC = _("Screencast your keys")
APP_URL  = 'http://www.thregr.org/~wavexx/software/screenkey/'
VERSION  = '0.9'

# CLI/Interface options
POSITIONS = {
    'top': _('Top'),
    'center': _('Center'),
    'bottom': _('Bottom'),
    'fixed': _('Fixed'),
}

KEY_MODES = {
    'composed': _('Composed'),
    'translated': _('Translated'),
    'keysyms': _('Keysyms'),
    'raw': _('Raw'),
}

BAK_MODES = {
    'normal': _('Normal'),
    'baked': _('Baked'),
    'full': _('Full'),
}

MODS_MODES = {
    'normal': _('Normal'),
    'emacs': _('Emacs'),
    'mac': _('Mac'),
}
