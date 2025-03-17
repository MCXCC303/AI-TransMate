import time
import os
import hashlib


def by_timestamp():
    current_time = str(time.time()).encode()  # time->byte
    # Use SHA256 to generate
    hash_object = hashlib.sha256(current_time)
    hex_digest = hash_object.hexdigest()
    return hex_digest[:7]


def by_timestamp_with_salt():
    salt = os.urandom(16)
    current_time = str(time.time()).encode()  # time->byte
    # Use SHA256 to generate
    hash_object = hashlib.sha256(current_time + salt)
    hex_digest = hash_object.hexdigest()
    return hex_digest[:7]
