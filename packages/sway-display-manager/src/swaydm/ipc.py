import os
import socket
import sys
import threading
from dataclasses import dataclass
from typing import Callable

from . import utils, code


@dataclass
class IPCManager:
    socket: str


DEFAULT_SOCKET_PATH = "/tmp/swaydm.sock"
mgr: IPCManager = IPCManager(socket=DEFAULT_SOCKET_PATH)


def setup(socket: str) -> None:
    mgr.socket = socket


def start_server(handler: Callable[[str], str]) -> None:
    if os.path.exists(mgr.socket):
        try:
            # check if socket is already held by a running process
            test = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            test.connect(mgr.socket)
            test.close()
            raise RuntimeError(
                f"Socket {mgr.socket!r} is already in use by another process"
            )
        except RuntimeError as e:
            utils.error(f"{e}")
            sys.exit(1)
        except ConnectionRefusedError:
            # stale socket, safe to remove
            os.unlink(mgr.socket)

    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(mgr.socket)
    server.listen(1)

    def serve():
        while True:
            conn, _ = server.accept()
            with conn:
                data = conn.recv(1024).decode().strip()
                utils.debug(f"IPC Server - Accept - {data!r}")
                response = handler(data)
                try:
                    conn.sendall(response.encode())
                except BrokenPipeError:
                    utils.warning(
                        "client disconnected before response could be sent"
                    )

    thread = threading.Thread(target=serve, daemon=True)

    utils.info("Starting Sway IPC server")
    thread.start()


def parse_response(raw: str) -> tuple[code.Code, str]:
    code_str, _, body = raw.partition("\n")
    return code.Code(int(code_str)), body


def send_command(command: str) -> None:
    resp_code = code.Code.ERROR
    try:
        client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        client.connect(mgr.socket)

        utils.debug(f"IPC Client - Send: {command!r}")
        client.sendall(command.encode())
        client.shutdown(socket.SHUT_WR)
        resp_code, response = parse_response(client.recv(4096).decode())

        if resp_code is code.Code.OK:
            print(response)
        else:
            utils.error(response)

        client.close()
        code.exit_with_status(resp_code)
    except ConnectionRefusedError:
        resp_code = code.Code.ERROR
        utils.error(
            "Unable to connect to display manager. Is swaydm daemon running?"
        )
    finally:
        code.exit_with_status(resp_code)


def switch_profile(profile: str) -> None:
    send_command(f"switch_profile {profile}")


def list_profiles() -> None:
    send_command("list_profiles")


def status(verbose: bool, json: bool) -> None:
    command = "status"
    if json:
        command = "status_json"

    send_command(f"{command} {'verbose' if verbose else ''}")


def reload_config() -> None:
    send_command("reload")


def toggle_auto_apply() -> None:
    send_command("toggle_auto_apply")


def enable_auto_apply() -> None:
    send_command("enable_auto_apply")


def disable_auto_apply() -> None:
    send_command("disable_auto_apply")


def debug() -> None:
    send_command("debug")
