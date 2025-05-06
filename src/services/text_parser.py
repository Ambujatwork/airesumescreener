from typing import Dict, Optional, List, Any, Union
import json
import re
import logging
import os
from openai import AzureOpenAI
from concurrent.futures import ThreadPoolExecutor
from fastapi import UploadFile
from src.services.text_extractor import TextExtractor

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

class TextParser:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TextParser, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        if self._initialized:
            return

        try:
            self.config = {
                "api_version": os.getenv("AZURE_OPENAI_API_VERSION", "2023-05-15"),
                "azure_endpoint": os.getenv("AZURE_OPENAI_ENDPOINT"),
                "api_key": os.getenv("AZURE_OPENAI_API_KEY"),
                "model": os.getenv("AZURE_OPENAI_MODEL", "gpt-4"),
                "max_workers": int(os.getenv("MAX_WORKERS", "5"))
            }

            self.client = AzureOpenAI(
                api_version=self.config["api_version"],
                azure_endpoint=self.config["azure_endpoint"],
                api_key=self.config["api_key"]
            )

            self.model = self.config["model"]
            self.executor = ThreadPoolExecutor(max_workers=self.config["max_workers"])
            self._initialized = True

            self.templates = {
                "resume": {
                    "system_role": "You are a professional resume parser. Extract detailed structured information even from noisy or poorly formatted resumes.",
                    "format": {
                        "personal_info": {"name": "", "email": "", "phone": "", "location": ""},
                        "experience": [{"title": "", "company": "", "period": ""}],
                        "education": [{"degree": "", "institution": "", "period": ""}],
                        "skills": []
                    }
                },
                "job": {
                    "system_role": "You are a professional job description parser. Extract all technical skills explicitly or implicitly mentioned.",
                    "format": {
                        "skills": {"required": [], "preferred": []},
                        "location": "",
                        "experience": {"min_years": 0}
                    }
                }
            }

        except Exception as e:
            logger.error(f"Failed to initialize TextParser: {str(e)}")
            raise

    def _fallback_parse(self, text: str) -> Dict[str, Any]:
        """Simple regex fallback if OpenAI fails."""
        name = "Unknown"
        email_match = re.search(r"[\w.-]+@[\w.-]+", text)
        phone_match = re.search(r"(\+?\d{1,3}[\s-]?)?(\(?\d{3}\)?[\s-]?)?\d{3}[\s-]?\d{4}", text)

        return {
            "personal_info": {
                "name": name,
                "email": email_match.group() if email_match else "",
                "phone": phone_match.group() if phone_match else "",
                "location": ""
            },
            "experience": [],
            "education": [],
            "skills": []
        }

    def _call_openai_api(self, text: str, parse_type: str = "resume") -> Optional[str]:
        if parse_type not in self.templates:
            logger.error(f"Invalid parse type: {parse_type}")
            return None

        template = self.templates[parse_type]

        messages = [
            {"role": "system", "content": f"{template['system_role']}"},
            {"role": "user", "content": f"""Extract {parse_type} information in pure JSON:
            {json.dumps(template['format'], indent=2)}

            Text: {text[:3500]}

            ONLY JSON as output."""}
        ]

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.2,
                max_tokens=1500
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Azure OpenAI error: {str(e)}")
            return None

    def _extract_json_from_response(self, response: str) -> Optional[Dict[str, Any]]:
        if not response:
            return None
        try:
            json_str = response.strip()
            if json_str.startswith("```json"):
                json_str = json_str[7:].rstrip("```").strip()
            return json.loads(json_str)
        except Exception as e:
            logger.error(f"JSON parse error: {str(e)}")
            return None

    def parse_text(self, text: str, parse_type: str = "resume") -> Optional[Dict[str, Any]]:
        try:
            response = self._call_openai_api(text, parse_type)
            if not response:
                return self._fallback_parse(text)

            parsed = self._extract_json_from_response(response)
            if not parsed:
                return self._fallback_parse(text)
            return parsed

        except Exception as e:
            logger.error(f"Parse error: {str(e)}")
            return self._fallback_parse(text)

    def parse_batch(self, texts: List[str], parse_type: str = "resume") -> List[Optional[Dict[str, Any]]]:
        if not texts:
            return []
        return list(self.executor.map(lambda x: self.parse_text(x, parse_type), texts))

    async def parse(self, file_or_text: Union[UploadFile, str], parse_type: str = "resume") -> dict:
        if isinstance(file_or_text, UploadFile):
            content = await TextExtractor.extract_text(file_or_text)
        else:
            content = file_or_text

        if not content.strip():
            return {}

        return self.parse_text(content, parse_type)