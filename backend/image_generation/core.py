import asyncio
import re
import boto3
import hashlib
import os
import json
import base64
from typing import Dict, List, Literal, Union
from bs4 import BeautifulSoup
from config import (
    IMAGE_OUPUT_S3_BUCKET,
    DEPLOY_ON_AWS,
    BACKEND_URL,
)

from image_generation.replicate import call_replicate


async def process_tasks(
    prompts: List[str],
    bedrock_access_key: str | None,
    bedrock_secret_key: str | None,
    bedrock_region: str | None,
    model: Literal["amazon.titan-image-generator-v1:0", "amazon.titan-image-generator-v2:0"],
):
    import time

    start_time = time.time()

    tasks = [generate_image(prompt, bedrock_access_key, bedrock_secret_key, bedrock_region) for prompt in prompts]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    end_time = time.time()
    generation_time = end_time - start_time
    print(f"Image generation time: {generation_time:.2f} seconds")

    processed_results: List[Union[str, None]] = []
    for result in results:
        if isinstance(result, BaseException):
            print(f"An exception occurred: {result}")
            processed_results.append(None)
        else:
            processed_results.append(result)
    return processed_results


async def generate_image(
    prompt: str, bedrock_access_key: str | None, bedrock_secret_key: str | None, bedrock_region: str | None, model: Literal["amazon.titan-image-generator-v1:0", "amazon.titan-image-generator-v2:0"] = "amazon.titan-image-generator-v2:0",
) -> Union[str, None]:
    client = boto3.client(service_name="bedrock-runtime", region_name=bedrock_region, aws_access_key_id=bedrock_access_key, aws_secret_access_key=bedrock_secret_key) # type: ignore
    
    native_request = {
        "taskType": "TEXT_IMAGE",
        "textToImageParams": {"text": prompt},
        "imageGenerationConfig": {
            "numberOfImages": 1,
            "quality": "standard",
            "cfgScale": 8.0,
            "height": 512,
            "width": 512,
            "seed": 512,
        },
    }
    request = json.dumps(native_request)

    # request content to md5 hash
    request_content = f'{model}{request}'
    request_hash = hashlib.md5(request_content.encode()).hexdigest()

    if IMAGE_OUPUT_S3_BUCKET != "" and s3_key_exists(IMAGE_OUPUT_S3_BUCKET, f'{request_hash}.png', bedrock_access_key, bedrock_secret_key):
        print(f'Image already exists in S3: {request_hash}.png')
        return s3_key_presigned_url(IMAGE_OUPUT_S3_BUCKET, f'{request_hash}.png')

    async def generate_image_replicate(model: str, request: str) -> str:
        print(f'generate image with promt: {prompt}')
        response = await asyncio.to_thread(client.invoke_model, modelId=model, body=request) # type: ignore
        return response # type: ignore
    
    output_dir = "static/images"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    image_path = os.path.join(output_dir, f"{request_hash}.png")
    if not os.path.exists(image_path):
        response = await generate_image_replicate(model, request)
        model_response = json.loads(response["body"].read()) # type: ignore
        base64_image_data = model_response["images"][0]
        image_data = base64.b64decode(base64_image_data)
        with open(image_path, "wb") as file:
            file.write(image_data)
        file.close()

    if IMAGE_OUPUT_S3_BUCKET == "":
        print(f"Image url create: {image_path}")
        return f"{BACKEND_URL}/{output_dir}/{request_hash}.png"
    
    s3_upload_file(image_path, IMAGE_OUPUT_S3_BUCKET, f'{request_hash}.png', bedrock_access_key, bedrock_secret_key)
    os.remove(image_path) # use s3 instead of local storage
    return s3_key_presigned_url(IMAGE_OUPUT_S3_BUCKET, f'{request_hash}.png', bedrock_access_key, bedrock_secret_key)

def s3_upload_file(file_path: str, bucket_name: str, object_name: str, access_key: str, secret_key: str) -> None:
    if not DEPLOY_ON_AWS:
        s3_client = boto3.client("s3", aws_access_key_id=access_key, aws_secret_access_key=secret_key)
    else:
        s3_client = boto3.client("s3") # type: ignore
    s3_client.upload_file(file_path, bucket_name, object_name) # type: ignore

def s3_key_presigned_url(mybucket: str, mykey: str, access_key: str, secret_key: str) -> str:
    if not DEPLOY_ON_AWS:
        s3_client = boto3.client("s3", aws_access_key_id=access_key, aws_secret_access_key=secret_key)
    else:
        s3_client = boto3.client("s3") # type: ignore
    url = s3_client.generate_presigned_url('get_object', Params={'Bucket': mybucket, 'Key': mykey}, ExpiresIn=3600) # type: ignore
    return url # type: ignore

def s3_key_exists(mybucket: str, mykey: str, access_key: str, secret_key: str) -> bool:
    if not DEPLOY_ON_AWS:
        s3_client = boto3.client("s3", aws_access_key_id=access_key, aws_secret_access_key=secret_key)
    else:
        s3_client = boto3.client("s3") # type: ignore
    try:
        response = s3_client.list_objects_v2(Bucket=mybucket, Prefix=mykey) # type: ignore
        for obj in response['Contents']: # type: ignore
            if mykey == obj['Key']:
                return True  # key exists
        return False  # no keys match
    except KeyError:
        return False  # no keys found

async def generate_image_replicate(prompt: str, api_key: str) -> str:

    # We use SDXL Lightning
    return await call_replicate(
        "5f24084160c9089501c1b3545d9be3c27883ae2239b6f412990e82d4a6210f8f",
        {
            "width": 1024,
            "height": 1024,
            "prompt": prompt,
            "scheduler": "K_EULER",
            "num_outputs": 1,
            "guidance_scale": 0,
            "negative_prompt": "worst quality, low quality",
            "num_inference_steps": 4,
        },
        api_key,
    )


def extract_dimensions(url: str):
    # Regular expression to match numbers in the format '300x200'
    matches = re.findall(r"(\d+)x(\d+)", url)

    if matches:
        width, height = matches[0]  # Extract the first match
        width = int(width)
        height = int(height)
        return (width, height)
    else:
        return (100, 100)


def create_alt_url_mapping(code: str) -> Dict[str, str]:
    soup = BeautifulSoup(code, "html.parser")
    images = soup.find_all("img")

    mapping: Dict[str, str] = {}

    for image in images:
        if not image["src"].startswith("https://placehold.co"):
            mapping[image["alt"]] = image["src"]

    return mapping


async def generate_images(
    code: str,
    bedrock_access_key: str | None,
    bedrock_secret_key: str | None,
    bedrock_region: str | None,
    image_cache: Dict[str, str],
    model: Literal["amazon.titan-image-generator-v1:0", "amazon.titan-image-generator-v2:0"] = "amazon.titan-image-generator-v2:0",
) -> str:
    # Find all images
    soup = BeautifulSoup(code, "html.parser")
    images = soup.find_all("img")

    # Extract alt texts as image prompts
    alts: List[str | None] = []
    for img in images:
        # Only include URL if the image starts with https://placehold.co
        # and it's not already in the image_cache
        if (
            img["src"].startswith("https://placehold.co")
            and image_cache.get(img.get("alt")) is None
        ):
            alts.append(img.get("alt", None))

    # Exclude images with no alt text
    filtered_alts: List[str] = [alt for alt in alts if alt is not None]

    # Remove duplicates
    prompts = list(set(filtered_alts))

    # Return early if there are no images to replace
    if len(prompts) == 0:
        print("No images to replace")
        return code

    # Generate images
    results = await process_tasks(prompts, bedrock_access_key, bedrock_secret_key, bedrock_region, model)

    # Create a dict mapping alt text to image URL
    mapped_image_urls = dict(zip(prompts, results))

    # Merge with image_cache
    mapped_image_urls = {**mapped_image_urls, **image_cache}

    # Replace old image URLs with the generated URLs
    for img in images:
        # Skip images that don't start with https://placehold.co (leave them alone)
        if not img["src"].startswith("https://placehold.co"):
            continue

        new_url = mapped_image_urls[img.get("alt")]

        if new_url:
            # Set width and height attributes
            width, height = extract_dimensions(img["src"])
            img["width"] = width
            img["height"] = height
            # Replace img['src'] with the mapped image URL
            img["src"] = new_url
        else:
            print("Image generation failed for alt text:" + img.get("alt"))

    # Return the modified HTML
    # (need to prettify it because BeautifulSoup messes up the formatting)
    return soup.prettify()
