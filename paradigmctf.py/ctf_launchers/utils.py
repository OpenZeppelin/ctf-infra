import json
import os
import re
import subprocess
from typing import Dict

from web3 import Web3

from foundry.anvil import anvil_autoImpersonateAccount, anvil_setCode


def deploy(
    web3: Web3,
    project_location: str,
    mnemonic: str,
    deploy_script: str = "script/Deploy.s.sol:Deploy",
    env: Dict = {},
) -> str:
    anvil_autoImpersonateAccount(web3, True)

    rfd, wfd = os.pipe2(os.O_NONBLOCK)

    proc = subprocess.Popen(
        args=[
            "/opt/foundry/bin/forge",
            "script",
            "--rpc-url",
            web3.provider.endpoint_uri,
            "--out",
            "/artifacts/out",
            "--cache-path",
            "/artifacts/cache",
            "--broadcast",
            "--unlocked",
            "--sender",
            "0x0000000000000000000000000000000000000000",
            deploy_script,
        ],
        env={
            "PATH": "/opt/huff/bin:/opt/foundry/bin:/usr/bin:" + os.getenv("PATH", "/fake"),
            "MNEMONIC": mnemonic,
            "OUTPUT_FILE": f"/proc/self/fd/{wfd}",
        }
        | env,
        pass_fds=[wfd],
        cwd=project_location,
        text=True,
        encoding="utf8",
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    stdout, stderr = proc.communicate()

    anvil_autoImpersonateAccount(web3, False)

    if proc.returncode != 0:
        print(stdout)
        print(stderr)
        raise Exception("forge failed to run")

    result = os.read(rfd, 256).decode("utf8")

    os.close(rfd)
    os.close(wfd)

    return result


def deploy_cairo(
    web3: Web3,
    project_location: str,
    credentials: list,
    deploy_script: str = "deploy.py",
    env: Dict = {},
) -> str:
    rfd, wfd = os.pipe2(os.O_NONBLOCK)

    proc = subprocess.Popen(
        args=[
            "/usr/local/bin/python3",
            deploy_script,
        ],
        env={
            "RPC_URL": web3.provider.endpoint_uri + "/rpc",
            "PRIVATE_KEY": credentials[0][1],
            "ACCOUNT_ADDRESS": credentials[0][0],
        }
        | env,
        pass_fds=[wfd],
        cwd=project_location,
        text=True,
        encoding="utf8",
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    stdout, stderr = proc.communicate()

    if proc.returncode != 0:
        print(stdout)
        print(stderr)
        raise Exception("script failed to run")

    output = stdout.split('address: ')[1].replace("\\n", "")

    return output[:65]


def deploy_no_impersonate(
    web3: Web3,
    project_location: str,
    mnemonic: str,
    token: str,
    deploy_script: str = "script/Deploy.s.sol:Deploy",
    env: Dict = {}
) -> str:
    proc = subprocess.Popen(
        args=[
            "/opt/foundry/bin/forge",
            "create",
            "src/Challenge.sol:Challenge",
            "--constructor-args",
            token,
            "--rpc-url",
            web3.provider.endpoint_uri,
            "--private-key",
            "0xb6b15c8cb491557369f3c7d2c287b053eb229daa9c22138887752191c9520659"
        ],
        env={
            "PATH": "/opt/huff/bin:/opt/foundry/bin:/usr/bin:" + os.getenv("PATH", "/fake"),
        }
        | env,
        cwd=project_location,
        text=True,
        encoding="utf8",
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    stdout, stderr = proc.communicate()

    if proc.returncode != 0:
        print(stdout)
        print(stderr)
        raise Exception("forge failed to run")

    address = stdout.split('Deployed to: ')[
        1].replace("\\n", "")[:42]

    cast_initialize(web3, project_location, token, address)

    return address


def cast_initialize(
    web3: Web3,
    project_location: str,
    token: str,
    entrypoint: str
) -> str:
    proc = subprocess.Popen(
        args=[
            "/opt/foundry/bin/cast",
            "send",
            token,
            "0xc4d66de8000000000000000000000000"  + entrypoint[2:],
            "--rpc-url",
            web3.provider.endpoint_uri,
            "--private-key",
            "0xb6b15c8cb491557369f3c7d2c287b053eb229daa9c22138887752191c9520659"
        ],
        cwd=project_location,
        text=True,
        encoding="utf8",
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    stdout, stderr = proc.communicate()

    if proc.returncode != 0:
        print(stdout)
        print(stderr)
        raise Exception("cast failed to run")


def deploy_nitro(
    web3: Web3,
    project_location: str,
    mnemonic: list,
    env: Dict = {},
) -> str:
    rfd, wfd = os.pipe2(os.O_NONBLOCK)

    proc = subprocess.Popen(
        args=[
            "/opt/rust/cargo/bin/cargo",
            "stylus",
            "deploy",
            "-e",
            web3.provider.endpoint_uri,
            "--private-key",
            "0xb6b15c8cb491557369f3c7d2c287b053eb229daa9c22138887752191c9520659"
        ],
        pass_fds=[wfd],
        cwd=project_location,
        text=True,
        encoding="utf8",
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    stdout, stderr = proc.communicate()

    if proc.returncode != 0:
        print(stdout)
        print(stderr)
        raise Exception("script failed to run")

    address = stdout.split('Activating program at address ')[
        1].replace("\\n", "")

    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

    token = ansi_escape.sub('', address)[:42]

    env = {
        "PATH": "/opt/huff/bin:/opt/foundry/bin:/usr/bin:" + os.getenv("PATH", "/fake"),
        "MNEMONIC": mnemonic,
        "OUTPUT_FILE": f"/proc/self/fd/{wfd}",
        "TOKEN": token
    }

    output = deploy_no_impersonate(
        web3,
        project_location,
        "",
        token,
        env=env,
    )

    return output


def anvil_setCodeFromFile(
    web3: Web3,
    addr: str,
    target: str,  # "ContractFile.sol:ContractName",
):
    file, contract = target.split(":")

    with open(f"/artifacts/out/{file}/{contract}.json", "r") as f:
        cache = json.load(f)

        bytecode = cache["deployedBytecode"]["object"]

    anvil_setCode(web3, addr, bytecode)


def http_url_to_ws(url: str) -> str:
    if url.startswith("http://"):
        return "ws://" + url[len("http://"):]
    elif url.startswith("https://"):
        return "wss://" + url[len("https://"):]

    return url
