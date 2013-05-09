import os
import yaml
import pycam.Utils.log

MODEL_FILENAME_FILTER = (
    ("All supported model filetypes",
     ("*.stl", "*.dxf", "*.svg", "*.eps", "*.ps")),
    ("STL models", "*.stl"),
    ("DXF contours", "*.dxf"),
    ("SVG contours", "*.svg"),
    ("PS contours", ("*.eps", "*.ps")),
    )

class PersistenceException(Exception):
    """
    Exception class for the Persistence module
    """
    pass

class Persistence(object):
    """
    The Persistence class is responsible for storing and retrieving
    GUI settings and task settings.
    """

    # config settings directory name (prepend with '.' in unix)
    CONFIG_DIR = "pycam"
    CONFIG_FILENAME = "preferences.conf"

    log = pycam.Utils.log.get_logger()

    def get_preferences_dirname(self):
        try:
            from win32com.shell import shellcon, shell            
            homedir = shell.SHGetFolderPath(0, shellcon.CSIDL_APPDATA, 0, 0)
            config_dir = os.path.join(homedir, self.CONFIG_DIR)
        except ImportError:
            # quick semi-nasty fallback for non-windows/win32com case
            homedir = os.path.expanduser("~")
            # hide the config directory for unixes
            config_dir = os.path.join(homedir, "." + self.CONFIG_DIR)
        if not os.path.isdir(config_dir):
            try:
                os.makedirs(config_dir)
            except OSError as e:
                raise PersistenceException(
                    "Failed to create configuration directory '%s': "
                    "[Errno %d %s" % (config_dir, e.errno, e.strerror))
        return config_dir

    def get_preferences_filename(self, filename=None):
        if filename is None:
            filename = self.CONFIG_FILENAME

        config_dir = self.get_preferences_dirname()
        return os.path.join(config_dir, filename)

    def load_file(self,filename):
        """
        Load a file, returning its contents as a string
        """
        try:
            fileobj = open(filename, "r")
            file_contents = fileobj.read()
            fileobj.close()
        except IOError as e:
            raise PersistenceException("[Errno %d] %s" % (e.errno, e.strerror))

        return file_contents


    def save_file(self, filename, file_contents):
        """
        Save file_contents to filename
        """
        try:
            file_obj = open(filename, "w")
            file_obj.write(file_contents)
            file_obj.close()
        except IOError, e:
            raise PersistenceException("[Errno %d] %s" % (e.errno, e.strerror))


    def unserialize_data(self, serialized_data):
        """
        Given a generic python data structure, serialize with YAML
        """
        return yaml.safe_load(serialized_data)


    def serialize_data(self, data, comment=''):
        """
        Given a generic python data structure, serialize with YAML
        """
        return (comment + 
                yaml.safe_dump(data, default_flow_style=False, indent=4)
                )


    def load_data_file(self, filename):
        """
        Read data from file, unserialize, and return
        """
        # Read data from file
        file_contents = self.load_file(filename)

        # Return prefs structure from YAML format
        return self.unserialize_data(file_contents)


    def save_data_file(self, filename, data, comment=''):
        """
        Serialize data and store to a file with optional comment
        """
        # Serialize data into YAML format
        serialized_data = self.serialize_data(data, comment=comment)

        # Save prefs into preferences file
        self.save_file(filename, serialized_data)


    def load_preferences_file(self):
        """
        Load the preferences file into a generic data structure for
        consumption by the StatusManager plugin
        """
        # Get preferences filename
        try:
            preferences_filename = self.get_preferences_filename()
            self.log.debug("Saved preferences file '%s'" % preferences_filename)
        except IOError, e:
            # Failed to write file; inform user
            self.log.error("Failed to write preferences file '%s': %s" %
                (preferences_filename, e.msg))

        # Read prefs from preferences file
        try:
            prefs = self.load_data_file(preferences_filename)
            self.log.debug("Loaded preferences file '%s'" %
                           preferences_filename)
        except PersistenceException as e:
            # Failed to create prefs dir; inform user
            self.log.error(e.msg)
            return

        return prefs

    def save_preferences_file(self, prefs):
        """
        Save the preferences file from a generic data structure
        provided by the StatusManager plugin
        """
        # Get preferences filename
        try:
            preferences_filename = self.get_preferences_filename()
        except PersistenceException, e:
            # Failed to create prefs dir; inform user
            self.log.error(e.msg)
            return

        # Initial comment at the beginning (with emacs mode id)
        comment = '# PyCAM preferences file' + ' '*45 + '-*-yaml-*-\n'

        # Save prefs into preferences file
        try:
            self.save_data_file(preferences_filename, prefs, comment=comment)
            self.log.debug("Saved preferences file '%s'" % preferences_filename)
        except IOError, e:
            # Failed to write file; inform user
            self.log.error("Failed to write preferences file '%s': %s" %
                (preferences_filename, e.msg))
