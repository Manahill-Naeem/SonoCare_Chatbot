import os
import asyncio
from dotenv import load_dotenv
from agents import AsyncOpenAI, OpenAIChatCompletionsModel, Agent, Runner, set_tracing_disabled, function_tool, tool
from duckduckgo_search import DDGS
from datetime import datetime

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
def search_info_tool(query:str) -> str:
    """git 
    Searches for information related to ultrasound scans.
    """
    results = DDGS().text(keywords=query, max_results=3)
    if not results: return "No results found."
    formatted_results = []
    for r in results: formatted_results.append(f"Title: {r['title']}\nURL: {r['href']}\nDescription: {r['body']}")
    return "\n\n".join(formatted_results)

@function_tool
def preparation_guide_tool(query:str) -> str:
    """
    Provides preparation guides for specific ultrasound types.
    """
    if "abdomen" in query.lower():
        return "#Purpose: To visualize abdominal organs.\n#Preparation: Fast for 6-8 hours before the scan."
    elif "pelvic" in query.lower() or "pelvis" in query.lower():
        return "#Purpose: To visualize pelvic organs.\n#Preparation: Drink several glasses of water to ensure a full bladder."
    elif "obsteric" in query.lower() or "obs" in query.lower():
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
def outofscope_guardrail_tool(query:str) -> str:
    return "I am sorry, but I can only assist with questions about ultrasound information and appointment booking. Please ask me about those topics."

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
    handoffs=[information_guide_agent, outofscope_guardrail_tool],
    tools=[appointment_booking_tool]
)


def streamlit_run_agent(user_input: str) -> str:
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
        return safe_output
    except Exception as e:
        return f"An error occurred: {e}"
    finally:
        loop.close()



