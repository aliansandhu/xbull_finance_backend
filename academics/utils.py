import os
import datetime

from botocore.signers import CloudFrontSigner
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding
from django.conf import settings
from django.http import HttpResponse, FileResponse
from django.shortcuts import get_object_or_404
from storages.backends.s3boto3 import S3Boto3Storage


def rsa_signer(message):
    with open('s3_cloudist_priavte.pem', 'rb') as key_file:
    # with open('/home/ubuntu/xbull_finance_backend/s3_cloudist_priavte.pem', 'rb') as key_file:
        private_key = serialization.load_pem_private_key(
            key_file.read(),
            password=None,
            backend=default_backend()
        )
    return private_key.sign(message, padding.PKCS1v15(), hashes.SHA1())


def video_upload_path(instance, filename):
    """Define upload path to save videos inside MEDIA_ROOT/videos/"""
    return os.path.join("videos", filename)


def stream_video(request, video_id):
    from .models import VideoLecture
    """Serve video files with HTTP Range support for fast seeking."""
    video = get_object_or_404(VideoLecture, id=video_id)
    file_path = os.path.join(settings.MEDIA_ROOT, str(video.video_file))

    if not os.path.exists(file_path):
        return HttpResponse("Video not found", status=404)

    response = FileResponse(open(file_path, "rb"), content_type="video/mp4")
    response["Accept-Ranges"] = "bytes"
    return response


class CustomS3Storage(S3Boto3Storage):
    def url(self, name):
        # Get the CloudFront URL instead of the S3 URL
        key_id = settings.PUBLIC_KEY_ID
        url = f"{settings.AWS_S3_CUSTOM_DOMAIN}/{name}"

        expire_date = datetime.datetime(2029, 1, 1)
        cloudfront_signer = CloudFrontSigner(key_id, rsa_signer)

        # Create a signed url that will be valid until the specific expiry date
        # provided using a canned policy.
        signed_url = cloudfront_signer.generate_presigned_url(url, date_less_than=expire_date)

        return signed_url