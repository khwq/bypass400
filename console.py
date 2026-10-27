from datetime import datetime
import shutil

class Console:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    CYAN = "\033[36m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    RED = "\033[31m"
    MAGENTA = "\033[35m"
    BLUE = "\033[34m"
    WHITE = "\033[37m"
    GRAY = "\033[90m"
    BG_GREEN = "\033[42m"
    BG_RED = "\033[41m"
    BG_YELLOW = "\033[43m"
    BG_BLUE = "\033[44m"

    @staticmethod
    def get_width():
        try:
            width = shutil.get_terminal_size().columns
            return max(40, width - 4)
        except:
            return 70

    @staticmethod
    def timestamp():
        return datetime.now().strftime("%H:%M:%S")

    @staticmethod
    def info(msg, **kwargs):
        ts = Console.timestamp()
        prefix = f"{Console.GRAY}[{ts}]{Console.RESET} {Console.GREEN}[INFO]{Console.RESET}"
        print(f"{prefix} {Console.WHITE}{msg}{Console.RESET}")
        for key, value in kwargs.items():
            print(f"         {Console.CYAN}-> {key}:{Console.RESET} {Console.WHITE}{value}{Console.RESET}")

    @staticmethod
    def success(msg, **kwargs):
        ts = Console.timestamp()
        prefix = f"{Console.GRAY}[{ts}]{Console.RESET} {Console.GREEN}{Console.BOLD}[SUCCESS]{Console.RESET}"
        print(f"{prefix} {Console.GREEN}{msg}{Console.RESET}")
        for key, value in kwargs.items():
            print(f"         {Console.CYAN}-> {key}:{Console.RESET} {Console.GREEN}{value}{Console.RESET}")

    @staticmethod
    def warn(msg, **kwargs):
        ts = Console.timestamp()
        prefix = f"{Console.GRAY}[{ts}]{Console.RESET} {Console.YELLOW}[WARN]{Console.RESET}"
        print(f"{prefix} {Console.YELLOW}{msg}{Console.RESET}")
        for key, value in kwargs.items():
            print(f"         {Console.CYAN}-> {key}:{Console.RESET} {Console.YELLOW}{value}{Console.RESET}")

    @staticmethod
    def error(msg, **kwargs):
        ts = Console.timestamp()
        prefix = f"{Console.GRAY}[{ts}]{Console.RESET} {Console.RED}[ERROR]{Console.RESET}"
        print(f"{prefix} {Console.RED}{msg}{Console.RESET}")
        for key, value in kwargs.items():
            print(f"         {Console.CYAN}-> {key}:{Console.RESET} {Console.RED}{value}{Console.RESET}")

    @staticmethod
    def request(endpoint, method="POST"):
        ts = Console.timestamp()
        width = Console.get_width()
        print(f"\n{Console.GRAY}{'─' * width}{Console.RESET}")
        print(f"{Console.GRAY}[{ts}]{Console.RESET} {Console.BLUE}{Console.BOLD}[REQUEST]{Console.RESET} {Console.CYAN}{method}{Console.RESET} → {Console.WHITE}{endpoint}{Console.RESET}")
        print(f"{Console.GRAY}{'─' * width}{Console.RESET}")

    @staticmethod
    def response(status="OK"):
        ts = Console.timestamp()
        color = Console.GREEN if status == "OK" else Console.RED
        print(f"{Console.GRAY}[{ts}]{Console.RESET} {color}{Console.BOLD}[RESPONSE]{Console.RESET} {color}{status}{Console.RESET}")