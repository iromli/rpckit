from rpckit import Worker


def hello(msg):
    print("got message: {}".format(msg))
    return "OK {}".format(msg.split()[-1])

worker = Worker(
    "hello_service",
    "tcp://127.0.0.1:5555",
    {"hello": hello},
)
worker.run()
