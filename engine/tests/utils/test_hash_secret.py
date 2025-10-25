import logging

from tangl.utils.hash_secret import uuid_for_secret, key_for_secret, uuid_for_key, hash_for_secret

def test_hash_for_secret():
    h = hash_for_secret("secret phrase!")
    logging.debug( h )
    logging.debug( hash_for_secret("secret phrase!")[:16] )
    u = uuid_for_secret("secret phrase!")
    logging.debug( u )
    key = key_for_secret("secret phrase!")
    logging.debug( key )
    u2 = uuid_for_key(key)
    logging.debug( u2 )
    assert u == u2
