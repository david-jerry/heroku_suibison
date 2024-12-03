from decimal import ROUND_UP, Decimal
import pprint
from typing import List
import base64
import hashlib
import asyncio
import nacl.signing
import requests

from src.apps.accounts.models import User
from src.apps.accounts.schemas import Coin, CoinBalance, MetaData, SuiTransferResponse, TransactionResponseData
from src.config.settings import Config
from src.utils.logger import LOGGER
from sui_python_sdk.wallet import SuiWallet
import ecdsa
import nacl

class SUIRequests:
    def __init__(self, url: str = Config.SUI_RPC) -> None:
        self.url = url
        self.decimals = 10**9
                
    async def sign_transaction(self, txBytes: str, pk: bytes, pubKey: bytes):
        bytesTx = base64.b64decode(txBytes)
        hasher = hashlib.blake2b(bytesTx, digest_size=32)
        digest = hasher.digest()
        LOGGER.debug(f"txBytes Digest: {base64.b64encode(digest).decode()}")
        
        scheme = pubKey[0:1]
        curve = ecdsa.SECP256k1
        if scheme == "\x00":
            curve = ecdsa.Ed25519
        pkECDSAKey = ecdsa.SigningKey.from_string(pk, curve=curve)
        signature = pkECDSAKey.sign(digest, hashfunc=hashlib.blake2b, sigencode=ecdsa.util.sigencode_string)
        # signature = nacl.signing.SigningKey(pk).sign(digest)[:64]
        LOGGER.debug(f"PubKey: {pubKey[0:1]}")
        # LOGGER.debug(f"PrivKey: {hashlib.blake2b(pk, digest_size=32).hexdigest()}")
        LOGGER.debug(signature)
        
        flag = b"\x00"
        serialized_sig = flag + signature + pubKey[1:]
        return serialized_sig
        
        
    async def getBalance(self, address: str, coinType: str = "0x2::sui::SUI"):
        """
        Geets the balance for a specific coin defaults to sui and returns the balance of the coin and coinId
        """
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "suix_getBalance",
            "params": [
                address,
                coinType
            ]
        }
        
        response = await asyncio.to_thread(requests.post, self.url, json=payload)
        
        if response.status_code == 200:
            result = response.json()
            if 'error' in result:
                raise Exception(f"Error: {result['error']}")
            res = result["result"]
            LOGGER.debug(res)
            return CoinBalance(**res)
        else:
            response.raise_for_status()
            
    async def getCoinMetadata(self, coinType: str = "0x2::sui::SUI"):
        """
        Gets the metadata for a specified coin type defaults to sui and returns a response which includes the coin id used for transafers 
        """
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "suix_getCoinMetadata",
            "params": [
                coinType
            ]
        }
        
        response = await asyncio.to_thread(requests.post, self.url, json=payload)
        
        if response.status_code == 200:
            result = response.json()
            if 'error' in result:
                raise Exception(f"Error: {result['error']}")
            metadata = result["result"]
            return MetaData(**metadata)
        else:
            response.raise_for_status()
 
    async def getCoins(self, address: str):
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "suix_getAllCoins",
            "params": [
                address
            ]
        }
        
        response = await asyncio.to_thread(requests.post, self.url, json=payload)
        coins: List[Coin] = []
        if response.status_code == 200:
            result = response.json()
            LOGGER.debug(f"COINIDS: {result}")
            if 'error' in result:
                raise Exception(f"Error: {result['error']}")
            for coin in result['result']["data"]:
                LOGGER.info(f"Checking coins {coin}")
                if coin["coinType"] == "0x2::sui::SUI":
                    coins.append(Coin(**coin))
            return coins
        else:
            response.raise_for_status()

    async def paySui(self, address: str, recipient: str, amount: Decimal, gas_budget: Decimal, coinIds: List[Coin]):
        coins = []
        for coin in coinIds:
            coins.append(coin.coinObjectId)

        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "unsafe_paySui",
            "params": [
                address,
                coins,
                [recipient],
                [str(round(amount * 10**9))],
                str(round(gas_budget * 10**9))
            ]
        }
                
        response = await asyncio.to_thread(requests.post, self.url, json=payload)
        
        if response.status_code == 200:
            result = response.json()
            LOGGER.debug(f"PAYSUI RESPONSE: {result}")
            if 'error' in result:
                raise Exception(f"PAYSUI-Error: {result['error']}")
            res = result["result"]["txBytes"]
            LOGGER.debug(f"TXBYTES: {res}")
            return res
        else:
            response.raise_for_status()
        
    async def payAllSui(self, address: str, recipient: str, gas_budget: Decimal, coinIds: List[Coin]):
        coins = []
        for coin in coinIds:
            coins.append(coin.coinObjectId)
        
        gb = str(round(gas_budget * 10**9))
        LOGGER.debug(f"PAYALL GASBUDGET: {gb}")
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "unsafe_payAllSui",
            "params": [
                address,
                coins,
                recipient,
                gb
            ]
        }
        
        response = await asyncio.to_thread(requests.post, self.url, json=payload)
        
        if response.status_code == 200:
            result = response.json()
            LOGGER.debug(f"PAYALLSUI RESPONSE: {result}")
            if 'error' in result:
                raise Exception(f"PAYALLSUI- Error: {result['error']}")
            res = result["result"]
            return SuiTransferResponse(**res)
        else:
            response.raise_for_status()
            
    async def dryRun(self, txBytes: str):
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "sui_dryRunTransactionBlock",
            "params": [
                txBytes,
            ]
        }
        response = await asyncio.to_thread(requests.post, self.url, json=payload)
        LOGGER.debug(response)
        
        if response.status_code == 200:
            result = response.json()
            if 'error' in result:
                raise Exception(f"Error: {result['error']}")
            res = result["result"]["transaction"]["txSignatures"]
            LOGGER.debug(pprint.pprint(res, indent=4))
            return TransactionResponseData(**res)
        else:
            response.raise_for_status()

    async def executeTransaction(self, bcsTxBytes: str, privateKey: str):
        payload = {
            "secret": privateKey,
            "txBytes": bcsTxBytes,
        }
        LOGGER.debug(f"EXECUTE PAYLOAD: {payload}")
        response = await asyncio.to_thread(requests.post, "https://suiwallet.sui-bison.live/wallet/se-transactions", json=payload)
        LOGGER.debug(f"Execution response: {response.json()}")
        
        result = response.json()
        return result

    async def depositToSmartContract(self, amount: Decimal, privateKey: str):
        payload = {
            "secret": privateKey,
            "amount": round(amount.quantize(Decimal("0.000000001"), rounding=ROUND_UP) * 10**9),
        }
        LOGGER.debug(f"EXECUTE PAYLOAD: {payload}")
        response = await asyncio.to_thread(requests.post, "https://suiwallet.sui-bison.live/escrow/deposit", json=payload)
        LOGGER.debug(f"Execution response: {response.json()}")
        
        result = response.json()
        return result

    async def transferFromSmartContract(self, amount: Decimal, wallet: str, privateKey: str):
        payload = {
            "secret": privateKey,
            "amount": round(amount.quantize(Decimal("0.000000001"), rounding=ROUND_UP) * 10**9),
            "wallet": wallet
        }
        LOGGER.debug(f"EXECUTE PAYLOAD: {payload}")
        response = await asyncio.to_thread(requests.post, "https://suiwallet.sui-bison.live/escrow/withdraw", json=payload)
        LOGGER.debug(f"Execution response: {response.json()}")
        
        result = response.json()
        return result

SUI = SUIRequests()

"""
sui keytool sign --address <SUI-ADDRESS> --data <TX_BYTES>

Ed25519 Pure: 0x00
ECDSA Secp256k1: 0x01
ECDSA Secp256r1: 0x02
Multisig: 0x03
zkLogin: 0x05

import { Secp256k1Keypair } from '@mysten/sui/keypairs/secp256k1';
import { Transaction } from '@mysten/sui/transactions';

// Assuming you have the serialized transaction bytes
const txBytes = ...; // Your serialized transaction bytes

// Create a keypair
const keypair = new Secp256k1Keypair();

// Get the public key
const publicKey = keypair.getPublicKey();

// Hash the transaction data
const digest = hashTransactionData(txBytes); // Implement Blake2b hashing

// Sign the digest
const signature = keypair.sign(digest);

// Concatenate flag, signature, and public key
const flag = Buffer.from([0x01]);
const serializedSignature = Buffer.concat([flag, signature, publicKey]);
"""