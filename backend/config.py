# Useful for debugging purposes when you don't want to waste GPT4-Vision credits
# Setting to True will stream a mock response instead of calling the OpenAI API
# TODO: Should only be set to true when value is 'True', not any abitrary truthy value
import os

NUM_VARIANTS = 1

# AWS-related
BEDROCK_ACCESS_KEY = os.environ.get("BEDROCK_ACCESS_KEY", "")
BEDROCK_SECRET_KEY = os.environ.get("BEDROCK_SECRET_KEY", "")
BEDROCK_REGION = os.environ.get("BEDROCK_REGION", "")
IMAGE_OUPUT_S3_BUCKET = os.environ.get("IMAGE_OUPUT_S3_BUCKET", "")
DEPLOY_ON_AWS = bool(os.environ.get("DEPLOY_ON_AWS", False))


# Backend-related, used for generating image URLs prefixed with this URL
BACKEND_URL = os.environ.get("BACKEND_URL", "http://127.0.0.1:7001")

# Debugging-related
SHOULD_MOCK_AI_RESPONSE = bool(os.environ.get("MOCK", False))
IS_DEBUG_ENABLED = bool(os.environ.get("IS_DEBUG_ENABLED", False))
DEBUG_DIR = os.environ.get("DEBUG_DIR", "")
