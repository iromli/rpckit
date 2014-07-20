import random
import time

from rpckit import Client

MESSAGE_CHOICES = (
    "I'm johndoe",
    "I'm janedoe",
)

client = Client("tcp://127.0.0.1:5555")

while True:
    msg = client.send(
        "hello_service",
        "hello",
        args=(random.choice(MESSAGE_CHOICES),),
    )
    print(msg)
    time.sleep(1)
