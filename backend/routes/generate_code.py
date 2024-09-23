import asyncio
from dataclasses import dataclass
from fastapi import APIRouter, WebSocket
from fastapi.websockets import WebSocketState
import openai
from codegen.utils import extract_html_content
from config import (
    BEDROCK_ACCESS_KEY,
    BEDROCK_SECRET_KEY,
    BEDROCK_REGION,
    DEPLOY_ON_AWS,
    NUM_VARIANTS,
    SHOULD_MOCK_AI_RESPONSE,
)
from custom_types import InputMode
from llm import (
    Llm,
    convert_frontend_str_to_llm,
    stream_claude_bedrock_response,
)
from fs_logging.core import write_logs
from mock_llm import mock_completion
from typing import Any, Callable, Coroutine, Dict, List, Literal, cast, get_args
from image_generation.core import generate_images
from prompts import create_prompt
from prompts.types import Stack

# from utils import pprint_prompt
from ws.constants import APP_ERROR_WEB_SOCKET_CODE  # type: ignore


router = APIRouter()


# Auto-upgrade usage of older models
def auto_upgrade_model(code_generation_model: Llm) -> Llm:
    #if code_generation_model == Llm.CLAUDE_3_SONNET:
    #    print(
    #        f"Initial deprecated model: {code_generation_model}. Auto-updating code generation model to CLAUDE-3.5-SONNET-2024-06-20"
    #    )
    #    return Llm.CLAUDE_3_5_SONNET_2024_06_20
    return code_generation_model


# Generate images, if needed
async def perform_image_generation(
    completion: str,
    should_generate_images: bool,
    bedrock_access_key: str | None,
    bedrock_secret_key: str | None,
    bedrock_region: str | None,
    image_cache: dict[str, str],
):
    if not should_generate_images:
        return completion

    image_generation_model = "amazon.titan-image-generator-v2:0"

    return await generate_images(
        completion,
        bedrock_access_key,
        bedrock_secret_key,
        bedrock_region,
        image_cache=image_cache,
        model=image_generation_model,
    )


@dataclass
class ExtractedParams:
    stack: Stack
    input_mode: InputMode
    code_generation_model: Llm
    should_generate_images: bool
    bedrock_access_key: str | None
    bedrock_secret_key: str | None
    bedrock_region: str | None


async def extract_params(
    params: Dict[str, str], throw_error: Callable[[str], Coroutine[Any, Any, None]]
) -> ExtractedParams:
    # Read the code config settings (stack) from the request.
    generated_code_config = params.get("generatedCodeConfig", "")
    if generated_code_config not in get_args(Stack):
        await throw_error(f"Invalid generated code config: {generated_code_config}")
        raise ValueError(f"Invalid generated code config: {generated_code_config}")
    validated_stack = cast(Stack, generated_code_config)

    # Validate the input mode
    input_mode = params.get("inputMode")
    if input_mode not in get_args(InputMode):
        await throw_error(f"Invalid input mode: {input_mode}")
        raise ValueError(f"Invalid input mode: {input_mode}")
    validated_input_mode = cast(InputMode, input_mode)

    # Read the model from the request. Fall back to default if not provided.
    code_generation_model_str = params.get(
        "codeGenerationModel", Llm.CLAUDE_3_5_SONNET_2024_06_20.value
    )
    try:
        code_generation_model = convert_frontend_str_to_llm(code_generation_model_str)
    except ValueError:
        await throw_error(f"Invalid model: {code_generation_model_str}")
        raise ValueError(f"Invalid model: {code_generation_model_str}")

    bedrock_access_key = get_from_settings_dialog_or_env(
        params, "bedrockAccessKey", BEDROCK_ACCESS_KEY
    )

    bedrock_secret_key = get_from_settings_dialog_or_env(
        params, "bedrockSecretKey", BEDROCK_SECRET_KEY
    )

    bedrock_region = get_from_settings_dialog_or_env(
        params, "bedrockRegion", BEDROCK_REGION
    )

    # Get the image generation flag from the request. Fall back to True if not provided.
    should_generate_images = bool(params.get("isImageGenerationEnabled", True))

    return ExtractedParams(
        stack=validated_stack,
        input_mode=validated_input_mode,
        code_generation_model=code_generation_model,
        should_generate_images=should_generate_images,
        bedrock_access_key=bedrock_access_key,
        bedrock_secret_key=bedrock_secret_key,
        bedrock_region=bedrock_region,
    )


def get_from_settings_dialog_or_env(
    params: dict[str, str], key: str, env_var: str | None
) -> str | None:
    value = params.get(key)
    if value:
        print(f"Using {key} from client-side settings dialog")
        return value

    if env_var:
        print(f"Using {key} from environment variable")
        return env_var

    return None


@router.websocket("/generate-code")
async def stream_code(websocket: WebSocket):
    await websocket.accept()
    print("Incoming websocket connection...")

    ## Communication protocol setup
    async def throw_error(
        message: str,
    ):
        print(message)
        await websocket.send_json({"type": "error", "value": message})
        await websocket.close(APP_ERROR_WEB_SOCKET_CODE)

    async def send_message(
        type: Literal["chunk", "status", "setCode", "error", "ping"],
        value: str,
        variantIndex: int,
    ):
        # Print for debugging on the backend
        if type == "error":
            print(f"Error (variant {variantIndex}): {value}")
        elif type == "status":
            print(f"Status (variant {variantIndex}): {value}")

        await websocket.send_json(
            {"type": type, "value": value, "variantIndex": variantIndex}
        )

    ## Parameter extract and validation

    # TODO: Are the values always strings?
    params: dict[str, str] = await websocket.receive_json()
    print("Received params")

    extracted_params = await extract_params(params, throw_error)
    stack = extracted_params.stack
    input_mode = extracted_params.input_mode
    code_generation_model = extracted_params.code_generation_model
    bedrock_access_key = extracted_params.bedrock_access_key
    bedrock_secret_key = extracted_params.bedrock_secret_key
    bedrock_region = extracted_params.bedrock_region
    should_generate_images = extracted_params.should_generate_images

    # Auto-upgrade usage of older models
    # code_generation_model = auto_upgrade_model(code_generation_model)

    print(
        f"Generating {stack} code in {input_mode} mode using {code_generation_model}..."
    )

    for i in range(NUM_VARIANTS):
        await send_message("status", "Generating code...", i)

    ### Prompt creation

    # Image cache for updates so that we don't have to regenerate images
    image_cache: Dict[str, str] = {}

    try:
        prompt_messages, image_cache = await create_prompt(params, stack, input_mode)
    except:
        await throw_error(
            "Error assembling prompt."
        )
        raise

    # pprint_prompt(prompt_messages)  # type: ignore

    ### Code generation

    async def process_chunk(content: str, variantIndex: int):
        await send_message("chunk", content, variantIndex)
        
    completions = []
    if SHOULD_MOCK_AI_RESPONSE:
        completions = [await mock_completion(process_chunk, input_mode=input_mode)]
    else:
        try:
            if input_mode == "video":
                print("Video mode")
                #if not anthropic_api_key:
                #    await throw_error(
                #        "Video only works with Anthropic models. No Anthropic API key found. Please add the environment variable ANTHROPIC_API_KEY to backend/.env or in the settings #dialog"
                #    )
                #    raise Exception("No Anthropic key")
#
                #completions = [
                #    await stream_claude_response_native(
                #        system_prompt=VIDEO_PROMPT,
                #        messages=prompt_messages,  # type: ignore
                #        api_key=anthropic_api_key,
                #        callback=lambda x: process_chunk(x, 0),
                #        model=Llm.CLAUDE_3_OPUS,
                #        include_thinking=True,
                #    )
                #]
            else:

                # Depending on the presence and absence of various keys,
                # we decide which models to run
                variant_models = ["bedrock"]
                if bedrock_region == "" or bedrock_region is None:
                    bedrock_region = "us-west-2"
                if not DEPLOY_ON_AWS:
                    if bedrock_access_key == "" or bedrock_secret_key == "":
                        await throw_error(
                            "No Bedrock Access permissions. Please add the environment variable BEDROCK_ACCESS_KEY and BEDROCK_SECRET_KEY to backend/.env or in the settings dialog. If you add it to .env, make sure to restart the backend server."
                        )
                        raise Exception("No Bedrock Access permissions")

                tasks: List[Coroutine[Any, Any, str]] = []
                for index, model in enumerate(variant_models):
                    if model == "bedrock":
                        tasks.append(
                            stream_claude_bedrock_response(
                                prompt_messages,
                                access_key=bedrock_access_key,
                                secret_key=bedrock_secret_key,
                                region=bedrock_region,
                                callback=lambda x, i=index: process_chunk(x, i),
                                model=code_generation_model,
                            )
                        )

                completions = await asyncio.gather(*tasks)
                print("Models used for generation: ", variant_models)
                
        except Exception as e:
            print("[GENERATE_CODE] An error occurred", e)
            error_message = (
                "An error occurred. Please try again later. If the problem persists, please contact support."
            )
            return await throw_error(error_message)

    ## Post-processing

    # Strip the completion of everything except the HTML content
    completions = [extract_html_content(completion) for completion in completions]

    # Write the messages dict into a log so that we can debug later
    write_logs(prompt_messages, completions[0])

    # Keep the websocket alive
    async def keep_alive(websocket: WebSocket):
        while websocket.client_state == WebSocketState.CONNECTED:
            try:
                await send_message("ping", "ping", 0)
                await asyncio.sleep(5)  # ping every 5 second
            except Exception:
                break
    keep_alive_task = asyncio.create_task(keep_alive(websocket))

    try:
        image_generation_tasks = [
            perform_image_generation(
                completion,
                should_generate_images,
                bedrock_access_key,
                bedrock_secret_key,
                bedrock_region,
                image_cache,
            )
            for completion in completions
        ]

        # Wait for all image generation tasks to complete
        updated_completions = await asyncio.gather(*image_generation_tasks)

        for index, updated_html in enumerate(updated_completions):
            await send_message("setCode", updated_html, index)
            await send_message("status", "Code generation complete.", index)
    except Exception as e:
        await throw_error(f"An error occurred: {str(e)}")
    finally:
        keep_alive_task.cancel()
        try:
            await keep_alive_task
        except asyncio.CancelledError:
            pass
        
        await websocket.close()
