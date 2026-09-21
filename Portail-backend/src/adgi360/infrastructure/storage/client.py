"""Client de stockage compatible S3 (MinIO en local, AWS S3 en production).

L'API S3 étant identique des deux côtés, passer de MinIO à un vrai bucket S3
ne demandera que de changer les variables d'environnement.
"""

import asyncio
from functools import lru_cache

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from adgi360.infrastructure.config.settings import settings
from adgi360.shared.exceptions import ExternalServiceError


@lru_cache(maxsize=4)
def _s3_client(endpoint_url: str | None = None):
    """Un client par endpoint. Les URL pré-signées portent l'hôte dans leur
    signature : pour qu'une URL soit valide depuis un conteneur n8n, il faut
    l'avoir signée avec l'endpoint que ce conteneur utilisera."""
    return boto3.client(
        "s3",
        endpoint_url=endpoint_url or settings.s3_endpoint_url,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        region_name=settings.s3_region,
        config=Config(signature_version="s3v4"),
    )


class FileStorage:
    """Opérations de stockage. Les appels boto3 sont synchrones : ils sont
    déportés dans un thread pour ne pas bloquer la boucle asyncio de FastAPI."""

    def __init__(self, bucket: str | None = None) -> None:
        self._bucket = bucket or settings.s3_bucket

    async def ensure_bucket(self) -> None:
        """Crée le bucket s'il n'existe pas (idempotent)."""

        def _run() -> None:
            client = _s3_client()
            try:
                client.head_bucket(Bucket=self._bucket)
            except ClientError:
                client.create_bucket(Bucket=self._bucket)

        try:
            await asyncio.to_thread(_run)
        except Exception as exc:  # pragma: no cover - dépend de l'infra
            raise ExternalServiceError(f"Stockage indisponible : {exc}") from exc

    async def upload(self, key: str, content: bytes, content_type: str | None = None) -> str:
        def _run() -> None:
            extra = {"ContentType": content_type} if content_type else {}
            _s3_client().put_object(Bucket=self._bucket, Key=key, Body=content, **extra)

        try:
            await asyncio.to_thread(_run)
        except Exception as exc:
            raise ExternalServiceError(f"Échec de l'upload de {key} : {exc}") from exc
        return key

    async def download(self, key: str) -> bytes:
        def _run() -> bytes:
            response = _s3_client().get_object(Bucket=self._bucket, Key=key)
            return response["Body"].read()

        try:
            return await asyncio.to_thread(_run)
        except Exception as exc:
            raise ExternalServiceError(f"Échec du téléchargement de {key} : {exc}") from exc

    async def delete(self, key: str) -> None:
        def _run() -> None:
            _s3_client().delete_object(Bucket=self._bucket, Key=key)

        try:
            await asyncio.to_thread(_run)
        except Exception as exc:
            raise ExternalServiceError(f"Échec de la suppression de {key} : {exc}") from exc

    async def list_keys(self, prefix: str) -> list[dict]:
        """Liste les objets sous un préfixe. Utilisé pour détecter les rapports
        déposés par n8n."""

        def _run() -> list[dict]:
            paginator = _s3_client().get_paginator("list_objects_v2")
            items: list[dict] = []
            for page in paginator.paginate(Bucket=self._bucket, Prefix=prefix):
                for obj in page.get("Contents", []):
                    items.append(
                        {
                            "key": obj["Key"],
                            "size": obj["Size"],
                            "last_modified": obj["LastModified"],
                        }
                    )
            return items

        try:
            return await asyncio.to_thread(_run)
        except Exception as exc:
            raise ExternalServiceError(f"Échec du listing sur {prefix} : {exc}") from exc

    async def presigned_url(
        self, key: str, expires_in: int = 3600, endpoint_url: str | None = None
    ) -> str:
        """URL temporaire de téléchargement direct, utile pour le frontend.

        `endpoint_url` permet de signer pour un autre consommateur que le
        navigateur — typiquement le conteneur n8n, qui ne résout pas localhost.
        """

        target = endpoint_url or settings.s3_public_endpoint_url or None

        def _run() -> str:
            return _s3_client(target).generate_presigned_url(
                "get_object",
                Params={"Bucket": self._bucket, "Key": key},
                ExpiresIn=expires_in,
            )

        try:
            return await asyncio.to_thread(_run)
        except Exception as exc:
            raise ExternalServiceError(f"Échec de génération d'URL pour {key} : {exc}") from exc


def get_storage() -> FileStorage:
    """Dépendance FastAPI."""
    return FileStorage()
