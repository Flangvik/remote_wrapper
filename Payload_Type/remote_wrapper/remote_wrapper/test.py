import asyncio
import json
import zlib
import sys
import base64

from servicebushelper import ServiceBusHandler

async def test_servicebus():
    # Connection string and queue names (replace with your actual values)
    # read the connection string from a txt file calld dont_show_on_stream.txt
    connection_string = open("dont_show_on_stream.txt", "r").read()
    request_queue_name = "payload_build_requests"
    response_queue_name = "payload_build_responses"

    # Create ServiceBus instance
    servicebus_connection = ServiceBusHandler(connection_string, request_queue_name, response_queue_name)

    servicebus_connection._ensure_queues_exist()
    # Generate a payload message similar to builder.py
    payload_message = {
        "payload_type": "remote_wrapper",
        "build_parameters": {
            "arch": "x64",
            "service_bus_connection_string": connection_string,
            "request_queue_name": request_queue_name,
            "response_queue_name": response_queue_name
        },
        #Base64 encoded payload, take the file bytes based on the path given as the  first argument
        "payload": base64.b64encode(zlib.compress(open(sys.argv[1], "rb").read())).decode()
    }

    serialized_payload = json.dumps(payload_message)
    compressed_payload = zlib.compress(serialized_payload.encode())
    base64_payload = base64.b64encode(compressed_payload).decode()

    # Send the message
    print("Sending message...")
    await servicebus_connection.send_message(base64_payload)
    print("Message sent.")

    # Receive the response
    print("Waiting for response...")
    response = await servicebus_connection.receive_message(timeout=30)  # 30 seconds timeout

    if response:
        print("Response received.")
        decompressed_response = zlib.decompress(base64.b64decode(response))
        response_data = json.loads(decompressed_response)
        print("Response data:", response_data)
    else:
        print("No response received within the timeout period.")

    # Close the connection
    await servicebus_connection.close()

if __name__ == "__main__":
    asyncio.run(test_servicebus())
