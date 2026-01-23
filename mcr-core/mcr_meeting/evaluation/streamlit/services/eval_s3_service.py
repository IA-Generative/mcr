from io import BytesIO
from typing import List, Optional

import pandas as pd
from loguru import logger

from mcr_meeting.app.configs.base import S3Settings
from mcr_meeting.app.utils.s3_client import s3_external_client

s3_settings = S3Settings()


class EvalS3Service:
    def list_evaluation_results(
        self,
        bucket: str = s3_settings.S3_BUCKET,
        prefix: str = s3_settings.S3_EVALUATION_FOLDER,
    ) -> List[str]:
        """List all CSV files in the evaluation folder."""
        try:
            paginator = s3_external_client.get_paginator("list_objects_v2")
            page_iterator = paginator.paginate(Bucket=bucket, Prefix=f"{prefix}/")

            files = []
            for page in page_iterator:
                if "Contents" in page:
                    for obj in page["Contents"]:
                        if obj["Key"].endswith(".csv"):
                            files.append(obj["Key"])

            # Sort by last modified (newest first)
            files.sort(reverse=True)
            return files
        except Exception as e:
            logger.error(f"Error listing evaluation results from S3: {e}")
            return []

    def download_csv_as_df(
        self, object_key: str, bucket: str = s3_settings.S3_BUCKET
    ) -> Optional[pd.DataFrame]:
        """Download a CSV file from S3 and return it as a pandas DataFrame."""
        try:
            response = s3_external_client.get_object(Bucket=bucket, Key=object_key)
            csv_content = response["Body"].read()
            df = pd.read_csv(BytesIO(csv_content))
            return df
        except Exception as e:
            logger.error(f"Error downloading {object_key} from S3: {e}")
            return None
