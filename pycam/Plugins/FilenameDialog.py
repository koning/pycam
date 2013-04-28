# -*- coding: utf-8 -*-
"""
$Id$

Copyright 2011 Lars Kruse <devel@sumpfralle.de>

This file is part of PyCAM.

PyCAM is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

PyCAM is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with PyCAM.  If not, see <http://www.gnu.org/licenses/>.
"""

import os
import gtk

import pycam.Plugins
import pycam.Utils
from pycam.Utils.Persistence import MODEL_FILENAME_FILTER
from pycam.Utils.locations import get_ui_file_location
from pycam.Utils import URIHandler


def _get_filters_from_list(filter_list):
    import gtk
    result = []
    for one_filter in filter_list:
        current_filter = gtk.FileFilter()
        current_filter.set_name(one_filter[0])
        file_extensions = one_filter[1]
        if not isinstance(file_extensions, (list, tuple)):
            file_extensions = [file_extensions]
        for ext in file_extensions:
            current_filter.add_pattern(
                    pycam.Utils.get_case_insensitive_file_pattern(ext))
        result.append(current_filter)
    return result

def _get_filename_with_suffix(filename, type_filter):
    # use the first extension provided by the filter as the default
    if isinstance(type_filter[0], (tuple, list)):
        filter_ext = type_filter[0][1]
    else:
        filter_ext = type_filter[1]
    if isinstance(filter_ext, (list, tuple)):
        filter_ext = filter_ext[0]
    if not filter_ext.startswith("*"):
        # weird filter content
        return filename
    else:
        filter_ext = filter_ext[1:]
    basename = os.path.basename(filename)
    if (basename.rfind(".") == -1) or (basename[-6:].rfind(".") == -1):
        # The filename does not contain a dot or the dot is not within the
        # last five characters. Dots within the start of the filename are
        # ignored.
        return filename + filter_ext
    else:
        # contains at least one dot
        return filename


class RecentManager(pycam.Plugins.PluginBase):
    UI_FILE = "recent_model_builder.xml"
    GTKMENU_FILE = "recent_model_ui.xml"
    CATEGORIES = [ 'System' ]
    CORE_METHODS = [ 'add_to_recent_file_list' ]

    def setup(self):
        if self.gui:
            # initialize the RecentManager (TODO: check for Windows)
            if False and pycam.Utils.get_platform() == \
                    pycam.Utils.PLATFORM_WINDOWS:
                # The pyinstaller binary for Windows fails mysteriously
                # when trying to display the stock item.
                #
                # Error message:
                #   Gtk:ERROR:gtkrecentmanager.c:1942:get_icon_fallback:
                #   assertion failed: (retval != NULL)
                self.recent_manager = None
            else:
                try:
                    self.recent_manager = gtk.recent_manager_get_default()
                except AttributeError:
                    # GTK 2.12.1 seems to have problems with
                    # "RecentManager" on Windows. Sadly this is the
                    # version, that is shipped with the "appunti" GTK
                    # packages for Windows (April 2010).  see
                    # http://www.daa.com.au/pipermail/pygtk/2009-May/017052.html
                    self.recent_manager = None

            uimanager = self.core.get("gtk-uimanager")
            gtkmenu_file = get_ui_file_location(self.GTKMENU_FILE)
            self.log.debug('gtkmenu_file:  %s' % gtkmenu_file)
            self.ui_merge_id = uimanager.add_ui_from_file(gtkmenu_file)


            # the "recent files" sub-menu
            if self.recent_manager is not None:
                recent_files_menu = gtk.RecentChooserMenu(self.recent_manager)
                recent_files_menu.set_name("RecentFilesMenu")
                recent_menu_filter = gtk.RecentFilter()
                case_converter = pycam.Utils.get_case_insensitive_file_pattern
                for filter_name, patterns in MODEL_FILENAME_FILTER:
                    if not isinstance(patterns, (list, set, tuple)):
                        patterns = [patterns]
                    # convert it into a mutable list (instead of set/tuple)
                    patterns = list(patterns)
                    for index in range(len(patterns)):
                        patterns[index] = case_converter(patterns[index])
                    for pattern in patterns:
                        recent_menu_filter.add_pattern(pattern)
                recent_files_menu.add_filter(recent_menu_filter)
                recent_files_menu.set_show_numbers(True)
                # non-local files (without "file://") are not supported. yet
                recent_files_menu.set_local_only(False)
                # most recent files to the top
                recent_files_menu.set_sort_type(gtk.RECENT_SORT_MRU)
                # show only ten files
                recent_files_menu.set_limit(10)


                # uimanager.get_widget(
                #     "/MenuBar/FileMenu/OpenRecentModelMenu")\
                #     .set_submenu(recent_files_menu)
                # recent_files_menu.connect("item-activated",
                #         self.load_recent_model_file)
            else:
                self.gui.get_object("OpenRecentModel").set_visible(False)


            self.core.register_event("notify-file-saved",
                                     self.add_to_recent_file_list)
            self.core.register_event("notify-file-opened",
                                     self.add_to_recent_file_list)

        self.register_core_methods()

    def teardown(self):
        if self.gui:
            self.core.get("gtk-uimanager").remove_ui(self.ui_merge_id)
            self.core.unregister_event("notify-file-saved",
                                       self.add_to_recent_file_list)
            self.core.unregister_event("notify-file-opened",
                                       self.add_to_recent_file_list)
        self.unregister_core_methods()

    def add_to_recent_file_list(self, filename):
        # Add the item to the recent files list - if it already exists.
        # Otherwise it will be added later after writing the file.
        uri = pycam.Utils.URIHandler(filename)
        if uri.exists():
            # skip this, if the recent manager is not available
            # (e.g. GTK 2.12.1 on Windows)
            if self.recent_manager:
                if self.recent_manager.has_item(uri.get_url()):
                    try:
                        self.recent_manager.remove_item(uri.get_url())
                    except gobject.GError:
                        pass
                self.recent_manager.add_item(uri.get_url())
            # store the directory of the last loaded file
            if uri.is_local():
                self.last_dirname = os.path.dirname(uri.get_local_path())



class FilenameDialog(pycam.Plugins.PluginBase):

    CATEGORIES = ["System"]
    CORE_METHODS = ['get_filename']

    def setup(self):
        import gtk
        self._gtk = gtk
        self.last_dirname = None
        self.register_core_methods()
        return True



    def teardown(self):
        self.unregister_core_methods()

    def get_filename(self, title="Choose file ...", mode_load=False,
                     type_filter=None, filename_templates=None,
                     filename_extension=None, parent=None, extra_widget=None):
        gtk = self._gtk
        if parent is None:
            parent = self.core.get("main_window")
        # we open a dialog
        if mode_load:
            action = gtk.FILE_CHOOSER_ACTION_OPEN
            stock_id_ok = gtk.STOCK_OPEN
        else:
            action = gtk.FILE_CHOOSER_ACTION_SAVE
            stock_id_ok = gtk.STOCK_SAVE
        dialog = gtk.FileChooserDialog(title=title,
                parent=parent, action=action,
                buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                    stock_id_ok, gtk.RESPONSE_OK))
        # set the initial directory to the last one used
        if self.last_dirname and os.path.isdir(self.last_dirname):
            dialog.set_current_folder(self.last_dirname)
        # add extra parts
        if extra_widget:
            extra_widget.show_all()
            dialog.get_content_area().pack_start(extra_widget, expand=False)
        # add filter for files
        if type_filter:
            for file_filter in _get_filters_from_list(type_filter):
                dialog.add_filter(file_filter)
        # guess the export filename based on the model's filename
        valid_templates = []
        if filename_templates:
            if not isinstance(filename_templates, (list,tuple)):
                filename_templates = [filename_templates]
            for template in filename_templates:
                if not template:
                    continue
                if hasattr(template, "get_path"):
                    valid_templates.append(template.get_path())
                else:
                    valid_templates.append(template)
        if valid_templates:
            filename_template = valid_templates[0]
            # remove the extension
            default_filename = os.path.splitext(filename_template)[0]
            if filename_extension:
                default_filename += os.path.extsep + filename_extension
            elif type_filter:
                for one_type in type_filter:
                    extension = one_type[1]
                    if isinstance(extension, (list, tuple, set)):
                        extension = extension[0]
                    # use only the extension of the type filter string
                    extension = os.path.splitext(extension)[1]
                    if extension:
                        default_filename += extension
                        # finish the loop
                        break
            dialog.select_filename(default_filename)
            try:
                dialog.set_current_name(
                        os.path.basename(default_filename).encode("utf-8"))
            except UnicodeError:
                # ignore
                pass
        # add filter for all files
        ext_filter = gtk.FileFilter()
        ext_filter.set_name("All files")
        ext_filter.add_pattern("*")
        dialog.add_filter(ext_filter)
        done = False
        while not done:
            dialog.set_filter(dialog.list_filters()[0])
            response = dialog.run()
            filename = dialog.get_filename()
            uri = pycam.Utils.URIHandler(filename)
            dialog.hide()
            if response != gtk.RESPONSE_OK:
                dialog.destroy()
                return None
            if not mode_load and filename:
                # check if we want to add a default suffix
                filename = _get_filename_with_suffix(filename, type_filter)
            if not mode_load and os.path.exists(filename):
                overwrite_window = gtk.MessageDialog(parent, type=gtk.MESSAGE_WARNING,
                        buttons=gtk.BUTTONS_YES_NO,
                        message_format="This file exists. Do you want to overwrite it?")
                overwrite_window.set_title("Confirm overwriting existing file")
                response = overwrite_window.run()
                overwrite_window.destroy()
                done = (response == gtk.RESPONSE_YES)
            elif mode_load and not uri.exists():
                not_found_window = gtk.MessageDialog(parent, type=gtk.MESSAGE_ERROR,
                        buttons=gtk.BUTTONS_OK,
                        message_format="This file does not exist. Please choose a different filename.")
                not_found_window.set_title("Invalid filename selected")
                response = not_found_window.run()
                not_found_window.destroy()
                done = False
            else:
                done = True
        if extra_widget:
            extra_widget.unparent()
        dialog.destroy()
        # add the file to the list of recently used ones
        if filename:
            if mode_load:
                self.core.emit_event("notify-file-opened", filename)
            else:
                self.core.emit_event("notify-file-saved", filename)
        return filename

