# OpenZeppelin CTF 2023

This repo contains the infrastructure & challenges for the OpenZeppelin CTF in 2023. The infrasturcture is built on top of [kCTF](https://github.com/google/kctf) and forked from [blazctf-2023](https://github.com/fuzzland/blazctf-2023).

Directory:
* `infrastructure`: Contains the infrastructure code forked from [paradigm-ctf-infrastructure](https://github.com/paradigmxyz/paradigm-ctf-infrastructure) with some modifications.
* `challenges`: Challenges code and environment setup.
* `solutions`: Solutions for the challenges.

### How launch the challenge locally?
1. cd into `infrastucture/paradigmctf.py` and run `docker-compose up -d` to start the infra servers.
2. cd into `challenges/<challenge_name>/challenge` and run `docker-compose up -d` to start the challenge server.
3. nc localhost 1337 to manage instance.

Remember to delete existing instance before you switch to another challenge.

# Challenges
WIP
