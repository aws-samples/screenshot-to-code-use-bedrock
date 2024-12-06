import copy
import boto3
import json
import asyncio
import base64
from enum import Enum
from typing import Any, Awaitable, Callable, List, cast
from anthropic import AsyncAnthropic
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam, ChatCompletionChunk
from config import IS_DEBUG_ENABLED
from debug.DebugFileWriter import DebugFileWriter
from image_processing.utils import process_image

from utils import pprint_prompt


# Actual model versions that are passed to the LLMs and stored in our logs
class Llm(Enum):
    CLAUDE_3_SONNET = "anthropic.claude-3-sonnet-20240229-v1:0"
    CLAUDE_3_OPUS = "anthropic.claude-3-opus-20240229-v1:0"
    CLAUDE_3_HAIKU = "anthropic.claude-3-haiku-20240307-v1:0"
    CLAUDE_3_5_SONNET_2024_06_20 = "anthropic.claude-3-5-sonnet-20240620-v1:0"
    CLAUDE_3_5_SONNET_2024_10_22 = "anthropic.claude-3-5-sonnet-20241022-v2:0"
    NOVA_LITE = "amazon.nova-lite-v1:0"
    NOVA_PRO = "amazon.nova-pro-v1:0"
    
# Will throw errors if you send a garbage string
def convert_frontend_str_to_llm(frontend_str: str) -> Llm:
        return Llm(frontend_str)


async def stream_openai_response(
    messages: List[ChatCompletionMessageParam],
    api_key: str,
    base_url: str | None,
    callback: Callable[[str], Awaitable[None]],
    model: Llm,
) -> str:
    client = AsyncOpenAI(api_key=api_key, base_url=base_url)

    # Base parameters
    params = {
        "model": model.value,
        "messages": messages,
        "stream": True,
        "timeout": 600,
        "temperature": 0.0,
    }
    params["max_tokens"] = 4096

    stream = await client.chat.completions.create(**params)  # type: ignore
    full_response = ""
    async for chunk in stream:  # type: ignore
        assert isinstance(chunk, ChatCompletionChunk)
        if (
            chunk.choices
            and len(chunk.choices) > 0
            and chunk.choices[0].delta
            and chunk.choices[0].delta.content
        ):
            content = chunk.choices[0].delta.content or ""
            full_response += content
            await callback(content)

    await client.close()

    return full_response


# TODO: Have a seperate function that translates OpenAI messages to Claude messages
async def stream_claude_response(
    messages: List[ChatCompletionMessageParam],
    api_key: str,
    callback: Callable[[str], Awaitable[None]],
    model: Llm,
) -> str:

    client = AsyncAnthropic(api_key=api_key)

    # Base parameters
    max_tokens = 8192
    temperature = 0.0

    # Translate OpenAI messages to Claude messages

    # Deep copy messages to avoid modifying the original list
    cloned_messages = copy.deepcopy(messages)

    system_prompt = cast(str, cloned_messages[0].get("content"))
    claude_messages = [dict(message) for message in cloned_messages[1:]]
    for message in claude_messages:
        if not isinstance(message["content"], list):
            continue

        for content in message["content"]:  # type: ignore
            if content["type"] == "image_url":
                content["type"] = "image"

                # Extract base64 data and media type from data URL
                # Example base64 data URL: data:image/png;base64,iVBOR...
                image_data_url = cast(str, content["image_url"]["url"])

                # Process image and split media type and data
                # so it works with Claude (under 5mb in base64 encoding)
                (media_type, base64_data) = process_image(image_data_url)

                # Remove OpenAI parameter
                del content["image_url"]

                content["source"] = {
                    "type": "base64",
                    "media_type": media_type,
                    "data": base64_data,
                }

    # Stream Claude response
    async with client.messages.stream(
        model=model.value,
        max_tokens=max_tokens,
        temperature=temperature,
        system=system_prompt,
        messages=claude_messages,  # type: ignore
        extra_headers={"anthropic-beta": "max-tokens-3-5-sonnet-2024-07-15"},
    ) as stream:
        async for text in stream.text_stream:
            await callback(text)

    # Return final message
    response = await stream.get_final_message()

    # Close the Anthropic client
    await client.close()

    return response.content[0].text

async def stream_claude_bedrock_response(
    messages: List[ChatCompletionMessageParam],
    access_key: str,
    secret_key: str,
    region: str,
    callback: Callable[[str], Awaitable[None]],
    model: Llm,
) -> str:
    
    bedrock_runtime = boto3.client(service_name="bedrock-runtime", region_name=region, aws_access_key_id=access_key, aws_secret_access_key=secret_key)

    # Base parameters
    max_tokens = 4096
    temperature = 0.0

    # Deep copy messages to avoid modifying the original list
    cloned_messages = copy.deepcopy(messages)

    system_prompt = cast(str, cloned_messages[0].get("content"))
    claude_messages = [dict(message) for message in cloned_messages[1:]]

    async def make_bedrock_call(messages_to_send):
        # Convert messages to the format expected by converse_stream
        formatted_messages = []
        for msg in messages_to_send:
            if isinstance(msg["content"], str):
                formatted_message = {
                    "role": msg["role"],
                    "content": [{"text": msg["content"]}]
                }
            else:
                # Handle image content
                formatted_content = []
                for content_item in msg["content"]:
                    if content_item.get("type") == "image_url":
                        # Process image data
                        image_data_url = cast(str, content_item["image_url"]["url"])
                        media_type, base64_data = process_image(image_data_url)
                        media_type = media_type.split("/")[1]
                        formatted_content.append({
                            "image": {
                                "format": media_type,
                                "source": {
                                    "bytes": base64_data
                                }
                            }
                        })
                    else:
                        # Handle text content
                        formatted_content.append({"text": content_item.get("text", "")})
                
                formatted_message = {
                    "role": msg["role"],
                    "content": formatted_content
                }
            formatted_messages.append(formatted_message)

        response = await asyncio.to_thread(
            bedrock_runtime.converse_stream,
            modelId=model.value,
            messages=formatted_messages,
            inferenceConfig={
                "maxTokens": max_tokens,
                "temperature": temperature
            },
            system=[{"text": system_prompt}]
        )

        content = ""
        stop_reason = None
        for event in response.get('stream'):
            if "contentBlockDelta" in event:
                text = event["contentBlockDelta"]["delta"]["text"]
                content += text
                await callback(text)
            elif "messageStop" in event:
                stop_reason = event["messageStop"]["stopReason"]

            await asyncio.sleep(0)

        return content.strip(), stop_reason

    # Initial call
    content, stop_reason = await make_bedrock_call(claude_messages)
    
    # Handle max_tokens case by adding a user message requesting continuation
    while stop_reason == "max_tokens":
        claude_messages_tmp = copy.deepcopy(claude_messages)
        # Add the previous response as an assistant message
        claude_messages_tmp.append({"role": "assistant", "content": content.strip()})
        
        # Make another call
        additional_content, stop_reason = await make_bedrock_call(claude_messages_tmp)
        
        # Update content
        content += additional_content

    return content

async def stream_claude_response_native(
    system_prompt: str,
    messages: list[Any],
    api_key: str,
    callback: Callable[[str], Awaitable[None]],
    include_thinking: bool = False,
    model: Llm = Llm.CLAUDE_3_OPUS,
) -> str:

    client = AsyncAnthropic(api_key=api_key)

    # Base model parameters
    max_tokens = 4096
    temperature = 0.0

    # Multi-pass flow
    current_pass_num = 1
    max_passes = 2

    prefix = "<thinking>"
    response = None

    # For debugging
    full_stream = ""
    debug_file_writer = DebugFileWriter()

    while current_pass_num <= max_passes:
        current_pass_num += 1

        # Set up message depending on whether we have a <thinking> prefix
        messages_to_send = (
            messages + [{"role": "assistant", "content": prefix}]
            if include_thinking
            else messages
        )

        pprint_prompt(messages_to_send)

        async with client.messages.stream(
            model=model.value,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt,
            messages=messages_to_send,  # type: ignore
        ) as stream:
            async for text in stream.text_stream:
                print(text, end="", flush=True)
                full_stream += text
                await callback(text)

        response = await stream.get_final_message()
        response_text = response.content[0].text

        # Write each pass's code to .html file and thinking to .txt file
        if IS_DEBUG_ENABLED:
            debug_file_writer.write_to_file(
                f"pass_{current_pass_num - 1}.html",
                debug_file_writer.extract_html_content(response_text),
            )
            debug_file_writer.write_to_file(
                f"thinking_pass_{current_pass_num - 1}.txt",
                response_text.split("</thinking>")[0],
            )

        # Set up messages array for next pass
        messages += [
            {"role": "assistant", "content": str(prefix) + response.content[0].text},
            {
                "role": "user",
                "content": "You've done a good job with a first draft. Improve this further based on the original instructions so that the app is fully functional and looks like the original video of the app we're trying to replicate.",
            },
        ]

        print(
            f"Token usage: Input Tokens: {response.usage.input_tokens}, Output Tokens: {response.usage.output_tokens}"
        )

    # Close the Anthropic client
    await client.close()

    if IS_DEBUG_ENABLED:
        debug_file_writer.write_to_file("full_stream.txt", full_stream)

    if not response:
        raise Exception("No HTML response found in AI response")
    else:
        return response.content[0].text
