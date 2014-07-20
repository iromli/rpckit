from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)

# there's also ``b`` as a shortcut to ``zmq.utils.strtypes.asbytes``,
# but as it MIGHT confuses readers, use the longname instead
from zmq.utils.strtypes import asbytes

MDP_EMPTY = asbytes("")
MDPC = asbytes("MDPC01")
MDPW = asbytes("MDPW01")
MDPW_READY = asbytes("\x01")
MDPW_REQUEST = asbytes("\x02")
MDPW_REPLY = asbytes("\x03")
MDPW_HEARTBEAT = asbytes("\x04")
MDPW_DISCONNECT = asbytes("\x05")
