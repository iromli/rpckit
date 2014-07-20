from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)

import zmq
from zmq.utils.strtypes import asbytes

from .exc import ConnectionError
from .proto import MDPC, MDP_EMPTY
from .util import make_logger
from .serialization import default_serializer


class Client(object):
    def __init__(self, endpoint, **opts):
        self.ctx = None
        self.endpoint = endpoint
        self.socket = None
        self.serializer = opts.get("serializer", default_serializer)

        logger_opts = {
            "name": "{}.{}".format(self.__module__, self.__class__.__name__),
            "level": "info",
        }
        logger_opts.update(opts.get("logger_opts", {}))
        self.logger = make_logger(**logger_opts)

        self.timeout = opts.get("timeout", 5)
        self.retries = opts.get("retries", 5)

    def reconnect(self):
        """Reconnects to broker.

        If a connection is already established, close it first before
        reconnecting.
        """
        if self.socket:
            self.socket.close()

        self.ctx = zmq.Context()
        self.socket = self.ctx.socket(zmq.DEALER)
        self.socket.setsockopt(zmq.LINGER, 0)
        self.socket.connect(self.endpoint)
        self.logger.info("Trying to establish a connection to broker")

    def disconnect(self):
        """Closes context and its socket connection.
        """
        self.ctx.destroy()
        self.ctx = None
        self.socket = None

    def send(self, service, func, args, timeout=None, retries=None):
        if not self.socket:
            self.reconnect()

        msg = [
            MDP_EMPTY,
            MDPC,
            asbytes(service),
            self.serializer.dumps(func),
            self.serializer.dumps(args),
        ]
        self.socket.send_multipart(msg)

        try:
            poller = zmq.Poller()
            retries_left = retries or self.retries
            timeout = timeout or self.timeout
            while 1:
                poller.register(self.socket, zmq.POLLIN)
                # wait for incoming response from broker
                events = dict(poller.poll(self.timeout * 1000))

                if events.get(self.socket) == zmq.POLLIN:
                    retries_left = self.retries
                    msg = self.socket.recv_multipart()
                    result = self.serializer.loads(msg[-1])
                    return result

                if not retries_left:
                    raise ConnectionError("Connection to broker is lost")

                retries_left -= 1
                self.logger.warn("No reply from broker")
                poller.register(self.socket, 0)
                self.reconnect()
        except:
            self.disconnect()
            raise
