"""Calls the Salesforce AI Model Gateway (AWS Bedrock-backed) to generate CI findings."""

import json
import requests
import streamlit as st

SYSTEM_PROMPT = """You are a professional customer insights analyst at Salesforce.
Your job is to analyze interview transcripts and produce structured, high-quality
customer insights findings in the exact JSON format specified.

You write in a professional, analytical tone — similar to a McKinsey-style research brief.
You identify patterns across multiple interviews, surface compelling direct quotes,
and organize findings around the research objectives provided.

CRITICAL: You must respond with ONLY valid JSON. No markdown, no explanation, no code fences."""

FINDINGS_SCHEMA = """
Return a JSON object with this exact structure:
{
  "title": "<Product/Topic>: Customer Insights",
  "subtitle": "<Product/Topic>: Customer Insights",
  "event": "<Event Name>  |  <Month Year>",
  "executive_summary": [
    "paragraph 1 — overall sentiment and key theme",
    "paragraph 2 — primary use cases and pain points that resonated",
    "paragraph 3 — what moved customers most and strategic implications"
  ],
  "methodology": {
    "description": "Brief description of how many interviews, when, where, and how conducted.",
    "participants": [
      {"name": "Name or role if anonymous", "role": "Title, Company/Industry"},
      ...
    ]
  },
  "key_findings": [
    {
      "title": "Key Finding N: <Short Descriptive Title>",
      "body": "2-3 sentence paragraph establishing the finding with evidence.",
      "quotes": [
        {"text": "exact quote from transcript", "attribution": "Name, Title, Company/Industry"},
        ...
      ],
      "closing": "optional 1-2 sentence synthesis paragraph"
    },
    ...
  ],
  "additional_sections": [],
  "outstanding_questions": [
    {"label": "Short Label", "text": "Explanation of the question or concern raised."},
    ...
  ],
  "future_requests": {
    "intro": "Intro sentence about what respondents surfaced.",
    "items": [
      "Use case or request described in 1-2 sentences.",
      ...
    ],
    "closing": "Optional synthesis of the most notable request."
  },
  "sources": "Description of how interviews were conducted, when, where, and by whom."
}
"""


def _build_prompt(transcripts: str, objectives: str, event_name: str, product_name: str) -> str:
    return f"""You are analyzing customer interview transcripts from {event_name} about {product_name}.

RESEARCH OBJECTIVES:
{objectives}

TRANSCRIPTS:
{transcripts}

Based on these transcripts and objectives, produce a complete customer insights findings document.

Requirements:
- Identify {_count_objectives(objectives)} or more key findings tied directly to the research objectives
- Extract 2-4 verbatim or near-verbatim quotes per key finding
- Identify outstanding questions/gaps customers raised
- Identify requests for future use cases or product development
- Write the executive summary last, after reviewing all findings
- Be specific and evidence-based — every claim should be traceable to the transcripts

{FINDINGS_SCHEMA}"""


def _count_objectives(objectives: str) -> int:
    lines = [l.strip() for l in objectives.strip().splitlines() if l.strip()]
    return max(3, min(len(lines) + 1, 7))


def call_gateway(
    transcripts: str,
    objectives: str,
    event_name: str,
    product_name: str,
    gateway_url: str,
    api_key: str,
    model_id: str,
) -> dict:
    """
    Calls the Salesforce AI Model Gateway and returns parsed findings JSON.
    Adjust the request format below to match your gateway's exact API contract.
    """
    prompt = _build_prompt(transcripts, objectives, event_name, product_name)

    # --- Adjust this payload to match your gateway's API format ---
    payload = {
        "model": model_id,
        "max_tokens": 8000,
        "system": SYSTEM_PROMPT,
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
        # Add any additional headers your gateway requires here
    }

    response = requests.post(gateway_url, json=payload, headers=headers, timeout=120)
    response.raise_for_status()

    response_data = response.json()

    # Extract the text content — adjust this path to match your gateway's response format
    # Common patterns:
    #   response_data["content"][0]["text"]          (Anthropic API format)
    #   response_data["choices"][0]["message"]["content"]  (OpenAI-compatible format)
    #   response_data["output"]["message"]["content"][0]["text"]  (Bedrock format)
    raw_text = _extract_text(response_data)

    # Parse the JSON findings
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"```(?:json)?", "", cleaned).strip().rstrip("`").strip()

    return json.loads(cleaned)


def _extract_text(response_data: dict) -> str:
    """Try common response formats to extract the assistant's text."""
    # Anthropic Messages API format
    if "content" in response_data and isinstance(response_data["content"], list):
        return response_data["content"][0]["text"]
    # OpenAI-compatible format
    if "choices" in response_data:
        return response_data["choices"][0]["message"]["content"]
    # AWS Bedrock direct format
    if "output" in response_data:
        output = response_data["output"]
        if "message" in output:
            return output["message"]["content"][0]["text"]
    # Fallback: look for any "text" key
    if "text" in response_data:
        return response_data["text"]
    raise ValueError(f"Unrecognized gateway response format: {list(response_data.keys())}")


import re
