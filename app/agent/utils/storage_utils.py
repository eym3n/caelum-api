from app.config import Config


def upload_image_to_gs(
    image_content,
    destination_path,
    is_gif=False,
    is_svg=False,
    cache_control="public, max-age=86400",
):
    try:
        bucket = Config.GCS_CLIENT.bucket(Config.GS_BUCKET_NAME)
        blob = bucket.blob(destination_path)
        # print(f"Uploading image to {destination_path}")
        blob.cache_control = cache_control
        if is_gif:
            blob.upload_from_string(image_content, content_type="image/gif")
        elif is_svg:
            blob.upload_from_string(image_content, content_type="image/svg+xml")
        else:
            blob.upload_from_string(image_content, content_type="image/webp")
        return (
            f"https://{Config.GS_BUCKET_NAME}.storage.googleapis.com/{destination_path}"
        )
    except Exception as e:
        print(f"Failed to upload image to Google Cloud Storage: {e}")
        return None
