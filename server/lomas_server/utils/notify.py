import errno
import os
import socket


def notify(message: bytes) -> None:
    """
    Implement the systemd notify protocol without external dependencies.

    According to the protocol defined at:
    https://www.freedesktop.org/software/systemd/man/latest/sd_notify.html

    Args:
        message (bytes): well-known assignements:
            - READY=1
            - STOPPING=1
    """
    socket_path = os.environ.get("NOTIFY_SOCKET")
    if socket_path is None or len(socket_path) == 0:
        return

    if socket_path[0] not in {"/", "@"}:
        raise OSError(errno.EAFNOSUPPORT, "Unsupported socket type")

    # Handle abstract socket.
    if socket_path[0] == "@":
        socket_path = "\0" + socket_path[1:]

    with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM | socket.SOCK_CLOEXEC) as sock:
        sock.connect(socket_path)
        sock.sendall(message)
