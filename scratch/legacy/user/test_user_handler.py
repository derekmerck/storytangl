import logging

from tangl.user.user_handler import UserHandler
from tangl.utils.uuid_for_secret import uuid_for_secret


def test_create_user():

    user = UserHandler.create_user("blah")
    logging.debug( user.model_dump() )


def test_user_secret():

    secret = "my secret"
    us = UserHandler.get_key_for_secret(secret)
    logging.debug( us )
    assert us.user_secret == secret
    assert us.user_id == uuid_for_secret(secret)