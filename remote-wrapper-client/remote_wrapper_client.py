import json
import sys
import base64
import zlib
import uuid
import os
import subprocess
import logging
from azure.servicebus import ServiceBusClient, ServiceBusMessage

def read_config(config_file):
    with open(config_file, 'r') as f:
        return json.load(f)

def execute_command(command, payload_message):
    input_file = f"input_{uuid.uuid4()}.bin"
    output_file = f"output_{uuid.uuid4()}.exe"
    input_file_path = os.path.abspath(input_file)
    output_file_path = os.path.abspath(output_file)

    try:
        # Write the payload_message to the input_file
        with open(input_file_path, 'wb') as f:
            f.write(zlib.decompress(base64.b64decode(payload_message["payload"])))

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

        return payload_bytes, result.stdout

    except zlib.error as e:
        logging.error(f"Failed to decompress payload: {str(e)}")
        return None, f"Error: Failed to decompress payload - {str(e)}"
    except base64.binascii.Error as e:
        logging.error(f"Failed to decode base64 payload: {str(e)}")
        return None, f"Error: Failed to decode base64 payload - {str(e)}"
    except IOError as e:
        logging.error(f"I/O error: {str(e)}")
        return None, f"Error: I/O error - {str(e)}"
    except subprocess.CalledProcessError as e:
        logging.error(f"Command execution failed: {e.stderr}")
        return None, f"Error: Command execution failed - {e.stderr}"
    except Exception as e:
        logging.error(f"Unexpected error: {str(e)}")
        return None, f"Error: Unexpected error occurred - {str(e)}"
    finally:
        # Clean up temporary files
        for file_path in (input_file_path, output_file_path):
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except Exception as e:
                    logging.warning(f"Failed to remove temporary file {file_path}: {str(e)}")

def main(config_file):
    config = read_config(config_file)

    connection_string = config['connection_string']
    input_queue = config['input_queue']
    output_queue = config['output_queue']
    command = config['command']

    servicebus_client = ServiceBusClient.from_connection_string(connection_string)

    with servicebus_client:
        receiver = servicebus_client.get_queue_receiver(queue_name=input_queue)
        sender = servicebus_client.get_queue_sender(queue_name=output_queue)

        with receiver, sender:
            print("Waiting for messages...")
            while True:
                received_msgs = receiver.receive_messages(max_message_count=1, max_wait_time=5)
                for message in received_msgs:

                    base64_payload = base64.b64decode(str(message))
                    
                    decompressed_payload = zlib.decompress(base64_payload)

                    payload_message = json.loads(decompressed_payload)

                    # Execute the command
                    payload_bytes, stdout = execute_command(command, payload_message)

                    # Prepare the response, only encode if the payload is not None
                    response = {
                        "payload": base64.b64encode(payload_bytes).decode() if payload_bytes else None,
                        "status": "success" if payload_bytes else "error",
                        "error": stdout
                    }

                    # Compress and encode the response
                    compressed_response = base64.b64encode(zlib.compress(json.dumps(response).encode())).decode()

                    # Send the response
                    sender.send_messages(ServiceBusMessage(compressed_response))
                    print("Response sent")

                    # Complete the message
                    receiver.complete_message(message)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python remote_wrapper_client.py <config_file>")
        sys.exit(1)
    
    main(sys.argv[1])
