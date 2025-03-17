from enum import Enum

class TerminalColor(Enum):
    BLUE = '\033[34m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    GREEN_BOLD = '\033[1;32m'
    CLEAR_LINE = '\033[2K'
    MOVE_TO_LAST_LINE = '\033[1A'
    YELLOW = '\033[33m'
    GRAY = '\033[90m'
    GRAY_ITALIC = '\033[90;3m'
    RESET = '\033[0m'
    CYAN = '\033[36m'

