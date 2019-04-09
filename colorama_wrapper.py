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

# roygbiv-ish
FG_RAINBOW = [Fore.LIGHTRED_EX, Fore.RED, Fore.LIGHTYELLOW_EX,
              Fore.LIGHTGREEN_EX, Fore.LIGHTCYAN_EX, Fore.BLUE,
              Fore.MAGENTA]
BG_RAINBOW = [Back.LIGHTRED_EX, Back.RED, Back.LIGHTYELLOW_EX,
              Back.LIGHTGREEN_EX, Back.LIGHTCYAN_EX, Back.BLUE,
              Back.MAGENTA]
