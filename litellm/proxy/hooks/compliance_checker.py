import sys
import traceback
import uuid
import yaml
from typing import Optional
import os
import requests
import json

from fastapi import HTTPException

import litellm
from litellm._logging import verbose_proxy_logger
from litellm.caching import DualCache
from litellm.integrations.custom_logger import CustomLogger
from litellm.proxy._types import UserAPIKeyAuth


class _PROXY_ComplianceChecker(
    CustomLogger
):  # https://docs.litellm.ai/docs/observability/custom_callback#callback-class
    # Class variables or attributes

    async def get_conformity_assessment(self, message):
        compliance_conform = True
        system_prompt = f"""
                        You are a strict compliace assistant that rejects any message that involves personal information of confidential information about the company medialine. When you find the user message should be rejected, answer exactly with the words: 'compliance violation'. If the user message is ok, always simply reply with: 'conform'."
                        """
        compliance_llm_url = os.getenv("COMPLIANCE_MODEL_URL")
        model=os.getenv("COMPLIANCE_MODEL")
        headers = {'Content-Type': 'application/json'}
        data = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt
                    },
                {
                    "role": "user",
                    "content": message
                }
                ],
            "stream": False,
            "max_tokens": 20
            }
        try:
            response = requests.post(compliance_llm_url, headers=headers, data=json.dumps(data), verify=False)
        except self.azure_http_error as e:
            verbose_proxy_logger.debug(
                "Error in request to compliance llm: %s", traceback.format_exc()
            )
            verbose_proxy_logger.debug(traceback.format_exc())
            raise
        eval_string = response.json()['choices'][0]['message']['content']
        if 'compliance violation' in eval_string or 'conform' not in eval_string:
            compliance_conform = False
        return compliance_conform
    async def async_pre_call_hook(
        self,
        user_api_key_dict: UserAPIKeyAuth,
        cache: DualCache,
        data: dict,
        call_type: str,  # "completion", "embeddings", "image_generation", "moderation"
    ):
        verbose_proxy_logger.debug("Inside Compliance Checker Pre-Call Hook")
        try:
            if call_type == "completion" and "messages" in data:
                if data['model']!= os.getenv("COMPLIANCE_MODEL"):
                    for m in data["messages"]:
                        if "content" in m and isinstance(m["content"], str):
                            compliance_conform = await self.get_conformity_assessment(message=m["content"])
                            if not compliance_conform:
                                data['messages'] = [
                                    {
                                        "role": "user",
                                        "content": " Simply tell me to use a compliance safe llm and do nothing else!"
                                        }
                                    ]
        except HTTPException as e:
            raise e
        except Exception as e:
            verbose_proxy_logger.error(
                f"litellm.proxy.hooks.compliance_checker.py::async_pre_call_hook(): Exception occured - {str(e)}"
                )
            verbose_proxy_logger.error(
                f"keys: {','.join(data.keys())}"
                )
            verbose_proxy_logger.error(
                f"{os.getenv('COMPLIANCE_MODEL')}, {data['model']}"
                )
            verbose_proxy_logger.debug(traceback.format_exc())
        return data
