import boto3
import gzip
import json
from datetime import datetime
from typing import Dict, Any
from backend.config import settings
import logging

logger = logging.getLogger(__name__)

class BackupService:
    def __init__(self):
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.S3_REGION
        )
        self.backup_bucket = f"{settings.S3_BUCKET_NAME}-backups"
    
    async def backup_payroll_data(self, payroll_run_id: int, data: Dict[str, Any]):
        """Backup payroll data to S3"""
        try:
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            backup_key = f"payroll_backups/{payroll_run_id}/backup_{timestamp}.json.gz"
            
            # Compress data
            json_data = json.dumps(data, default=str)
            compressed_data = gzip.compress(json_data.encode('utf-8'))
            
            # Upload to S3
            self.s3_client.put_object(
                Bucket=self.backup_bucket,
                Key=backup_key,
                Body=compressed_data,
                ContentType='application/gzip',
                Metadata={
                    'payroll_run_id': str(payroll_run_id),
                    'backup_timestamp': timestamp
                }
            )
            
            logger.info(f"Payroll data backed up to {backup_key}")
            return backup_key
            
        except Exception as e:
            logger.error(f"Failed to backup payroll data: {e}")
            raise
    
    async def restore_payroll_data(self, backup_key: str) -> Dict[str, Any]:
        """Restore payroll data from S3"""
        try:
            response = self.s3_client.get_object(
                Bucket=self.backup_bucket,
                Key=backup_key
            )
            
            # Decompress data
            compressed_data = response['Body'].read()
            json_data = gzip.decompress(compressed_data).decode('utf-8')
            data = json.loads(json_data)
            
            logger.info(f"Payroll data restored from {backup_key}")
            return data
            
        except Exception as e:
            logger.error(f"Failed to restore payroll data: {e}")
            raise
