from azure.servicebus.aio import ServiceBusClient
from azure.servicebus import ServiceBusMessage
from azure.servicebus.management import ServiceBusAdministrationClient
import asyncio
from azure.core.exceptions import ResourceNotFoundError

class ServiceBusHandler:
    def __init__(self, connection_string, input_queue_name, output_queue_name):
        self.connection_string = connection_string
        self.servicebus_client = ServiceBusClient.from_connection_string(conn_str=connection_string)
        self.admin_client = ServiceBusAdministrationClient.from_connection_string(connection_string)
        self.input_queue_name = input_queue_name
        self.output_queue_name = output_queue_name


    def _ensure_queues_exist(self):
        self._ensure_queue_exists(self.input_queue_name)
        self._ensure_queue_exists(self.output_queue_name)

    def _ensure_queue_exists(self, queue_name):
        try:
            # Use run_in_executor to run the synchronous method in a separate thread
            self.admin_client.get_queue, queue_name
            print(f"Queue {queue_name} exists.")
        except Exception as e:
            print(f"Queue {queue_name} does not exist. Creating...")
            self.admin_client.create_queue, queue_name

    async def send_message(self, message):
        async with self.servicebus_client:
            sender = self.servicebus_client.get_queue_sender(queue_name=self.input_queue_name)
            async with sender:
                message = ServiceBusMessage(message)
                await sender.send_messages(message)

    async def receive_message(self, timeout=60):
        async with self.servicebus_client:
            receiver = self.servicebus_client.get_queue_receiver(queue_name=self.output_queue_name)
            async with receiver:
                received_msgs = await receiver.receive_messages(max_message_count=1)
                for msg in received_msgs:
                    await receiver.complete_message(msg)
                    return str(msg)
        return None

    async def close(self):
        await self.servicebus_client.close()
