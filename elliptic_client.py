"""
Elliptic API client with enhanced error handling and retry logic.
"""
import json
import base64
import hmac
import hashlib
import time
import requests
import logging
from typing import Dict, Optional, Tuple
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import csv
import os

import config

logger = logging.getLogger(__name__)

class EllipticAPIError(Exception):
    """Custom exception for Elliptic API errors."""
    pass

class EllipticClient:
    def __init__(self):
        self.api_key = config.ELLIPTIC_API_KEY
        self.api_secret = config.ELLIPTIC_API_SECRET
        self.base_url = config.ELLIPTIC_URL
        self.session = self._create_session()
        self.category_mapping = self._load_category_mapping()
    
    def _create_session(self) -> requests.Session:
        """Create a requests session with retry logic."""
        session = requests.Session()
        
        retry_strategy = Retry(
            total=config.MAX_RETRIES,
            backoff_factor=config.RETRY_DELAY,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["POST", "GET"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        
        return session
    
    def _load_category_mapping(self) -> Dict[str, str]:
        """Load category mapping from CSV file."""
        category_mapping = {}
        csv_file_path = os.path.join(os.path.dirname(__file__), "Category_ID.csv")
        
        try:
            with open(csv_file_path, mode="r", encoding="utf-8") as file:
                reader = csv.reader(file)
                next(reader)  # Skip header
                for row in reader:
                    if len(row) >= 2:
                        category_id, category_name = row[:2]
                        category_mapping[category_id.strip()] = category_name.strip()
            logger.info(f"Loaded {len(category_mapping)} categories from CSV")
        except Exception as e:
            logger.error(f"Error loading category mapping: {e}")
        
        return category_mapping
    
    def _get_signature(self, secret: str, time_of_request: str, 
                       http_method: str, http_path: str, payload: str) -> str:
        """Generate HMAC-SHA256 signature for Elliptic API."""
        hmac_obj = hmac.new(base64.b64decode(secret), digestmod=hashlib.sha256)
        request_text = time_of_request + http_method + http_path.lower() + payload
        hmac_obj.update(request_text.encode('UTF-8'))
        return base64.b64encode(hmac_obj.digest()).decode('utf-8')
    
    def analyze_wallet(self, wallet_address: str) -> Tuple[bool, Optional[Dict], Optional[str]]:
        """
        Analyze a wallet address using Elliptic API.
        Returns: (success, response_data, error_message)
        """
        try:
            timestamp = str(int(time.time() * 1000))
            method = "POST"
            path = "/v2/wallet/synchronous"
            
            payload = json.dumps({
                "subject": {
                    "hash": wallet_address,
                    "type": "address",
                    "asset": "holistic",
                    "blockchain": "holistic"
                },
                "type": "wallet_exposure"
            }, separators=(',', ':'))
            
            signature = self._get_signature(self.api_secret, timestamp, method, path, payload)
            
            headers = {
                "x-access-key": self.api_key,
                "x-access-sign": signature,
                "x-access-timestamp": timestamp,
                "Content-Type": "application/json"
            }
            
            response = self.session.post(
                self.base_url,
                headers=headers,
                data=payload,
                timeout=config.REQUEST_TIMEOUT
            )
            
            # Check for HTTP errors
            if response.status_code == 401:
                error_msg = "API authentication failed. Please check your credentials."
                logger.error(error_msg)
                return False, None, error_msg
            
            if response.status_code == 429:
                error_msg = "API rate limit exceeded. Please try again later."
                logger.warning(error_msg)
                return False, None, error_msg
            
            if response.status_code >= 500:
                error_msg = f"Elliptic API server error (HTTP {response.status_code})"
                logger.error(error_msg)
                return False, None, error_msg
            
            response.raise_for_status()
            
            result = response.json()
            
            # Validate response structure
            if not isinstance(result, dict):
                error_msg = "Invalid API response format"
                logger.error(error_msg)
                return False, None, error_msg
            
            logger.info(f"Successfully analyzed wallet: {wallet_address[:10]}...")
            return True, result, None
            
        except requests.exceptions.Timeout:
            error_msg = "API request timed out. Please try again."
            logger.error(error_msg)
            return False, None, error_msg
        
        except requests.exceptions.ConnectionError:
            error_msg = "Failed to connect to Elliptic API. Please check your internet connection."
            logger.error(error_msg)
            return False, None, error_msg
        
        except requests.exceptions.RequestException as e:
            error_msg = f"API request failed: {str(e)}"
            logger.error(error_msg)
            return False, None, error_msg
        
        except json.JSONDecodeError:
            error_msg = "Failed to parse API response"
            logger.error(error_msg)
            return False, None, error_msg
        
        except Exception as e:
            error_msg = f"Unexpected error during wallet analysis: {str(e)}"
            logger.error(error_msg)
            return False, None, error_msg
    
    def apply_compliance_rules(self, response_data: Dict) -> Tuple[str, Dict]:
        """
        Apply compliance rules to determine wallet approval/rejection.
        Returns: (decision, details)
        """
        risk_score = response_data.get("risk_score", None)
        source_exposures = response_data.get("evaluation_detail", {}).get("source", [])
        destination_exposures = response_data.get("evaluation_detail", {}).get("destination", [])
        
        triggered_rules = {"Source": [], "Destination": []}
        rejection_reason = None
        
        # Check if risk score exists
        if risk_score is None:
            return "Approved", {"reason": "No risk score found", "triggered_rules": triggered_rules}
        
        # Rule 1: High risk score
        if risk_score >= config.RISK_SCORE_THRESHOLD:
            rejection_reason = f"High Risk Score ({risk_score})"
            return f"Rejected - {rejection_reason}", {
                "reason": rejection_reason,
                "risk_score": risk_score,
                "triggered_rules": triggered_rules
            }
        
        # Get high-risk category IDs
        high_risk_category_ids = {
            cat_id for cat_id, cat_name in self.category_mapping.items()
            if cat_name in config.HIGH_RISK_CATEGORIES
        }
        
        # Rule 2-4: Check exposures
        for exposure_list, risk_type in [(source_exposures, "Source"), (destination_exposures, "Destination")]:
            for exposure in exposure_list:
                for matched_element in exposure.get("matched_elements", []):
                    category_id = matched_element.get("category_id", "Unknown")
                    category = self.category_mapping.get(category_id, "Unknown")
                    
                    for contribution in matched_element.get("contributions", []):
                        min_hops = contribution.get("min_number_of_hops", 999)
                        indirect_percentage = contribution.get("indirect_percentage", 0)
                        
                        # Log triggered rule
                        triggered_rules[risk_type].append({
                            "category": category,
                            "hops": min_hops,
                            "contribution": round(indirect_percentage, 2)
                        })
                        
                        # Rule 2: High-risk category within hop limit
                        if category_id in high_risk_category_ids and min_hops <= config.MAX_HOP_DISTANCE:
                            rejection_reason = f"{category} detected within {min_hops} hops"
                            return f"Rejected - {rejection_reason}", {
                                "reason": rejection_reason,
                                "risk_score": risk_score,
                                "category": category,
                                "hops": min_hops,
                                "triggered_rules": triggered_rules
                            }
                        
                        # Rule 3: High-risk country
                        country_codes = contribution.get("risk_triggers", {}).get("country", [])
                        if isinstance(country_codes, list):
                            for country_code in country_codes:
                                if country_code in config.HIGH_RISK_COUNTRIES and min_hops <= config.MAX_HOP_DISTANCE:
                                    rejection_reason = f"High-risk country {country_code} detected within {min_hops} hops"
                                    return f"Rejected - {rejection_reason}", {
                                        "reason": rejection_reason,
                                        "risk_score": risk_score,
                                        "country": country_code,
                                        "hops": min_hops,
                                        "triggered_rules": triggered_rules
                                    }
                        
                        # Rule 4: Gambling special case
                        if category == "Gambling":
                            if min_hops <= config.GAMBLING_HOP_LIMIT:
                                rejection_reason = f"Gambling found at {min_hops} hops"
                                return f"Rejected - {rejection_reason}", {
                                    "reason": rejection_reason,
                                    "risk_score": risk_score,
                                    "category": category,
                                    "hops": min_hops,
                                    "triggered_rules": triggered_rules
                                }
                            elif min_hops == 3 and indirect_percentage > config.GAMBLING_CONTRIBUTION_THRESHOLD:
                                rejection_reason = f"Gambling at 3 hops with {indirect_percentage:.2f}% contribution"
                                return f"Rejected - {rejection_reason}", {
                                    "reason": rejection_reason,
                                    "risk_score": risk_score,
                                    "category": category,
                                    "hops": min_hops,
                                    "contribution": indirect_percentage,
                                    "triggered_rules": triggered_rules
                                }
        
        # All rules passed
        return "Approved", {
            "reason": "All compliance checks passed",
            "risk_score": risk_score,
            "triggered_rules": triggered_rules
        }
