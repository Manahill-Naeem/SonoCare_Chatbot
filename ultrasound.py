import os
import asyncio
import base64
import requests
from dotenv import load_dotenv
from agents import AsyncOpenAI, OpenAIChatCompletionsModel, Agent, Runner, set_tracing_disabled, function_tool
from duckduckgo_search import DDGS
from datetime import datetime
import json

load_dotenv()
set_tracing_disabled(True)

external_client = AsyncOpenAI(
    api_key=os.getenv("GEMINI_API_KEY"),
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
)
model = OpenAIChatCompletionsModel(
    model="gemini-2.0-flash",
    openai_client=external_client,
)

@function_tool
def search_info_tool(query: str) -> str:
    """
    Searches for information related to ultrasound scans.
    """
    try:
        ddg_results = DDGS().text(keywords=query, max_results=3)
        results = list(ddg_results) if ddg_results else []
    except Exception:
        return "No internet connection or search service unavailable."
    if not results:
        return "No results found."
    formatted_results = []
    for r in results:
        formatted_results.append(f"Title: {r['title']}\nURL: {r['href']}\nDescription: {r['body']}")
    return "\n\n".join(formatted_results)

@function_tool
def preparation_guide_tool(query: str) -> str:
    """
    Provides preparation guides for specific ultrasound types.
    """
    if "abdomen" in query.lower():
        return "#Purpose: To visualize abdominal organs.\n#Preparation: Fast for 6-8 hours before the scan."
    elif "pelvic" in query.lower() or "pelvis" in query.lower():
        return "#Purpose: To visualize pelvic organs.\n#Preparation: Drink several glasses of water to ensure a full bladder."
    elif "obstetric" in query.lower() or "obs" in query.lower():
        return "#Purpose: To monitor fetal development.\n#Preparation: No specific preparation is needed, but wearing loose clothing is recommended."
    elif "kidneys" in query.lower():
        return "#Purpose: To visualize the kidneys.\n#Preparation: Drink 1 liter of water one hour before the appointment and do not urinate."
    else:
        return "Sorry, preparation details for this scan is not available."

@function_tool
def appointment_booking_tool() -> str:
    """
    Provides a link to the appointment booking form.
    """
    FORM_LINK = "https://docs.google.com/forms/d/e/1FAIpQLSeF0RvnrhnpxBlMWOg0hIJlAatg1BE9-0CRi5v7HYcLyaq8pA/viewform?usp=dialog"
    return f"To book an appointment, please fill out this form: {FORM_LINK}"

@function_tool
def outofscope_guardrail_tool(query: str) -> str:
    return "I am sorry, but I can only assist with questions about ultrasound information and appointment booking. Please ask me about those topics."


def text_to_speech_tool(text: str) -> bytes:
    """
    Converts text to speech using the Gemini TTS API.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("GEMINI_API_KEY is not set; skipping TTS.")
        return None

    payload = {
        "contents": [
            {
                "parts": [{"text": text}]
            }
        ],
        "generationConfig": {
            "response_mime_type": "audio/mpeg"
        }
    }
    api_url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-2.5-flash:generateContent?key={api_key}"
    )
    print("TTS payload:", payload)
    print("TTS api_url:", api_url)
    try:
        response = requests.post(
            api_url,
            headers={"Content-Type": "application/json"},
            data=json.dumps(payload),
            timeout=30
        )
        print("TTS raw response:", response.text)
        result = response.json()
        print("TTS parsed result:", result)
        audio_data_base64 = None
        try:
            audio_data_base64 = (
                result.get('candidates', [{}])[0]
                .get('content', {}).get('parts', [{}])[0]
                .get('inline_data', {}).get('data')
            )
        except Exception as parse_err:
            print(f"Error parsing TTS response: {parse_err}")
        if audio_data_base64:
            print("TTS audio_data_base64 found.")
            audio_bytes = base64.b64decode(audio_data_base64)
            # Save to file for debugging
            try:
                with open("tts_debug.mp3", "wb") as f:
                    f.write(audio_bytes)
                print("TTS audio written to tts_debug.mp3")
            except Exception as file_err:
                print(f"Error writing TTS audio to file: {file_err}")
            return audio_bytes
        else:
            print("TTS audio_data_base64 NOT found.")
    except Exception as e:
        print(f"Error in TTS API call: {e}")
        return None
    return None

def check_output_for_safety(output: str) -> str:
    undesired_phrases = ["error", "i am sorry", "i cannot provide", "invalid date"]
    for phrase in undesired_phrases:
        if phrase in output.lower():
            return "I am sorry, there seems to be an issue with my response. Please try asking again in a different way."
    return output

information_guide_agent = Agent(
    name="Information guide Assistant",
    instructions="You will provide the information of ultrasound to the users according to their queries",
    model=model,
    tools=[search_info_tool, preparation_guide_tool]
)

UltrasoundAgent = Agent(
    name="Ultrasound Assistant",
    instructions="""
    You are the central assistant for SonoCare. Your role is to determine the user's intent and hand off the conversation to the correct specialized agent.
    - If the user is asking for information or a preparation guide about ultrasound, hand off the conversation to the '{information_guide_agent.name}' agent.
    - If the user is trying to book an appointment, you must provide the booking form link by calling the 'appointment_booking_tool'.
    - If the user's request is not related to these two topics, you must hand off to the outofscope_guardrail_tool.
    """,
    model=model,
    handoffs=[information_guide_agent],
    tools=[appointment_booking_tool, outofscope_guardrail_tool]
)

def streamlit_run_agent(user_input: str, use_voice: bool = False) -> tuple[str, bytes]:
    """
    Takes input from the Streamlit UI, runs the agent, and returns the output.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        runner = Runner()
        current_agent = UltrasoundAgent
        result = loop.run_until_complete(
            runner.run(
                starting_agent=current_agent,
                input=user_input,
            )
        )
        safe_output = check_output_for_safety(result.final_output)

        audio_data = None
        if use_voice and safe_output:
            audio_data = text_to_speech_tool(safe_output)
            
        return safe_output, audio_data
    except Exception as e:
        return f"An error occurred: {e}", None
    finally:
        loop.close()
