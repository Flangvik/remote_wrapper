import json
import sys
import base64
import zlib
import uuid
import os
import asyncio
import subprocess
import logging
from azure.servicebus import ServiceBusMessage

# Add the path to the remote_wrapper package
remote_wrapper_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'Payload_Type', 'remote_wrapper'))
sys.path.append(remote_wrapper_path)

from remote_wrapper.servicebushelper import ServiceBusHandler
from remote_wrapper.storagehelper import StorageHandler

def read_config(config_file):
    with open(config_file, 'r') as f:
        return json.load(f)

def execute_command(command, payload_message, storage_handler):
    input_file = f"input_{uuid.uuid4()}.bin"
    output_file = f"output_{uuid.uuid4()}.exe"
    input_file_path = os.path.abspath(input_file)
    output_file_path = os.path.abspath(output_file)

    try:
        # Download the payload from the storage account
        payload_bytes = storage_handler.download_bytes(payload_message["payload"])
        
        with open(input_file_path, "wb") as download_file:
            download_file.write(payload_bytes)

        # Replace placeholders in the command
        command = command.replace("{input_file}", input_file_path)
        command = command.replace("{output_file}", output_file_path)

        logging.info(f"Executing command: {command}")
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)

        # Read the output file if it exists
        payload_bytes = None
        if os.path.exists(output_file_path):
            with open(output_file_path, 'rb') as f:
                payload_bytes = f.read()

        # Upload the output file to the storage account
        sas_url = storage_handler.upload_bytes(payload_bytes)

        return sas_url, result.stdout

    except Exception as e:
        logging.error(f"Error: {str(e)}")
        return None, f"Error: {str(e)}"
    finally:
        # Clean up temporary files
        for file_path in (input_file_path, output_file_path):
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except Exception as e:
                    logging.warning(f"Failed to remove temporary file {file_path}: {str(e)}")

async def main(config_file):
    config = read_config(config_file)

    connection_string = config['connection_string']
    input_queue = config['input_queue']
    output_queue = config['output_queue']
    encryption_key = config['encryption_key']
    command = config['command']
    storage_connection_string = config['storage_connection_string']
    storage_container_name = config['storage_container_name']

    servicebus_handler = ServiceBusHandler(connection_string, input_queue, output_queue)
    storage_handler = StorageHandler(storage_connection_string, storage_container_name, encryption_key)

    servicebus_handler._ensure_queues_exist()

    print("Waiting for messages...")
    while True:
        message = await servicebus_handler.receive_message(timeout=5)
        if message:
            base64_payload = base64.b64decode(str(message))
            decompressed_payload = zlib.decompress(base64_payload)
            payload_message = json.loads(decompressed_payload)

            # Execute the command
            payload_url, stdout = execute_command(command, payload_message, storage_handler)

            # Prepare the response
            response = {
                "payload": payload_url,
                "status": "success" if payload_url else "error",
                "error": stdout
            }

            # Compress and encode the response
            compressed_response = base64.b64encode(zlib.compress(json.dumps(response).encode())).decode()

            # Send the response
            await servicebus_handler.send_message(compressed_response)
            print("Response sent")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python remote_wrapper_client.py <config_file>")
        sys.exit(1)
    

    asyncio.run(main(sys.argv[1]))
