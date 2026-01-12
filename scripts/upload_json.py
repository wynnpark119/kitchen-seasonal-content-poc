#!/usr/bin/env python3
"""
JSON 파일을 객체 스토리지(S3/R2/GCS) 또는 Railway Volume에 업로드하는 스크립트

사용법:
    # S3/R2 업로드
    python scripts/upload_json.py --input data/collection.json --provider s3 --bucket my-bucket --prefix imports/2024-01-15

    # GCS 업로드
    python scripts/upload_json.py --input data/collection.json --provider gcs --bucket my-bucket --prefix imports/2024-01-15

    # Railway Volume 복사 (로컬에서 서버로)
    python scripts/upload_json.py --input data/collection.json --provider volume --path /data/imports

환경 변수:
    STORAGE_PROVIDER: s3|r2|gcs|volume (기본값: s3)
    STORAGE_BUCKET: 버킷 이름
    STORAGE_PREFIX: 키 prefix (예: imports/2024-01-15)
    STORAGE_ACCESS_KEY: Access Key ID
    STORAGE_SECRET_KEY: Secret Access Key
    STORAGE_ENDPOINT_URL: R2용 endpoint URL (예: https://xxx.r2.cloudflarestorage.com)
    IMPORT_DIR: Railway Volume 경로 (예: /data/imports)
"""
import os
import sys
import json
import argparse
import time
from pathlib import Path
from datetime import datetime
from typing import List, Optional
import uuid

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# .env 파일 로드
try:
    from dotenv import load_dotenv
    env_path = project_root / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
    else:
        load_dotenv()
except ImportError:
    pass


def upload_to_s3(file_path: Path, bucket: str, key: str, 
                 access_key: str, secret_key: str, endpoint_url: Optional[str] = None) -> str:
    """S3 또는 R2에 파일 업로드"""
    try:
        import boto3
        from botocore.exceptions import ClientError
    except ImportError:
        print("❌ ERROR: boto3 not installed. Run: pip install boto3")
        sys.exit(1)
    
    print(f"📤 Uploading to S3/R2: s3://{bucket}/{key}")
    
    # S3 클라이언트 생성
    s3_config = {
        'aws_access_key_id': access_key,
        'aws_secret_access_key': secret_key,
    }
    
    if endpoint_url:
        # R2 또는 다른 S3-compatible 서비스
        s3_config['endpoint_url'] = endpoint_url
        s3_config['region_name'] = 'auto'  # R2는 auto
    
    s3_client = boto3.client('s3', **s3_config)
    
    try:
        start_time = time.time()
        s3_client.upload_file(str(file_path), bucket, key)
        elapsed = time.time() - start_time
        
        file_size = file_path.stat().st_size
        print(f"✅ Upload successful ({elapsed:.2f}s, {file_size / 1024 / 1024:.2f} MB)")
        
        # URI 반환
        if endpoint_url:
            # R2의 경우 public URL 또는 signed URL
            return f"s3://{bucket}/{key}"
        else:
            return f"s3://{bucket}/{key}"
            
    except ClientError as e:
        print(f"❌ Upload failed: {e}")
        sys.exit(1)


def upload_to_gcs(file_path: Path, bucket: str, blob_name: str,
                  credentials_path: Optional[str] = None) -> str:
    """GCS에 파일 업로드"""
    try:
        from google.cloud import storage
        from google.oauth2 import service_account
    except ImportError:
        print("❌ ERROR: google-cloud-storage not installed. Run: pip install google-cloud-storage")
        sys.exit(1)
    
    print(f"📤 Uploading to GCS: gs://{bucket}/{blob_name}")
    
    # GCS 클라이언트 생성
    if credentials_path:
        credentials = service_account.Credentials.from_service_account_file(credentials_path)
        storage_client = storage.Client(credentials=credentials)
    else:
        # 환경 변수 GOOGLE_APPLICATION_CREDENTIALS 또는 기본 인증 사용
        storage_client = storage.Client()
    
    try:
        bucket_obj = storage_client.bucket(bucket)
        blob = bucket_obj.blob(blob_name)
        
        start_time = time.time()
        blob.upload_from_filename(str(file_path))
        elapsed = time.time() - start_time
        
        file_size = file_path.stat().st_size
        print(f"✅ Upload successful ({elapsed:.2f}s, {file_size / 1024 / 1024:.2f} MB)")
        
        return f"gs://{bucket}/{blob_name}"
        
    except Exception as e:
        print(f"❌ Upload failed: {e}")
        sys.exit(1)


def copy_to_volume(file_path: Path, volume_path: str) -> str:
    """Railway Volume에 파일 복사 (로컬에서 서버로 복사하는 경우)"""
    print(f"⚠️  Railway Volume copy: {file_path} -> {volume_path}")
    print("   Note: This requires manual copy via Railway CLI or SSH")
    print(f"   Command: railway run cp {file_path} {volume_path}/")
    
    # 실제로는 Railway CLI를 통해 복사해야 함
    # 또는 서버에서 직접 실행하는 경우에만 사용 가능
    return f"file://{volume_path}/{file_path.name}"


def upload_directory(input_dir: Path, provider: str, **kwargs) -> List[str]:
    """디렉토리 내 모든 JSON 파일 업로드"""
    json_files = list(input_dir.glob("*.json"))
    if not json_files:
        print(f"❌ ERROR: No JSON files found in {input_dir}")
        sys.exit(1)
    
    print(f"📂 Found {len(json_files)} JSON files")
    
    uris = []
    for json_file in json_files:
        print(f"\n📄 Processing: {json_file.name}")
        
        if provider == "s3" or provider == "r2":
            uri = upload_to_s3(json_file, kwargs['bucket'], kwargs['key_prefix'] + json_file.name,
                             kwargs['access_key'], kwargs['secret_key'], kwargs.get('endpoint_url'))
        elif provider == "gcs":
            uri = upload_to_gcs(json_file, kwargs['bucket'], kwargs['key_prefix'] + json_file.name,
                              kwargs.get('credentials_path'))
        elif provider == "volume":
            uri = copy_to_volume(json_file, kwargs['volume_path'])
        else:
            print(f"❌ ERROR: Unknown provider: {provider}")
            sys.exit(1)
        
        uris.append(uri)
    
    return uris


def main():
    parser = argparse.ArgumentParser(description="Upload JSON files to object storage or Railway Volume")
    parser.add_argument("--input", type=str, required=True,
                       help="Input JSON file or directory")
    parser.add_argument("--provider", type=str,
                       choices=["s3", "r2", "gcs", "volume"],
                       default=os.getenv("STORAGE_PROVIDER", "s3"),
                       help="Storage provider (default: s3)")
    parser.add_argument("--bucket", type=str,
                       default=os.getenv("STORAGE_BUCKET"),
                       help="Bucket name (S3/R2/GCS)")
    parser.add_argument("--prefix", type=str,
                       default=os.getenv("STORAGE_PREFIX", ""),
                       help="Key prefix (e.g., imports/2024-01-15)")
    parser.add_argument("--access-key", type=str,
                       default=os.getenv("STORAGE_ACCESS_KEY"),
                       help="Access Key ID")
    parser.add_argument("--secret-key", type=str,
                       default=os.getenv("STORAGE_SECRET_KEY"),
                       help="Secret Access Key")
    parser.add_argument("--endpoint-url", type=str,
                       default=os.getenv("STORAGE_ENDPOINT_URL"),
                       help="Endpoint URL (for R2)")
    parser.add_argument("--gcs-credentials", type=str,
                       default=os.getenv("GOOGLE_APPLICATION_CREDENTIALS"),
                       help="GCS credentials JSON file path")
    parser.add_argument("--volume-path", type=str,
                       default=os.getenv("IMPORT_DIR", "/data/imports"),
                       help="Railway Volume path")
    parser.add_argument("--job-id", type=str,
                       default=None,
                       help="Job ID for tracking (default: auto-generated)")
    
    args = parser.parse_args()
    
    # Job ID 생성
    job_id = args.job_id or f"import-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:8]}"
    
    print("=" * 60)
    print("JSON Upload Script")
    print("=" * 60)
    print(f"Provider: {args.provider}")
    print(f"Job ID: {job_id}")
    
    # 입력 경로 확인
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"❌ ERROR: Input path not found: {input_path}")
        sys.exit(1)
    
    # Prefix에 날짜와 job_id 추가
    if args.prefix:
        prefix = f"{args.prefix.rstrip('/')}/{job_id}/"
    else:
        prefix = f"imports/{datetime.now().strftime('%Y-%m-%d')}/{job_id}/"
    
    uris = []
    
    if input_path.is_file():
        # 단일 파일 업로드
        print(f"\n📄 File: {input_path.name}")
        
        key_name = prefix + input_path.name
        
        if args.provider == "s3" or args.provider == "r2":
            if not args.bucket or not args.access_key or not args.secret_key:
                print("❌ ERROR: --bucket, --access-key, --secret-key required for S3/R2")
                sys.exit(1)
            uri = upload_to_s3(input_path, args.bucket, key_name,
                              args.access_key, args.secret_key, args.endpoint_url)
        elif args.provider == "gcs":
            if not args.bucket:
                print("❌ ERROR: --bucket required for GCS")
                sys.exit(1)
            uri = upload_to_gcs(input_path, args.bucket, key_name, args.gcs_credentials)
        elif args.provider == "volume":
            uri = copy_to_volume(input_path, args.volume_path)
        else:
            print(f"❌ ERROR: Unknown provider: {args.provider}")
            sys.exit(1)
        
        uris.append(uri)
        
    elif input_path.is_dir():
        # 디렉토리 업로드
        if args.provider == "s3" or args.provider == "r2":
            if not args.bucket or not args.access_key or not args.secret_key:
                print("❌ ERROR: --bucket, --access-key, --secret-key required for S3/R2")
                sys.exit(1)
            uris = upload_directory(input_path, args.provider,
                                   bucket=args.bucket,
                                   key_prefix=prefix,
                                   access_key=args.access_key,
                                   secret_key=args.secret_key,
                                   endpoint_url=args.endpoint_url)
        elif args.provider == "gcs":
            if not args.bucket:
                print("❌ ERROR: --bucket required for GCS")
                sys.exit(1)
            uris = upload_directory(input_path, args.provider,
                                   bucket=args.bucket,
                                   key_prefix=prefix,
                                   credentials_path=args.gcs_credentials)
        elif args.provider == "volume":
            uris = upload_directory(input_path, args.provider,
                                   volume_path=args.volume_path)
        else:
            print(f"❌ ERROR: Unknown provider: {args.provider}")
            sys.exit(1)
    else:
        print(f"❌ ERROR: Invalid input path: {input_path}")
        sys.exit(1)
    
    # 결과 출력
    print("\n" + "=" * 60)
    print("Upload Summary")
    print("=" * 60)
    print(f"Job ID: {job_id}")
    print(f"Files uploaded: {len(uris)}")
    print("\nURIs:")
    for uri in uris:
        print(f"  - {uri}")
    
    # URI 목록을 파일로 저장 (서버에서 import 시 사용)
    uri_list_file = project_root / f"uploaded_uris_{job_id}.txt"
    with open(uri_list_file, 'w') as f:
        for uri in uris:
            f.write(f"{uri}\n")
    
    print(f"\n✅ URI list saved to: {uri_list_file}")
    print("=" * 60)


if __name__ == "__main__":
    main()
