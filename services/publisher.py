import json

from nats.js.client import JetStreamContext


async def send_publisher_data(
    js: JetStreamContext,
    subject: str,
    data: dict
) -> None:
    print('start_transfer')
    await js.publish(subject=subject, payload=json.dumps(data).encode())