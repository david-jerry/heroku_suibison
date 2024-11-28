from src.utils.sui_json_rpc_apis import SUI
import asyncio
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

mnemonic_phrase = "ozone proof crawl brief abuse minor flower invest save banana seat head goose eternal chunk ecology liquid gentle arrange erosion vital photo music beach"
future = loop.run_until_complete(SUI.paySui("0xaa8bea4226bda3a323a13f33157547c5847cbeca1384018bcfc7a4b18cb43b7c", "0x28768bb2c5ede1e7e99ba27301494ba75f933e3c83ce242f43d9dc1b9b455a30", "10", "10000", "0x21a571e5082bea828eeb8c07a940a0194181a0223cb3502d71f4b0f9d1003f26"))
transactionResponse = loop.run_until_complete(SUI.executeTransaction(future.txBytes, mnemonic_phrase))
