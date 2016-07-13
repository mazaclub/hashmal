import logging
import time

from hashmal_lib.core import chainparams
from config import Config
from downloader import DownloadController
from plugin_handler import PluginHandler

class HashmalPlatform(object):
    """Hashmal internal state, plugin support, etc."""
    def __init__(self, main_window):
        # Whether unit tests are running.
        self.testing_mode = False

        self.main_window = main_window
        self.config = self.main_window.config = Config()
        self.init_logger()

        self.download_controller = DownloadController(self.config)

        # Plugin Handler loads plugins and handles their dock widgets.
        self.plugin_handler = PluginHandler(self)

    def set_testing_mode(self, is_testing):
        """Set whether unit tests are being run."""
        self.testing_mode = is_testing

    def init_plugins(self):
        """Initialize chainparams and plugins."""
        active_params = self.config.get_option('chainparams', 'Bitcoin')
        # True if chainparams needs to be set after plugins load.
        needs_params_change = False
        # An exception is thrown if the last-active chainparams preset
        # only exists due to a plugin that defines it.
        try:
            chainparams.set_to_preset(active_params)
        except KeyError:
            chainparams.set_to_preset('Bitcoin')
            needs_params_change = True

        self.plugin_handler.load_plugins()

        # Attempt to load chainparams preset again if necessary.
        if needs_params_change:
            try:
                chainparams.set_to_preset(active_params)
                self.config.optionChanged.emit('chainparams')
            except KeyError:
                self.log_message('Core', 'Chainparams preset "%s" does not exist. Setting chainparams to Bitcoin.' % active_params, logging.ERROR)
                self.config.set_option('chainparams', 'Bitcoin')

    def init_logger(self):
        """Initialize logger."""
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', '%Y-%m-%d %H:%M:%S')
        handler.setFormatter(formatter)
        logger = logging.getLogger()
        logger.addHandler(handler)
        self.change_log_level(self.config.get_option('log_level', 'INFO'))

    def change_log_level(self, level_str):
        level_str = level_str.upper()
        if level_str not in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']:
            level_str = 'INFO'
        level = getattr(logging, level_str)
        logging.getLogger().setLevel(level)

    def log_message(self, plugin_name, msg, level):
        if self.testing_mode:
            return
        message = '[%s] -> %s' % (plugin_name, msg)
        logging.log(level, message)
        self.main_window.show_status_message(message, True if level == logging.ERROR else False)
        log_plugin = self.plugin_handler.get_plugin('Log')
        if log_plugin:
            log_plugin.ui.add_log_message(time.time(), level, plugin_name, msg)

    def on_option_changed(self, key):
        if key == 'log_level':
            self.change_log_level(self.config.get_option('log_level', 'INFO'))
