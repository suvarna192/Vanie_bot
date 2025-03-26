import json
from pymongo import MongoClient
from bson import ObjectId
from langchain.schema import HumanMessage
from langchain_groq import ChatGroq

# === Load ChatGroq LLM ===
llm = ChatGroq(
    temperature=0,
    groq_api_key="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",  # Replace with actual API key
    model_name="llama-3.3-70b-versatile"
)

# === MongoDB Connection ===
mongo_uri = "mongodb://testuser:mypwd1234@192.168.120.142:27017/?authSource=Call_Audit_Automation"
client = MongoClient(mongo_uri)
db = client["Call_Audit_Automation"]
collection = db["nonLiveData"]

def query_mongodb(user_input):
    """
    Converts user input into a MongoDB query, executes it, and returns a generative LLM answer.
    """
    prompt = f"""
    Convert the following query into a MongoDB filter.

    Query: "{user_input}"

    Response format: Strict JSON with `filter` and `projection` fields.

    - The `filter` must include all relevant fields (e.g., `month`, `year`, `processGroup`, `type`) if necessary.
    - The `projection` should include the fields explicitly mentioned in the query.

    Example Input: "What was the fatal score for PAM in October 2023 for callAuditData?"
    Example Output:
    {{
        "filter": {{"month": "October", "year": 2023, "processGroup": "PAM", "type": "callAuditData"}},
        "projection": {{"fatalScore": 1, "_id": 0}}
    }}
    """

    llm_response = llm.invoke([HumanMessage(content=prompt)])

    try:
        # Extract and parse JSON from LLM response
        response_text = llm_response.content.strip()
        json_start = response_text.find("{")
        json_end = response_text.rfind("}")
        json_data = response_text[json_start : json_end + 1]
        mongo_query = json.loads(json_data)

        # Ensure the generated query doesn't include incorrect fields
        filter_criteria = mongo_query.get("filter", {})
        projection = mongo_query.get("projection", {})

        # ✅ Fix: Convert `_id` to `ObjectId` if it's a string
        if "_id" in filter_criteria and isinstance(filter_criteria["_id"], str):
            try:
                filter_criteria["_id"] = ObjectId(filter_criteria["_id"])
            except:
                return "Invalid ObjectId format."

        # Execute MongoDB Query
        results = list(collection.find(filter_criteria, projection))

        if not results:
            return "No matching records found."

        # ✅ Pass results to LLM for a natural response
        return generate_llm_answer(user_input, results)

    except json.JSONDecodeError as json_err:
        return f"JSON Parsing Error: {str(json_err)}\nRaw LLM Output: {llm_response.content}"
    
    except Exception as e:
        return f"Error: {str(e)}"

# === Function to Generate LLM Answer ===
def generate_llm_answer(user_query, mongo_results):
    """
    Takes the user's query and MongoDB results, then uses LLM to generate a human-like response.
    """
    prompt = f"""
    You are an AI assistant answering questions based on MongoDB query results.

    User Query: "{user_query}"

    Data Retrieved from MongoDB:
    {json.dumps(mongo_results, indent=4)}

    Provide a clear, natural-language response based on this data.
    """

    llm_response = llm.invoke([HumanMessage(content=prompt)])
    return llm_response.content.strip()

# === Final Result Function (For WebSocket & API Integration) ===
async def final_result(user_input):
    """
    Asynchronous function that fetches MongoDB query results and returns the final response.
    """
    response = query_mongodb(user_input)
    return response  # Ensure it returns a string

def load_llm():
    """Function to load the LLM instance if needed."""
    return ChatGroq(
        temperature=0,
        groq_api_key="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",  # Replace with actual API key
        model_name="llama-3.3-70b-versatile"
    )

def initialize_components():
    """Initialize the global components once."""
    global llm

    if llm is None:
        start_time = time.time()
        llm = load_llm()
        logging.info(f"LLM loaded in {time.time() - start_time:.2f} seconds")