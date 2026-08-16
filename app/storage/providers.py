import asyncio
import os
import re
import uuid
from pathlib import Path
from typing import Protocol

import boto3
from botocore.config import Config

from app.core.config import Settings, get_settings

_SAFE_KEY_PART = re.compile(r"^[A-Za-z0-9._-]+$")


def _key_parts(key: str) -> tuple[str, ...]:
    parts = key.split("/")
    if (
        not key
        or key.startswith("/")
        or "\\" in key
        or any(
            not part or part in {".", ".."} or not _SAFE_KEY_PART.fullmatch(part)
            for part in parts
        )
    ):
        raise ValueError("Invalid object storage key")
    return tuple(parts)


class StorageProvider(Protocol):
    async def upload(self, key: str, data: bytes, content_type: str) -> None: ...

    async def read(self, key: str) -> bytes: ...

    async def delete(self, key: str) -> None: ...

    async def create_download_url(self, key: str, expires_in: int) -> str: ...


class LocalStorageProvider:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    def _path(self, key: str) -> Path:
        path = self.root.joinpath(*_key_parts(key)).resolve()
        if not path.is_relative_to(self.root):
            raise ValueError("Object storage key escapes the storage root")
        return path

    async def upload(self, key: str, data: bytes, content_type: str) -> None:
        path = self._path(key)

        def write() -> None:
            path.parent.mkdir(parents=True, exist_ok=True)
            temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
            try:
                with temporary.open("xb") as output:
                    output.write(data)
                os.replace(temporary, path)
            finally:
                temporary.unlink(missing_ok=True)

        await asyncio.to_thread(write)

    async def read(self, key: str) -> bytes:
        return await asyncio.to_thread(self._path(key).read_bytes)

    async def delete(self, key: str) -> None:
        await asyncio.to_thread(self._path(key).unlink, missing_ok=True)

    async def create_download_url(self, key: str, expires_in: int) -> str:
        raise RuntimeError("Local storage objects use the authenticated content endpoint")


class S3StorageProvider:
    def __init__(self, settings: Settings) -> None:
        missing = [
            name
            for name, value in (
                ("S3_BUCKET", settings.s3_bucket),
                ("S3_ACCESS_KEY", settings.s3_access_key),
                ("S3_SECRET_KEY", settings.s3_secret_key),
            )
            if not value
        ]
        if missing:
            raise RuntimeError(f"S3 storage configuration is incomplete: {', '.join(missing)}")
        self.bucket = settings.s3_bucket
        self.client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint or None,
            region_name=settings.s3_region,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            config=Config(
                signature_version="s3v4",
                connect_timeout=settings.s3_connect_timeout_seconds,
                read_timeout=settings.s3_read_timeout_seconds,
                retries={"max_attempts": 3, "mode": "standard"},
            ),
        )

    async def upload(self, key: str, data: bytes, content_type: str) -> None:
        key = "/".join(_key_parts(key))
        await asyncio.to_thread(
            self.client.put_object,
            Bucket=self.bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
        )

    async def read(self, key: str) -> bytes:
        key = "/".join(_key_parts(key))
        response = await asyncio.to_thread(
            self.client.get_object,
            Bucket=self.bucket,
            Key=key,
        )
        body = response["Body"]
        try:
            return await asyncio.to_thread(body.read)
        finally:
            await asyncio.to_thread(body.close)

    async def delete(self, key: str) -> None:
        key = "/".join(_key_parts(key))
        await asyncio.to_thread(self.client.delete_object, Bucket=self.bucket, Key=key)

    async def create_download_url(self, key: str, expires_in: int) -> str:
        key = "/".join(_key_parts(key))
        if expires_in <= 0:
            raise ValueError("Download URL expiry must be positive")
        return await asyncio.to_thread(
            self.client.generate_presigned_url,
            "get_object",
            Params={"Bucket": self.bucket, "Key": key},
            ExpiresIn=expires_in,
        )


def make_storage_key(clinic_id: uuid.UUID, patient_id: uuid.UUID) -> str:
    clinic = uuid.UUID(str(clinic_id))
    patient = uuid.UUID(str(patient_id))
    return f"clinics/{clinic}/patients/{patient}/xrays/{uuid.uuid4().hex}"


def storage_provider() -> StorageProvider:
    settings = get_settings()
    provider = settings.object_storage_provider.strip().lower()
    if provider == "local":
        return LocalStorageProvider(settings.local_storage_path)
    if provider == "s3":
        return S3StorageProvider(settings)
    raise RuntimeError(f"Unsupported OBJECT_STORAGE_PROVIDER: {provider}")
