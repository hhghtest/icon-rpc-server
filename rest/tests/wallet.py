#!/usr/bin/env python
import base64
import hashlib
import logging
import binascii
import random
import sys

from secp256k1 import PrivateKey, PublicKey
from loopchain import utils

ICX_FACTOR = 10 ** 18
ICX_FEE = 0.01


class Wallet:
    def __init__(self, private_key=None):
        self.__private_key = private_key or PrivateKey()
        self.__address = self.__create_address(self.__private_key.pubkey)
        self.__last_raw_icx_origin = None

        self.to_address = None
        self.value = None
        self.fee = ICX_FEE
        self.is_logging = True

    @property
    def address(self):
        return self.__address

    def get_last_icx_origin(self, is_raw_data=False):
        if self.__last_raw_icx_origin is None:
            return None

        return self.__last_raw_icx_origin if is_raw_data else self.__last_raw_icx_origin["params"]

    def create_icx_origin(self, is_raw_data=False):
        params = dict()
        params["from"] = self.address
        params["to"] = self.to_address
        params["value"] = hex(int(self.value * ICX_FACTOR))
        params["fee"] = hex(int(self.fee * ICX_FACTOR))
        params["timestamp"] = str(utils.get_now_time_stamp())

        tx_hash = self.__create_hash(params)
        params["tx_hash"] = tx_hash
        params["signature"] = self.__create_signature(tx_hash)

        icx_origin = dict()
        icx_origin["jsonrpc"] = "2.0"
        icx_origin["method"] = "icx_sendTransaction"
        icx_origin["id"] = random.randrange(0, 100000)
        icx_origin["params"] = params
        self.__last_raw_icx_origin = icx_origin

        return icx_origin if is_raw_data else params

    def create_icx_origin_v3(self, is_raw_data=False):
        params = dict()
        params["version"] = "0x3"
        params["from"] = self.address
        params["to"] = self.to_address
        params["value"] = hex(int(self.value * ICX_FACTOR))
        params["stepLimit"] = "0x12345"
        params["timestamp"] = hex(utils.get_now_time_stamp())
        params["nonce"] = "0x0"
        hash_for_sign = self.__create_hash(params)
        params["signature"] = self.__create_signature(hash_for_sign)

        icx_origin = dict()
        icx_origin["jsonrpc"] = "2.0"
        icx_origin["method"] = "icx_sendTransaction"
        icx_origin["id"] = random.randrange(0, 100000)
        icx_origin["params"] = params
        self.__last_raw_icx_origin = icx_origin

        return icx_origin if is_raw_data else params

    def __create_address(self, public_key: PublicKey) -> str:
        serialized_pub = public_key.serialize(compressed=False)
        hashed_pub = hashlib.sha3_256(serialized_pub[1:]).hexdigest()
        return f"hx{hashed_pub[-40:]}"

    def __create_hash(self, icx_origin):
        # gen origin
        gen = self.__gen_ordered_items(icx_origin)
        origin = ".".join(gen)
        origin = f"icx_sendTransaction.{origin}"
        if self.is_logging:
            logging.debug(f"origin data : {origin}")
            logging.debug(f"encode origin : {origin.encode()}")
        # gen hash
        return hashlib.sha3_256(origin.encode()).hexdigest()

    def __create_signature(self, tx_hash):
        signature = self.__private_key.ecdsa_sign_recoverable(msg=binascii.unhexlify(tx_hash),
                                                              raw=True,
                                                              digest=hashlib.sha3_256)
        serialized_sig = self.__private_key.ecdsa_recoverable_serialize(signature)
        if self.is_logging:
            logging.debug(f"serialized_sig : {serialized_sig} "
                          f"\n not_recover_msg size : {sys.getsizeof(serialized_sig[0])}"
                          f"\n len {len(serialized_sig[0])}")
        sig_message = b''.join([serialized_sig[0], bytes([serialized_sig[1]])])
        if self.is_logging:
            logging.debug(f"sig message :{sig_message} "
                          f"\n with_recover_msg size : {sys.getsizeof(sig_message)}"
                          f"\n len {len(sig_message)}"
                          f"\n {type(sig_message[-1])}")
        signature = base64.b64encode(sig_message).decode()
        return signature

    def __gen_ordered_items(self, parameter):
        ordered_keys = list(parameter)
        ordered_keys.sort()
        for key in ordered_keys:
            if self.is_logging:
                logging.debug(f"item : {key}, {parameter[key]}")
            yield key
            if isinstance(parameter[key], str):
                yield parameter[key]
            elif isinstance(parameter[key], dict):
                yield from self.__gen_ordered_items(parameter[key])
            else:
                raise TypeError(f"{key} must be dict or str")

