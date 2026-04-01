# gemini_client.py

import streamlit as st
import google.generativeai as genai


MODEL_NAME = "gemini-2.5-pro"


def configure_gemini():
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)


def get_model(system_prompt: str):
    return genai.GenerativeModel(
        model_name=MODEL_NAME,
        system_instruction=system_prompt,
    )


def generate_text_response(system_prompt: str, user_input: str) -> str:
    configure_gemini()
    model = get_model(system_prompt)
    response = model.generate_content(user_input)
    return response.text


def generate_multimodal_response(system_prompt: str, image, user_input: str) -> str:
    configure_gemini()
    model = get_model(system_prompt)
    response = model.generate_content([image, user_input])
    return response.text
