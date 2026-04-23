"""
The ten Gaze effects and their mapping to Python modules/functions.

This is the vocabulary. Every entry here is a claim:
"calling this Python function performs this effect."
"""

from enum import Enum


class Effect(str, Enum):
    NET = "Net"
    FS = "Fs"
    DB = "Db"
    CONSOLE = "Console"
    ENV = "Env"
    TIME = "Time"
    RAND = "Rand"
    ASYNC = "Async"
    UNSAFE = "Unsafe"
    FAIL = "Fail"

    def __str__(self) -> str:
        return self.value


# Module-level effects: importing or calling anything from these modules
# implies the effect. The key is the module name (or prefix), the value
# is the effect.
MODULE_EFFECTS: dict[str, Effect] = {
    # Net: network I/O
    "urllib": Effect.NET,
    "urllib.request": Effect.NET,
    "urllib.parse": Effect.NET,  # debatable, but it's in the net family
    "http": Effect.NET,
    "http.client": Effect.NET,
    "http.server": Effect.NET,
    "socket": Effect.NET,
    "ssl": Effect.NET,
    "smtplib": Effect.NET,
    "ftplib": Effect.NET,
    "xmlrpc": Effect.NET,
    "requests": Effect.NET,
    "httpx": Effect.NET,
    "aiohttp": Effect.NET,
    "urllib3": Effect.NET,
    "websockets": Effect.NET,
    "grpc": Effect.NET,
    "paramiko": Effect.NET,
    "fabric": Effect.NET,
    "boto3": Effect.NET,
    "botocore": Effect.NET,
    # Fs: filesystem
    "os.path": Effect.FS,
    "pathlib": Effect.FS,
    "shutil": Effect.FS,
    "tempfile": Effect.FS,
    "glob": Effect.FS,
    "fnmatch": Effect.FS,
    "fileinput": Effect.FS,
    "zipfile": Effect.FS,
    "tarfile": Effect.FS,
    "gzip": Effect.FS,
    "bz2": Effect.FS,
    "lzma": Effect.FS,
    # Db: databases
    "sqlite3": Effect.DB,
    "dbm": Effect.DB,
    "shelve": Effect.DB,
    "psycopg2": Effect.DB,
    "psycopg": Effect.DB,
    "pymysql": Effect.DB,
    "mysql.connector": Effect.DB,
    "pymongo": Effect.DB,
    "redis": Effect.DB,
    "sqlalchemy": Effect.DB,
    "peewee": Effect.DB,
    "tortoise": Effect.DB,
    "databases": Effect.DB,
    "asyncpg": Effect.DB,
    "aiosqlite": Effect.DB,
    "motor": Effect.DB,
    # Console: terminal I/O
    "curses": Effect.CONSOLE,
    "readline": Effect.CONSOLE,
    "getpass": Effect.CONSOLE,
    # Env: environment
    # (os.environ is handled as a special case in the analyzer)
    "dotenv": Effect.ENV,
    "python_dotenv": Effect.ENV,
    # Time: clock and sleep
    "time": Effect.TIME,
    "datetime": Effect.TIME,
    "sched": Effect.TIME,
    "calendar": Effect.TIME,
    # Rand: randomness
    "random": Effect.RAND,
    "secrets": Effect.RAND,
    # Async: concurrency
    "asyncio": Effect.ASYNC,
    "threading": Effect.ASYNC,
    "multiprocessing": Effect.ASYNC,
    "concurrent": Effect.ASYNC,
    "concurrent.futures": Effect.ASYNC,
    # Unsafe: low-level / FFI
    "ctypes": Effect.UNSAFE,
    "cffi": Effect.UNSAFE,
    "mmap": Effect.UNSAFE,
    "struct": Effect.UNSAFE,
}

# Function-level effects: specific functions that imply effects
# regardless of which module they're in. Format: "module.function" -> Effect.
FUNCTION_EFFECTS: dict[str, Effect] = {
    # Builtins
    "builtins.print": Effect.CONSOLE,
    "builtins.input": Effect.CONSOLE,
    "builtins.open": Effect.FS,
    "builtins.exec": Effect.UNSAFE,
    "builtins.eval": Effect.UNSAFE,
    "builtins.compile": Effect.UNSAFE,
    "builtins.__import__": Effect.UNSAFE,
    # os module: mixed effects
    "os.getcwd": Effect.FS,
    "os.chdir": Effect.FS,
    "os.listdir": Effect.FS,
    "os.scandir": Effect.FS,
    "os.mkdir": Effect.FS,
    "os.makedirs": Effect.FS,
    "os.remove": Effect.FS,
    "os.unlink": Effect.FS,
    "os.rmdir": Effect.FS,
    "os.rename": Effect.FS,
    "os.replace": Effect.FS,
    "os.stat": Effect.FS,
    "os.walk": Effect.FS,
    "os.link": Effect.FS,
    "os.symlink": Effect.FS,
    "os.readlink": Effect.FS,
    "os.chmod": Effect.FS,
    "os.chown": Effect.FS,
    "os.getenv": Effect.ENV,
    "os.putenv": Effect.ENV,
    "os.environ": Effect.ENV,
    "os.system": Effect.UNSAFE,
    "os.popen": Effect.UNSAFE,
    "os.exec": Effect.UNSAFE,
    "os.execv": Effect.UNSAFE,
    "os.execve": Effect.UNSAFE,
    "os.fork": Effect.ASYNC,
    "os.kill": Effect.UNSAFE,
    "os.getpid": Effect.ENV,
    # subprocess: both Net-adjacent and Unsafe
    "subprocess.run": Effect.UNSAFE,
    "subprocess.call": Effect.UNSAFE,
    "subprocess.check_call": Effect.UNSAFE,
    "subprocess.check_output": Effect.UNSAFE,
    "subprocess.Popen": Effect.UNSAFE,
    # sys module
    "sys.exit": Effect.FAIL,
    "sys.argv": Effect.ENV,
    "sys.stdin": Effect.CONSOLE,
    "sys.stdout": Effect.CONSOLE,
    "sys.stderr": Effect.CONSOLE,
}

# Attribute access patterns that imply effects.
# These catch things like `os.environ["KEY"]` or `sys.argv[0]`.
ATTRIBUTE_EFFECTS: dict[str, Effect] = {
    "os.environ": Effect.ENV,
    "sys.argv": Effect.ENV,
    "sys.stdin": Effect.CONSOLE,
    "sys.stdout": Effect.CONSOLE,
    "sys.stderr": Effect.CONSOLE,
}
