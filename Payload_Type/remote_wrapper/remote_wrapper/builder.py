from mythic_container.PayloadBuilder import *
from mythic_container.MythicCommandBase import *
import asyncio
import os
import tempfile
import json
import zlib
from distutils.dir_util import copy_tree
from pathlib import PurePath
import base64
from mythic_container.MythicRPC import *
from remote_wrapper.servicebushelper import ServiceBusHandler

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
        ),
        BuildParameter(
            name="request_queue_name",
            parameter_type=BuildParameterType.String,
            description="The name of the queue for payload build requests",
            default_value="payload_build_requests",
        ),
        BuildParameter(
            name="response_queue_name",
            parameter_type=BuildParameterType.String,
            description="The name of the queue for payload build responses",
            default_value="payload_build_responses",
        )
    ]
    c2_profiles = []
    agent_path = PurePath(".") / "remote_wrapper"
    agent_icon_path = agent_path / "service_wrapper.svg"
    agent_code_path = agent_path / "agent_code"

    build_steps = [
        BuildStep(step_name="Send Request", step_description="Sending payload wrapper request to remote host"),
        BuildStep(step_name="Build", step_description="Waiting for response from remote host"),
        BuildStep(step_name="Receive Binary", step_description="Receiving compiled binary from remote host")
    ]


    async def build(self) -> BuildResponse:
        # this function gets called to create an instance of your payload
        resp = BuildResponse(status=BuildStatus.Error)
        output = ""
        try:

            # Send Request step
            await SendMythicRPCPayloadUpdatebuildStep(MythicRPCPayloadUpdateBuildStepMessage(
                PayloadUUID=self.uuid,
                StepName="Send Request",
                StepStdout="Sent payload wrapper request to Azure Service Bus",
                StepSuccess=True
            ))

            ## Establish a new servicebus connection
            servicebus_connection = ServiceBusHandler(self.get_parameter("service_bus_connection_string"), self.get_parameter("request_queue_name"), self.get_parameter("response_queue_name"))
            
            servicebus_connection._ensure_queues_exist()
            ## Generate a new payload message object
            payload_message = {
                "payload_type": self.name,
                "build_parameters": self.get_parameter_dict(),
                "payload": self.wrapped_payloads[0] if self.wrapped_payloads else None
            }

            serialized_payload = json.dumps(payload_message)
            compressed_payload = zlib.compress(serialized_payload.encode())
            base64_payload = base64.b64encode(compressed_payload).decode()

            ## Push it down the correct thing
            await servicebus_connection.send_message(base64_payload)

            # Build step
            await SendMythicRPCPayloadUpdatebuildStep(MythicRPCPayloadUpdateBuildStepMessage(
                PayloadUUID=self.uuid,
                StepName="Build",
                StepStdout="Waiting for response from remote host",
                StepSuccess=True
            ))
          
            
            ## Wait for the response
            response = await servicebus_connection.receive_message(timeout=300)  # 5 minutes timeout
            final_status = False

            if response:
                base64_payload = base64.b64decode(str(response))
                    
                decompressed_payload = zlib.decompress(base64_payload)

                response_data = json.loads(decompressed_payload)
                # check if success is true
                if response_data['status'] == 'success':
                    payload_bytes = base64.b64decode(response_data['payload'])
                    final_status = True
                else:
                    error_msg = response_data['error']
                    final_status = False
                    raise Exception(f"Remote host returned an error: {response_data['error']}")

              

                resp.payload = payload_bytes
                resp.status = BuildStatus.Success if final_status else BuildStatus.Error
                # if final_status is true, set the build message to "New Service Executable created!", if not set it to the error message
                resp.build_message = "New Service Executable created!" if final_status else error_msg

                # Receive Binary step
                await SendMythicRPCPayloadUpdatebuildStep(MythicRPCPayloadUpdateBuildStepMessage(
                    PayloadUUID=self.uuid,
                    StepName="Receive Binary",
                    StepStdout="Received compiled binary from remote host",
                    StepSuccess=final_status
                ))


        except Exception as e:
            raise Exception(str(e) + "\n" + output)
        return resp
