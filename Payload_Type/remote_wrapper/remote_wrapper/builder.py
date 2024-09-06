from mythic_container.PayloadBuilder import *
from mythic_container.MythicCommandBase import *
import asyncio
import os
import servicebus
import tempfile
import json
import zlib
from distutils.dir_util import copy_tree
from pathlib import PurePath
import base64
from mythic_container.MythicRPC import *

class RemoteWrapper(PayloadType):

    name = "remote_wrapper"
    file_extension = "exe"
    author = "@flangvik"
    supported_os = [SupportedOS.Windows]
    wrapper = True
    wrapped_payloads = []
    note = "This is a wrapper payload that allows payload wrapping to occur fully on a remote host. It uses Azure Service Bus for communication between Mythic and the remote host."
    supports_dynamic_loading = False
    build_parameters = [
        BuildParameter(
            name="arch",
            parameter_type=BuildParameterType.ChooseOne,
            choices=["x64", "Any CPU"],
            default_value="x64",
            description="Target architecture",
        ),
        BuildParameter(
            name="service_bus_connection_string",
            parameter_type=BuildParameterType.String,
            description="The connection string for the Azure Service Bus",
            default_value="",
        )
    ]
    c2_profiles = []
    agent_path = PurePath(".") / "remote_wrapper"
    agent_icon_path = agent_path / "remote_wrapper.svg"
    agent_code_path = agent_path / "agent_code"
    build_steps = [
        BuildStep(step_name="Sending Payload Wrapper Request", step_description="")
        BuildStep(step_name="Building (Waiting for response)", step_description="")
        BuildStep(step_name="Recived Compiled Binary", step_description="")
    ]


    async def build(self) -> BuildResponse:
        # this function gets called to create an instance of your payload
        resp = BuildResponse(status=BuildStatus.Error)
        output = ""
        try:
            ## Establish a new servicebus connection
            servicebusConnection = servicebus()

            ## Generate a new payload message object
            payload_message = {
                "payload_type": self.name,
                "build_parameters": self.get_parameter_dict(),
                "wrapped_payload": self.wrapped_payloads[0] if self.wrapped_payloads else None
            }



            serialized_payload = json.dumps(payload_message)
            compressed_payload = zlib.compress(serialized_payload.encode())
            base64_payload = base64.b64encode(compressed_payload).decode()

            ## Push it down the correct thing
            queue_name = "payload_build_requests"
            servicebusConnection.send_message(queue_name, base64_payload)

            ## Wait for the response
            response_queue = "payload_build_responses"
            response = servicebusConnection.receive_message(response_queue, timeout=300)  # 5 minutes timeout

            if response:
                decompressed_response = zlib.decompress(base64.b64decode(response))
                response_data = json.loads(decompressed_response)
                payload_bytes = base64.b64decode(response_data['payload'])
        except Exception as e:
            raise Exception(str(e) + "\n" + output)
        return resp
