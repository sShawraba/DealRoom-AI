"""
scripts/backup.py
=================
Dump the Postgres database, compress it, and upload to MinIO.

Usage:
    DATABASE_URL=postgresql://... python scripts/backup.py
"""
import datetime
import gzip
import os
import subprocess
import sys

import boto3
from botocore.exceptions import BotoCoreError, ClientError

DATABASE_URL = os.environ.get("DATABASE_URL", "")
MINIO_ENDPOINT = os.environ.get("MINIO_ENDPOINT", "http://minio:9000")
MINIO_BUCKET = os.environ.get("MINIO_BUCKET", "dealroom-documents")
MINIO_ACCESS_KEY = os.environ.get("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.environ.get("MINIO_SECRET_KEY", "minioadmin")


def backup() -> None:
    if not DATABASE_URL:
        print("ERROR: DATABASE_URL not set", file=sys.stderr)
        sys.exit(1)

    ts = datetime.datetime.utcnow().strftime("%Y-%m-%d-%H")
    print(f"Starting backup {ts} ...")

    result = subprocess.run(
        ["pg_dump", DATABASE_URL],
        capture_output=True,
        check=True,
    )
    compressed = gzip.compress(result.stdout)

    s3 = boto3.client(
        "s3",
        endpoint_url=MINIO_ENDPOINT,
        aws_access_key_id=MINIO_ACCESS_KEY,
        aws_secret_access_key=MINIO_SECRET_KEY,
    )

    key = f"backups/{ts}.sql.gz"
    s3.put_object(Bucket=MINIO_BUCKET, Key=key, Body=compressed)
    print(f"Backup {ts}.sql.gz uploaded ({len(compressed) / 1024:.1f} KB)")


if __name__ == "__main__":
    backup()
