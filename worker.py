from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)
import time

import zmq

from .proto import (
    MDP_EMPTY,
    MDPW,
    MDPW_HEARTBEAT,
    MDPW_READY,
    MDPW_REPLY,
    MDPW_REQUEST,
    MDPW_DISCONNECT,
)
from .util import (
    make_logger,
    clock_time,
)
from .serialization import default_serializer


class Worker(object):
    def __init__(self, service, endpoint, methods=None, **opts):
        self.ctx = zmq.Context()
        self.socket = None
        self.endpoint = endpoint
        self.service = service
        self.methods = methods or {}
        self.serializer = opts.get("serializer", default_serializer)

        logger_opts = {
            "name": "{}.{}".format(self.__module__, self.__class__.__name__),
            "level": "info",
        }
        logger_opts.update(opts.get("logger_opts", {}))
        self.logger = make_logger(**logger_opts)

        self.heartbeat_at = 0
        self.heartbeat_timeout = opts.get("heartbeat_timeout", 3)
        self.heartbeat_retries = opts.get("heartbeat_retries", 5)
        self.reconnect_timeout = opts.get("reconnect_timeout", 1)
        self.reconnect()

    def disconnect(self):
        self.send_disconnect_msg()
        self.ctx.destroy()
        self.ctx = None
        self.socket = None
        self.methods = {}

    def reconnect(self):
        if self.socket:
            self.socket.close()

        self.logger.info("Establishing a connection to broker")
        self.socket = self.ctx.socket(zmq.DEALER)
        self.socket.setsockopt(zmq.LINGER, 0)
        self.socket.connect(self.endpoint)
        self.send_ready_msg()
        self.heartbeat_at = clock_time() + self.heartbeat_timeout

    def send_ready_msg(self):
        """Sends a message to broker to mark this worker
        as a part of a specific service.
        """
        self.logger.info("Sending READY to broker")
        outgoing = [MDP_EMPTY, MDPW, MDPW_READY, self.service]
        self.socket.send_multipart(outgoing)

    def send_disconnect_msg(self):
        """Sends a message to broker to mark this worker as disconnected.
        """
        msg = [MDP_EMPTY, MDPW, MDPW_DISCONNECT]
        self.socket.send_multipart(msg)

    def send_heartbeat_msg(self):
        msg = [MDP_EMPTY, MDPW, MDPW_HEARTBEAT]
        self.logger.info("Sending HEARTBEAT to broker")
        self.socket.send_multipart(msg)
        self.heartbeat_at = clock_time() + self.heartbeat_timeout

    def send_reply_msg(self, msg):
        """Sends reply to broker.
        """
        client_id = msg[3]
        method = self.serializer.loads(msg[5])
        args = self.serializer.loads(msg[6])
        # TODO: handle error from worker
        result = self.methods[method](*args)

        msg = [
            MDP_EMPTY, MDPW, MDPW_REPLY, client_id,
            MDP_EMPTY, self.serializer.dumps(result),
        ]
        self.logger.info("Sending REPLY to broker")
        self.socket.send_multipart(msg)

    def handle_msg(self, msg):
        cmd = msg[2]
        if cmd == MDPW_REQUEST:
            self.logger.info("Receiving REQUEST from broker")
            self.send_reply_msg(msg)
        elif cmd == MDPW_HEARTBEAT:
            self.logger.info("Receiving HEARTBEAT from broker")
        elif cmd == MDPW_DISCONNECT:
            self.logger.info("Receiving DISCONNECT from broker")
            self.reconnect()

    def run(self):
        try:
            poller = zmq.Poller()
            retries_left = self.heartbeat_retries
            reconnect_timeout = self.reconnect_timeout

            while 1:
                # TODO: send heartbeat X times before reconnecting,
                # where X is self.heartbeat_retries
                poller.register(self.socket, zmq.POLLIN)
                events = dict(poller.poll(self.heartbeat_timeout * 1000))

                if events.get(self.socket) == zmq.POLLIN:
                    msg = self.socket.recv_multipart()
                    self.handle_msg(msg)
                    retries_left = self.heartbeat_retries
                elif not retries_left:
                    # If the worker detects that the broker
                    # has disconnected, it SHOULD restart
                    # a new conversation.
                    self.logger.warn("Broker is unreachable -- reconnecting")
                    time.sleep(reconnect_timeout)
                    poller.register(self.socket, 0)
                    self.send_disconnect_msg()
                    self.reconnect()
                    retries_left = self.heartbeat_retries
                else:
                    retries_left -= 1
                    self.check_heartbeat()
        except:
            self.disconnect()
            raise

    def check_heartbeat(self):
        if clock_time() > self.heartbeat_at:
            self.send_heartbeat_msg()
            self.heartbeat_at = clock_time() + self.heartbeat_timeout
