# SUI Byson - Version 2

Sui-Bison is the first of its kind community driven smart contract project on the sui blockchain, with expert computer engineers and mathematicians, working to ensure that we earn and grow our sui portfolio.

## Why Accumulate the SUI Tken with SUI Bison Smart Contract

The SUI Token is the native cryptocurrency of the Sui Blockchain, which is designed to facilitate transactions, incentivize network peticipants, and enable governance. Sui Token and its blockchain are one of the fastest, smooth and reliable crypto projects of our time. Many has predicted it to be next Solana. What better way to accumulate Sui than participating on the staking opportunity o Sui bison

## History of SUI

Sui is a layer-1 blockchai optimizing for low-latency blockchain transfers. Its focused on instant transaction finality and high-speed transaction to make Sui a suitable platform for on-chain use cases like games, finance ad other real-time applicatios.

## Deployment Requirements

1. Rust - `curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh`
    Essentially required to run sui commands with pysui

2. Dokku - Smallest paas alternative to Heroku

    ```shell
    # download the installation script

    wget -NP . https://dokku.com/bootstrap.sh

    # run the installer

    sudo DOKKU_TAG=v0.35.10 bash bootstrap.sh

    # Configure your server domain

    dokku domains:set-global sui-bison.live

    # and your ssh key to the dokku user

    PUBLIC_KEY="your-public-key-contents-here"

    echo "$PUBLIC_KEY" | dokku ssh-keys:add admin

    # create your first app and you're off!

    dokku apps:create test-app
    ```

3. VPS
    Minimum 4GB Ram, Ubuntu OS installed

4. SUI Binaries

    ```shell
    cargo install --locked --git https://github.com/MystenLabs/sui.git --branch testnet sui
    ```

## DOKKU LOG SPECIFIC

dokku logs node-js-app -t -p web