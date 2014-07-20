from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)

import msgpack


class MsgPackSerializer(object):
    """Handles serializing/deserializing using msgpack.
    """
    @staticmethod
    def dumps(data):
        return msgpack.packb(data)

    @staticmethod
    def loads(value):
        return msgpack.unpackb(value)


default_serializer = MsgPackSerializer
