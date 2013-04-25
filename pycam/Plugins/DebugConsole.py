# FIXME gtk needs to go into PluginBase class; see StatusManager.py
import gtk
import code
import pycam.Plugins
from pycam.Utils.locations import get_ui_file_location

class DebugConsole(pycam.Plugins.PluginBase):

    CATEGORIES = ["System"]
    UI_FILE = "debug_console.ui"
    GTKMENU_FILE = 'debug_console_ui.xml'

    def setup(self):
        if self.gui:
            item = self.gui.get_object("StartDebugConsole")
            action = 'activate'
            item.connect(action, self.start_debug_console)
            actiongroup = gtk.ActionGroup('debug_console')
            actiongroup.add_action(item)

            uimanager = self.core.get("gtk-uimanager")
            uimanager.insert_action_group(actiongroup, pos=-1)

            gtkmenu_file = get_ui_file_location(self.GTKMENU_FILE)
            self.ui_merge_menus = uimanager.add_ui_from_file(gtkmenu_file)


    def start_debug_console(self, widget=None):
        # list of variables available in the debug shell
        local_vars = {'__name__' : '__console__',
                      '__doc__' : None,
                      'core' : self.core}
        console = code.InteractiveConsole(local_vars)
        console.interact('PyCAM interactive shell\n'
                         'EventCore object is available as "core"\n'
                         'Press Ctrl-D to exit'
                         )
