# Ethernaut 2024 CTF Infra

This repository contains all the infrastructure to host the Ethernaut CTF 2024, based on [Paradigm's CTF infrastructure](https://github.com/paradigmxyz/paradigm-ctf-infrastructure).

## Usage Local

To run the CTF infrastructure locally, simply run the following commands:

```bash
cd paradigmctf.py
docker compose up -d
```

To run the CTF infrastructure in kCTF, you'll need to do the following:

```bash
# create the cluster if it doesn't exist
kctf cluster create --type kind local-cluster --start

# build the image
(cd paradigmctf.py; docker build ghcr.io/openzeppelin/ctf-infra:latest)

# push the image to kind
kind load docker-image --name "${CLUSTER_NAME}" "ghcr.io/openzeppelin/ctf-infra:latest"

# create all the resources
kubectl apply kubernetes/ctf-server.yaml

# port forward the anvil proxy for local access
kubectl port-forward service/anvil-proxy 8545:8545 &
```

Now you'll be able to build and test challenges in kCTF:
```bash
# start the challenge
kctf chal start

# port forward the challenge
kctf chal debug port-forward --port 1337 --local-port 1337 &

# connect to the challenge
nc 127.0.0.1 1337
```

## Images

This infrastructure runs on [kCTF](https://google.github.io/kctf/), a Kubernetes-based CTF platform. Follow the kCTF setup instructions to get a local cluster running on your computer.

### kctf-challenge
The [kctf-challenge](/kctf-challenge/) image acts as a standard image on top of the kCTF base image. It's optional, not required, but provides the following features:
- Adds the `/bin/kctf_persist_env` and `/bin/kctf_restore_env` scripts for use with `kctf_drop_privs`, which resets all environment variables (this might be removed if a better way of passing configuration variables is identified)
- Adds a common `nsjail.cfg` for use with Anvil. The usefulness of running the Anvil server inside nsjail is debatable, as a lot of security features need to be disabled (timeouts, resource limits, etc). The file is also poorly-named, and may be changed in the future

### paradigmctf.py
The [paradigmctf.py](/paradigmctf.py/) image acts as the base image for all challenges. It provides the following features:
- Installs the `ctf_launchers`, `ctf_solvers`, and `ctf_server` libraries. These can be used to orchestrate CTF challenge instances.

## Libraries

### forge-ctf
The [forge-ctf](/forge-ctf/) library provides two Forge scripts which can be used to deploy and solve challenges. They are intended to be used with the `eth_launchers` package.

The `CTFDeployment` script can be overridden to implement the `deploy(address system, address player) internal returns (address challenge)` function. It defaults to using the `test [...] test junk` mnemonic, but will read from the `MNEMONIC` environment variable. It writes the address that the challenge was deployed at to `/tmp/deploy.txt`, or the value of `OUTPUT_FILE`.

The `CTFSolver` script can be overriden to implement the `solve(address challenge, address player)` function. The challenge address must be specified as the `CHALLENGE` environment variable. The player private key defaults to the first key generated from the `test [...] junk` mnemonic, but can be overridden with `PLAYER`.
