try:
    from colorama import Fore, Back, Style
    COLOUR_AVAILABLE = True
except ImportError:
    COLOUR_AVAILABLE = False
    class Dummy(object):
        def __getattribute__(self, name):
            return ''
    Fore = Back = Style = Dummy()

COLORAMA_RESET = Fore.RESET + Back.RESET + Style.RESET_ALL

