from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)
from collections import (
    defaultdict,
    deque,
    namedtuple,
)
from itertools import chain

import zmq

from .proto import (
    MDP_EMPTY,
    MDPC,
    MDPW,
    MDPW_DISCONNECT,
    MDPW_HEARTBEAT,
    MDPW_READY,
    MDPW_REPLY,
    MDPW_REQUEST,
)
from .util import make_logger, clock_time


WorkerProxy = namedtuple("WorkerProxy", ["id", "service"])


class Broker(object):
    def __init__(self, endpoint, **opts):
        self.ctx = zmq.Context()
        self.socket = self.ctx.socket(zmq.ROUTER)
        self.endpoint = endpoint
        self.socket.bind(self.endpoint)

        self.workers = {}
        self.services = defaultdict(deque)

        logger_opts = {
            "name": "{}.{}".format(self.__module__, self.__class__.__name__),
            "level": "info",
        }
        logger_opts.update(opts.get("logger_opts", {}))
        self.logger = make_logger(**logger_opts)

        self.heartbeat_timeout = opts.get("heartbeat_timeout", 3)
        self.heartbeat_at = clock_time() + self.heartbeat_timeout

    def disconnect(self):
        self.ctx.destroy()
        self.ctx = None
        self.socket = None
        self.workers = {}
        self.services = defaultdict(deque)

    def handle_worker_msg(self, worker_id, msg):
        cmd = msg[2]
        if cmd == MDPW_READY:
            self.handle_ready_msg(worker_id, msg)
        elif cmd == MDPW_DISCONNECT:
            self.handle_disconnect_msg(worker_id)
        elif cmd == MDPW_HEARTBEAT:
            self.handle_heartbeat_msg(worker_id)
        elif cmd == MDPW_REPLY:
            self.handle_reply_msg(worker_id, msg)

    def handle_client_msg(self, client_id, msg):
        """Handles incoming message from client, pass it to appropriate worker.
        """
        service = msg[2]
        if service in self.services and len(self.services[service]):
            worker_id = self.services[service].popleft()
            msg.insert(0, client_id)
            self.send_request_msg(worker_id, msg)
            self.services[service].append(worker_id)
        else:
            # TODO: should queue the request, and hands it
            # when service is available
            self.logger.info(
                "Client is requesting non-existant service {!r}".format(
                    service))
            msg.insert(0, client_id)

    def run(self):
        try:
            poller = zmq.Poller()
            self.logger.info("Starting broker")

            while 1:
                poller.register(self.socket, zmq.POLLIN)
                events = dict(poller.poll(self.heartbeat_timeout * 1000))

                if events.get(self.socket) == zmq.POLLIN:
                    msg = self.socket.recv_multipart()
                    sender = msg.pop(0)
                    self.handle_msg(sender, msg)
                else:
                    self.check_heartbeat()
        except:
            # poller.register(self.socket, 0)
            self.disconnect()
            raise

    def send_heartbeat_msg(self, worker_id):
        outgoing = [worker_id, MDP_EMPTY, MDPW, MDPW_HEARTBEAT]
        self.logger.info("Sending HEARTBEAT to worker {!r}".format(worker_id))
        self.socket.send_multipart(outgoing)

    def send_request_msg(self, worker_id, msg):
        outgoing = [
            worker_id,
            MDP_EMPTY,   # frame 0
            MDPW,
            MDPW_REQUEST,
            msg[0],
            MDP_EMPTY,
            msg[4],
            msg[5],
        ]
        self.logger.info("Sending REQUEST to worker {!r}".format(
            worker_id
        ))
        self.socket.send_multipart(outgoing)

    def check_heartbeat(self):
        if clock_time() > self.heartbeat_at:
            # send heartbeat to idle workers
            for worker_id in chain(*self.services.itervalues()):
                self.send_heartbeat_msg(worker_id)
            self.heartbeat_at = clock_time() + self.heartbeat_timeout

    def handle_msg(self, sender, msg):
        try:
            header = msg[1]
            if header == MDPW:
                self.handle_worker_msg(sender, msg)
            elif header == MDPC:
                self.handle_client_msg(sender, msg)
        except IndexError:
            # no header (MDPW or MDPC)
            pass

    def handle_disconnect_msg(self, worker_id, disconnected=False):
        if worker_id in self.workers:
            worker = self.workers.pop(worker_id)
            service = worker.service
            self.services[service].remove(worker_id)

            if not len(self.services[service]):
                del self.services[service]

            self.logger.info("Receiving DISCONNECT from worker {!r}".format(
                worker_id
            ))

    def handle_reply_msg(self, worker_id, msg):
        if worker_id in self.workers:
            client_id = msg[3]
            service = self.workers[worker_id].service
            outgoing = [client_id, MDP_EMPTY, MDPC, service, msg[-1]]
            self.logger.info("Receiving REPLY from worker {!r}".format(
                worker_id
            ))
            self.socket.send_multipart(outgoing)

    def handle_ready_msg(self, worker_id, msg):
        if not worker_id in self.workers:
            service = msg[3]
            worker = WorkerProxy(worker_id, service)
            self.workers[worker_id] = worker
            self.services[service].append(worker_id)
            self.logger.info(
                "Receiving READY from worker {!r}".format(worker_id))

    def handle_heartbeat_msg(self, worker_id):
        self.logger.info(
            "Receiving HEARTBEAT from worker {!r}".format(worker_id))
