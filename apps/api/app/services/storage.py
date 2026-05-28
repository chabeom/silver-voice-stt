import os
from pathlib import Path
from urllib.parse import quote

import boto3
from botocore.client import Config
from botocore.exceptions import BotoCoreError, ClientError

from app.core.config import get_settings


class StorageService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.backend = self.settings.storage_backend
        self.local_root = Path(self.settings.local_storage_path)
        if self.backend == "minio":
            self.client = self._create_s3_client(self.settings.minio_endpoint)
            self.public_client = self._create_s3_client(self.settings.minio_public_endpoint)
        else:
            self.client = None
            self.public_client = None
            self.local_root.mkdir(parents=True, exist_ok=True)

    def _create_s3_client(self, endpoint: str):
        return boto3.client(
            "s3",
            endpoint_url=f"http{'s' if self.settings.minio_secure else ''}://{endpoint}",
            aws_access_key_id=self.settings.minio_access_key,
            aws_secret_access_key=self.settings.minio_secret_key,
            config=Config(signature_version="s3v4"),
            region_name="us-east-1",
        )

    def ensure_bucket(self) -> None:
        if self.backend != "minio":
            self.local_root.mkdir(parents=True, exist_ok=True)
            return
        try:
            buckets = self.client.list_buckets().get("Buckets", [])
            if not any(bucket["Name"] == self.settings.minio_bucket for bucket in buckets):
                self.client.create_bucket(Bucket=self.settings.minio_bucket)
        except (BotoCoreError, ClientError):
            return

    def upload_bytes(self, *, object_key: str, data: bytes, content_type: str) -> None:
        if self.backend == "minio":
            self.client.put_object(
                Bucket=self.settings.minio_bucket,
                Key=object_key,
                Body=data,
                ContentType=content_type,
            )
            return

        target_path = self.local_root / object_key
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_bytes(data)

    def download_file(self, *, object_key: str, target_path: str) -> str:
        if self.backend == "minio":
            self.client.download_file(self.settings.minio_bucket, object_key, target_path)
            return target_path

        source = self.local_root / object_key
        Path(target_path).write_bytes(source.read_bytes())
        return target_path

    def delete_file(self, *, object_key: str | None) -> bool:
        if not object_key:
            return False

        if self.backend == "minio":
            try:
                self.client.delete_object(Bucket=self.settings.minio_bucket, Key=object_key)
                return True
            except (BotoCoreError, ClientError):
                return False

        target_path = self.local_root / object_key
        try:
            if target_path.exists():
                target_path.unlink()
                return True
        except OSError:
            return False
        return False

    def create_presigned_get_url(self, *, object_key: str, expires_in: int = 3600) -> str:
        if self.backend == "minio":
            return self.public_client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.settings.minio_bucket, "Key": object_key},
                ExpiresIn=expires_in,
            )
        abs_path = (self.local_root / object_key).resolve()
        return f"file:///{quote(str(abs_path).replace(os.sep, '/'))}"
