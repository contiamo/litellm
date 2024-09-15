import os
import traceback
from typing import Dict, Any

import requests
from fastapi import HTTPException

from litellm._logging import verbose_proxy_logger
from litellm.caching import DualCache
from litellm.integrations.custom_logger import CustomLogger
from litellm.proxy._types import UserAPIKeyAuth

class _PROXY_ComplianceChecker(CustomLogger):
    """
    A compliance checker that evaluates messages for conformity with company policies.
    """

    async def get_conformity_assessment(self, message: str) -> bool:
        """
        Assess the compliance of a given message using a specified LLM.

        Args:
            message (str): The message to be assessed.

        Returns:
            bool: True if the message conforms to compliance standards, False otherwise.

        Raises:
            HTTPException: If there's an error in the LLM request.
        """
        system_prompt = (
            "You are a strict compliance assistant that rejects any message that involves personal information "
            "or confidential information about the company medialine. When you find the user message should be rejected, "
            "answer exactly with the words: 'compliance violation'. If the user message is ok, always simply reply with: 'conform'."
        )

        compliance_llm_url = os.getenv("COMPLIANCE_MODEL_URL")
        model = os.getenv("COMPLIANCE_MODEL")
        
        headers = {'Content-Type': 'application/json'}
        data = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message}
            ],
            "stream": False,
            "max_tokens": 20
        }

        try:
            response = requests.post(compliance_llm_url, headers=headers, json=data, verify=False)
            response.raise_for_status()
        except requests.RequestException as e:
            verbose_proxy_logger.debug(f"Error in request to compliance LLM: {traceback.format_exc()}")
            raise HTTPException(status_code=500, detail="Error in compliance check") from e

        eval_string = response.json()['choices'][0]['message']['content'].lower()
        return 'conform' in eval_string and 'compliance violation' not in eval_string

    async def async_pre_call_hook(
        self,
        user_api_key_dict: UserAPIKeyAuth,
        cache: DualCache,
        data: Dict[str, Any],
        call_type: str,
    ) -> Dict[str, Any]:
        """
        Pre-call hook to check compliance of messages before processing.

        Args:
            user_api_key_dict (UserAPIKeyAuth): User API key information.
            cache (DualCache): Cache object.
            data (Dict[str, Any]): The data containing the messages to be checked.
            call_type (str): The type of call being made.

        Returns:
            Dict[str, Any]: The original data, potentially modified if compliance issues are found.

        Raises:
            HTTPException: If there's an error during the compliance check process.
        """
        verbose_proxy_logger.debug("Inside Compliance Checker Pre-Call Hook")
        
        try:
            if call_type == "completion" and "messages" in data:
                if data.get('model') != os.getenv("COMPLIANCE_MODEL"):
                    for m in data["messages"]:
                        if isinstance(m.get("content"), str):
                            if not await self.get_conformity_assessment(m["content"]):
                                data['messages'] = [{
                                    "role": "user",
                                    "content": "Simply return exactly the following: Please ensure you use a compliant language model in accordance with our company's regulations. Thank you for your cooperation."
                                }]
                                break
        except HTTPException:
            raise
        except Exception as e:
            verbose_proxy_logger.error(f"Error in compliance check: {str(e)}")
            verbose_proxy_logger.debug(traceback.format_exc())

        return data