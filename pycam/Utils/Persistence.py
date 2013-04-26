import os
import yaml
import pycam.Utils.log

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

    def get_config_dirname(self):
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
                    "OS error(%d): %s" % (config_dir, e.errno, e.strerror))
        return config_dir

    def get_config_filename(self, filename=None):
        if filename is None:
            filename = self.CONFIG_FILENAME

        config_dir = self.get_config_dirname()
        return os.path.join(config_dir, filename)

    def load_preferences_file(self):
        """
        Load the preferences file into a generic data structure for
        consumption by the StatusManager plugin
        """
        # get config filename
        config_filename = self.get_config_filename()

        # read prefs from config file
        try:
            config_file = open(config_filename, "r")
            serialized_data = config_file.read()
            config_file.close()
            self.log.debug("Read configuration file '%s'" %
                           config_filename)
        except IOError as e:
            raise PersistenceException(
                "Failed to read preferences file '%s': IO error(%d):  %s" %
                    (config_filename, e.errno, e.strerror))

        # return prefs structure from YAML format
        return yaml.safe_load(serialized_data)

    def save_preferences_file(self, prefs):
        """
        Save the preferences file from a generic data structure
        provided by the StatusManager plugin
        """
        # get config filename
        config_filename = self.get_config_filename()

        # serialize prefs into YAML format
        # add a comment at the beginning (with emacs mode id)
        comment = '# PyCAM preferences file' + ' '*56 + '-*-yaml-*-'
        serialized_prefs = comment + \
            yaml.safe_dump(prefs,
                           default_flow_style=False,
                           indent=4)

        # save prefs into config file
        try:
            config_file = open(config_filename, "w")
            config_file.write(serialized_prefs)
            config_file.close()
            self.log.debug("Saved configuration file '%s'" %
                           config_filename)
        except IOError, e:
            raise PersistenceException(
                "Failed to write preferences file '%s': IO error(%d) :  %s" %
                (config_filename, e.errno, e.strerror))
