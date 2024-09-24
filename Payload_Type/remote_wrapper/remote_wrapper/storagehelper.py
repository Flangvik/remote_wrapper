from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient
import uuid
from datetime import datetime, timedelta
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
import base64

class StorageHandler:
    def __init__(self, connection_string, container_name, encryption_key):
        self.connection_string = connection_string
        self.container_name = container_name
        ## Validate the connection string, and wait for the container to be created
        try:
            self.blob_service_client = BlobServiceClient.from_connection_string(self.connection_string)
            self.container_client = self.blob_service_client.get_container_client(self.container_name)
        except Exception as e:
            print(f"Error: {str(e)}")
            raise
        self.encryption_key = encryption_key.encode('utf-8')

    def _ensure_container_exists(self):
        try:
            self.container_client.get_container_properties()
        except Exception:
            self.container_client.create_container()

    def upload_bytes(self, data):
        self._ensure_container_exists()
        blob_name = str(uuid.uuid4())
        
        # Encrypt the data
        encrypted_data, iv = self._encrypt_data(data)
        
        # Combine IV and encrypted data
        data_to_upload = iv + encrypted_data
        
        blob_client = self.container_client.get_blob_client(blob_name)
        blob_client.upload_blob(data_to_upload)

        return blob_name

    def download_bytes(self, blob_name):
        blob_client = self.container_client.get_blob_client(blob_name)
        encrypted_data = blob_client.download_blob().readall()
        
        # Extract IV and decrypt the data
        iv = encrypted_data[:16]
        data = encrypted_data[16:]
        decrypted_data = self._decrypt_data(data, iv)
        
        return decrypted_data

    def _encrypt_data(self, data):
        iv = get_random_bytes(16)
        cipher = AES.new(self.encryption_key, AES.MODE_CBC, iv)
        padded_data = self._pad(data)
        encrypted_data = cipher.encrypt(padded_data)
        return encrypted_data, iv

    def _decrypt_data(self, encrypted_data, iv):
        cipher = AES.new(self.encryption_key, AES.MODE_CBC, iv)
        decrypted_data = cipher.decrypt(encrypted_data)
        return self._unpad(decrypted_data)

    @staticmethod
    def _pad(s):
        block_size = AES.block_size
        return s + (block_size - len(s) % block_size) * chr(block_size - len(s) % block_size).encode()

    @staticmethod
    def _unpad(s):
        return s[:-ord(s[len(s)-1:])]
