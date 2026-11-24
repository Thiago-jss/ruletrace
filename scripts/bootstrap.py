from os import O_APPEND, O_CREAT, O_EXCL, O_NOFOLLOW, O_RDWR, fdopen, fstat
from os import open as open_file
from pathlib import Path
from secrets import token_hex
from stat import S_ISREG

path = Path(__file__).resolve().parents[1] / ".env"
names = ("RULETRACE_DB_PASSWORD", "RULETRACE_READER_PASSWORD")
try:
    descriptor = open_file(path, O_CREAT | O_EXCL | O_RDWR, 0o600)
except FileExistsError:
    descriptor = open_file(path, O_APPEND | O_NOFOLLOW | O_RDWR)
with fdopen(descriptor, "a+", encoding="utf-8") as stream:
    mode = fstat(stream.fileno()).st_mode
    if not S_ISREG(mode) or mode & 0o077:
        raise SystemExit("Expected a private regular .env file")
    stream.seek(0)
    current = stream.read()
    present = {line.split("=", 1)[0].strip() for line in current.splitlines() if "=" in line}
    pending = [f"{name}={token_hex(32)}" for name in names if name not in present]
    if pending:
        stream.write(
            ("\n" if current and not current.endswith("\n") else "") + "\n".join(pending) + "\n"
        )
    print(f"Added {len(pending)} missing local settings; existing values preserved.")
