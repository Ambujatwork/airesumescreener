from typing import Dict, Optional, List, Any
import json
import logging
import os
from openai import AzureOpenAI
from concurrent.futures import ThreadPoolExecutor
import requests
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

class TextParser:
    """Text parser using Azure OpenAI for extracting structured information from resumes and job descriptions."""

    _instance = None  # Correct placement of the class attribute

    # Singleton pattern to avoid creating multiple instances
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
            # Configuration for Azure OpenAI
            self.config = {
                "api_version": os.getenv("AZURE_OPENAI_API_VERSION", "2023-05-15"),
                "azure_endpoint": os.getenv("AZURE_OPENAI_ENDPOINT"),
                "api_key": os.getenv("AZURE_OPENAI_API_KEY"),
                "model": os.getenv("AZURE_OPENAI_MODEL", "gpt-4"),
                "max_workers": int(os.getenv("MAX_WORKERS", "5"))
            }

            logger.info("Initializing TextParser with configuration")

            # Initialize the Azure OpenAI client
            self.client = AzureOpenAI(
                api_version=self.config["api_version"],
                azure_endpoint=self.config["azure_endpoint"],
                api_key=self.config["api_key"]
            )

            self.model = self.config["model"]
            self.executor = ThreadPoolExecutor(max_workers=self.config["max_workers"])
            self._initialized = True

            # Define parsing templates
            self.templates = {
                "resume": {
                    "system_role": "You are a professional resume parser. Extract structured information from resumes accurately.",
                    "format": {
                        "personal_info": {"name": "", "email": "", "phone": "", "location": ""},
                        "experience": [{"title": "", "company": "", "period": "", "responsibilities": []}],
                        "education": [{"degree": "", "institution": "", "period": ""}],
                        "skills": {"technical": [], "soft": []},
                        "certifications": [],
                        "languages": []
                    }
                },
                "job": {
                    "system_role": "You are a professional job parser. Extract ALL technical skills mentioned in the job description, even if implied.",
                    "format": {
                        "skills": {
                            "required": [
                                "List ALL programming languages, tools, databases, and methodologies explicitly or implicitly mentioned (e.g., Java, Python, NoSQL)."
                            ],
                            "preferred": []
                        }
                    }
                }
            }

            logger.info("TextParser initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize TextParser: {str(e)}")
            raise

    def _call_openai_api(self, text: str, parse_type: str = "resume") -> Optional[str]:
        """Make a call to Azure OpenAI API with error handling."""
        if parse_type not in self.templates:
            logger.error(f"Invalid parse type: {parse_type}")
            return None

        try:
            template = self.templates[parse_type]

            messages = [
                {
                    "role": "system",
                    "content": f"{template['system_role']} Extract information in the specified JSON format."
                },
                {
                    "role": "user",
                    "content": f"""Extract {parse_type} information as JSON using this exact format:
                    {json.dumps(template['format'], indent=2)}

                    Text to parse: {text}

                    Return ONLY valid JSON without any markdown formatting or extra text."""
                }
            ]

            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.3,
                max_tokens=1500
            )

            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"Error calling Azure OpenAI API: {str(e)}")
            return None

    def _extract_json_from_response(self, response: str) -> Optional[Dict[str, Any]]:
        """Extract and parse JSON from API response with robust error handling."""
        if not response:
            return None

        try:
            # Clean up response to ensure valid JSON
            json_str = response.strip()

            # Remove code blocks if present
            if json_str.startswith("```json"):
                json_str = json_str[7:]
                if json_str.endswith("```"):
                    json_str = json_str[:-3]
            elif json_str.startswith("```"):
                json_str = json_str[3:]
                if json_str.endswith("```"):
                    json_str = json_str[:-3]

            json_str = json_str.strip()
            parsed_data = json.loads(json_str)
            return parsed_data

        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {str(e)}")
            logger.debug(f"Problematic JSON string: {response}")
            return None

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def parse_text(self, text: str, parse_type: str):
        """Parse text using Azure OpenAI."""
        try:
            response = self._call_openai_api(text, parse_type)
            if not response:
                logger.warning(f"Failed to parse {parse_type}")
                return None

            parsed_data = self._extract_json_from_response(response)
            return parsed_data

        except requests.exceptions.Timeout:
            self.logger.error("Azure OpenAI API request timed out")
            return None
        except Exception as e:
            self.logger.error(f"API error: {str(e)}")
            return None

    def parse_batch(self, texts: List[str], parse_type: str = "resume") -> List[Optional[Dict[str, Any]]]:
        """Batch process multiple texts concurrently."""
        self.logger.debug(f"Initialized: {hasattr(self, 'logger')}")  # Should be True
        self.logger.debug(f"API client exists: {hasattr(self, 'client')}")        
        if not texts:
            return []

        logger.info(f"Starting batch parsing for {len(texts)} texts")
        return list(self.executor.map(lambda x: self.parse_text(x, parse_type), texts))