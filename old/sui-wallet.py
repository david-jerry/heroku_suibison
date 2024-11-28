from bip_utils import Bip39MnemonicGenerator, Bip39SeedGenerator, Bip32Slip10Ed25519, Bip32Utils
from hashlib import blake2b
import bech32
from sui_python_sdk.wallet import SuiWallet

from src.utils.logger import LOGGER

mnemonic = Bip39MnemonicGenerator().FromWordsNumber(12)
LOGGER.info(f"Mnemonic Phrase: {mnemonic}")

seed_bytes = Bip39SeedGenerator(mnemonic=mnemonic).Generate()


# Step 3: Derive the keypair using the specified derivation path
bip32_ctx = Bip32Slip10Ed25519.FromSeed(seed_bytes)
derived_key = bip32_ctx.DerivePath("m/44'/784'/0'/0'/0'")

private_key = derived_key.PrivateKey().Raw().ToBytes()
public_key = derived_key.PublicKey().RawCompressed().ToBytes()
bech32.bech32_encode("sui", bech32.convertbits(private_key + b"\x00", 8, 5))

# Step 4: Generate the Sui address
# Ed25519 scheme flag is 0x00
flag = b'\x00'
sui_address_input = flag + public_key
sui_address = blake2b(sui_address_input, digest_size=32).hexdigest()

wallet = SuiWallet(mnemonic)
suiWallet_address_input = flag + wallet.public_key
suiWallet_address = blake2b(suiWallet_address_input, digest_size=32).hexdigest()
bech32.bech32_encode("suiprivkey1", bech32.convertbits(private_key + b"\x00", 8, 5))
LOGGER.debug(f"Private Key: \x00{wallet.private_key}")
LOGGER.debug(f"Public Key: {wallet.public_key.hex()}")
LOGGER.debug(f"SUI Address: {suiWallet_address}")