import os
import subprocess
from dataclasses import dataclass
from typing import Dict, List, NotRequired, Optional

from eth_account import Account
from eth_account.account import LocalAccount
from eth_account.hdaccount import key_from_seed, seed_from_mnemonic
from typing_extensions import TypedDict
from web3 import Web3

DEFAULT_IMAGE = "ghcr.io/foundry-rs/foundry:latest"
DEFAULT_DERIVATION_PATH = "m/44'/60'/0'/0/"
DEFAULT_ACCOUNTS = 10
DEFAULT_BALANCE = 1000
DEFAULT_MNEMONIC = "test test test test test test test test test test test junk"

PUBLIC_HOST = os.getenv("PUBLIC_HOST", "http://127.0.0.1:8545")


class LaunchAnvilInstanceArgs(TypedDict):
    image: NotRequired[Optional[str]]
    accounts: NotRequired[Optional[int]]
    balance: NotRequired[Optional[float]]
    derivation_path: NotRequired[Optional[str]]
    mnemonic: NotRequired[Optional[str]]
    fork_url: NotRequired[Optional[str]]
    fork_block_num: NotRequired[Optional[int]]
    fork_chain_id: NotRequired[Optional[int]]
    no_rate_limit: NotRequired[Optional[bool]]
    chain_id: NotRequired[Optional[int]]
    code_size_limit: NotRequired[Optional[int]]
    block_time: NotRequired[Optional[int]]


def format_anvil_args(args: LaunchAnvilInstanceArgs, anvil_id: str, port: int = 8545) -> List[str]:
    cmd_args = []
    cmd_args += ["--host", "0.0.0.0"]
    cmd_args += ["--port", str(port)]
    cmd_args += ["--accounts", "0"]
    cmd_args += ["--state", f"/data/{anvil_id}-state.json"]
    cmd_args += ["--state-interval", "5"]

    if args.get("fork_url") is not None:
        cmd_args += ["--fork-url", args["fork_url"]]

    if args.get("fork_chain_id") is not None:
        cmd_args += ["--fork-chain-id", str(args["fork_chain_id"])]

    if args.get("fork_block_num") is not None:
        cmd_args += ["--fork-block-number", str(args["fork_block_num"])]

    if args.get("no_rate_limit") == True:
        cmd_args += ["--no-rate-limit"]

    if args.get("chain_id") is not None:
        cmd_args += ["--chain-id", str(args["chain_id"])]

    if args.get("code_size_limit") is not None:
        cmd_args += ["--code-size-limit", str(args["code_size_limit"])]

    if args.get("block_time") is not None:
        cmd_args += ["--block-time", str(args["block_time"])]

    return cmd_args


def format_starknet_args(args: LaunchAnvilInstanceArgs, anvil_id: str, port: int = 8545) -> List[str]:
    cmd_args = []
    cmd_args += ["--host", "0.0.0.0"]
    cmd_args += ["--port", str(port)]
    cmd_args += ["--accounts", "2"]
    cmd_args += ["--seed", "0"]

    return cmd_args


def format_nitro_args(args: LaunchAnvilInstanceArgs, anvil_id: str, port: int = 8545) -> List[str]:
    cmd_args = []
    cmd_args += ["--node.dangerous.no-l1-listener"]
    cmd_args += ["--node.sequencer.dangerous.no-coordinator"]
    cmd_args += ["--node.sequencer.enable"]
    cmd_args += ["--node.staker.enable=false"]
    cmd_args += ["--init.dev-init"]
    cmd_args += ["--init.empty=false"]
    cmd_args += ["--chain.id=473474"]
    cmd_args += ["--chain.dev-wallet.private-key=b6b15c8cb491557369f3c7d2c287b053eb229daa9c22138887752191c9520659"]
    cmd_args += ["--http.addr=0.0.0.0"]
    cmd_args += ["--http.port", str(port)]
    cmd_args += ["--http.vhosts='*'"]
    cmd_args += ["--http.corsdomain='*'"]
    cmd_args += ["--chain.info-json", '[{"chain-name": "ctf","chain-config": {"chainId": 473474,"homesteadBlock": 0,"daoForkBlock": null,"daoForkSupport": true,"eip150Block": 0,"eip150Hash": "0x0000000000000000000000000000000000000000000000000000000000000000","eip155Block": 0,"eip158Block": 0,"byzantiumBlock": 0,"constantinopleBlock": 0,"petersburgBlock": 0,"istanbulBlock": 0,"muirGlacierBlock": 0,"berlinBlock": 0,"londonBlock": 0,"clique": {"period": 0,"epoch": 0},"arbitrum": {"EnableArbOS": true,"AllowDebugPrecompiles": true,"DataAvailabilityCommittee": false,"InitialArbOSVersion": 11,"InitialChainOwner": "0x0000000000000000000000000000000000000000","GenesisBlockNum": 0}}}]']

    return cmd_args


class DaemonInstanceArgs(TypedDict):
    image: str


class CreateInstanceRequest(TypedDict):
    type: str
    instance_id: str
    timeout: int
    anvil_instances: NotRequired[Dict[str, LaunchAnvilInstanceArgs]]
    daemon_instances: NotRequired[Dict[str, DaemonInstanceArgs]]


class InstanceInfo(TypedDict):
    id: str
    ip: str
    port: int


@dataclass
class AnvilInstance:
    proc: subprocess.Popen
    id: str

    ip: str
    port: int


class UserData(TypedDict):
    instance_id: str
    external_id: str
    created_at: float
    expires_at: float
    # launch_args: Dict[str, LaunchAnvilInstanceArgs]
    anvil_instances: Dict[str, InstanceInfo]
    daemon_instances: Dict[str, InstanceInfo]
    metadata: Dict


def get_account(mnemonic: str, offset: int) -> LocalAccount:
    seed = seed_from_mnemonic(mnemonic, "")
    private_key = key_from_seed(seed, f"{DEFAULT_DERIVATION_PATH}{offset}")

    return Account.from_key(private_key)


def get_player_account(mnemonic: str) -> LocalAccount:
    return get_account(mnemonic, 0)


def get_system_account(mnemonic: str) -> LocalAccount:
    return get_account(mnemonic, 1)


def get_additional_account(mnemonic: str, offset: int) -> LocalAccount:
    return get_account(mnemonic, offset + 2)


def get_privileged_web3(user_data: UserData, anvil_id: str) -> Web3:
    anvil_instance = user_data["anvil_instances"][anvil_id]
    return Web3(
        Web3.HTTPProvider(
            f"http://{anvil_instance['ip']}:{anvil_instance['port']}")
    )


def get_unprivileged_web3(user_data: UserData, anvil_id: str) -> Web3:
    return Web3(
        Web3.HTTPProvider(
            f"http://anvil-proxy:8545/{user_data['external_id']}/{anvil_id}"
        )
    )
