FROM python:3.11.6-slim

# Set up unprivileged user and install dependencies
# TODO: we need bsdmainutils so we have hexdump so foundry-huff can...
#       generate some random bytes... :/
RUN true && \
    useradd -u 1000 -m user && \
    apt-get update && \
    apt-get install -y curl git socat bsdmainutils build-essential && \
    rm -rf /var/cache/apt/lists /var/lib/apt/lists/* && \
    true

# Install Foundry
ENV FOUNDRY_DIR=/opt/foundry

ENV PATH=${FOUNDRY_DIR}/bin/:${PATH}

RUN true && \
    curl -L https://foundry.paradigm.xyz | bash && \
    foundryup && \
    true

# Install Huff
ENV HUFF_DIR=/opt/huff

ENV PATH=${HUFF_DIR}/bin/:${PATH}

RUN true && \
    curl -L http://get.huff.sh | bash && \
    huffup && \
    true

# Install Stylus

env RUSTUP_HOME=/opt/rust/rustup CARGO_HOME=/opt/rust/cargo
env PATH=${PATH}:/opt/rust/cargo/bin

RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
RUN rustup toolchain install nightly
RUN rustup component add rust-src --toolchain nightly
RUN rustup target add wasm32-unknown-unknown
RUN RUSTFLAGS="-C link-args=-rdynamic" cargo install --force cargo-stylus
RUN cargo install wasm-opt --locked

RUN chmod -R 777 /opt/rust

# (Optimization) Install requirements
COPY requirements.txt /tmp/requirements.txt

RUN pip install -r /tmp/requirements.txt

# Install the library
COPY . /tmp/paradigmctf.py

RUN true && \
    pip install /tmp/paradigmctf.py uvicorn && \
    rm -rf /tmp/requirements.txt /tmp/paradigmctf.py && \
    true

USER 1000

WORKDIR /home/user