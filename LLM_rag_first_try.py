from openai import OpenAI
import os
from pathlib import Path

# --- 1. SETUP ---

# Create the OpenAI client object with your API key
# In production, you should NOT hardcode your API key — store it in an environment variable instead.
# Example: set the key in your OS → os.environ["OPENAI_API_KEY"] = "sk-..."
client = OpenAI(api_key="sk-your-key")

# If you already have a vector store (permanent document index) created in your OpenAI account,
# put its ID here so we can reuse it without re-uploading files every time.
# Otherwise, set this to None and the script will create a new one.
VECTOR_STORE_ID = "vs_6896714506888191b782deb94f80fc03"

# Path to your PDF file you want to upload and query.
# Must be accessible from this machine.
PDF_PATH = r"C:\Users\finni\OneDrive\Dokumente\ETH\Climate Finance\Impact on Finance\IRENA_Risk_Mitigation_and_Structured_Finance_2016.pdf"


# --- 2. HELPER FUNCTIONS ---

def ensure_vector_store_and_upload(pdf_path: str, vector_store_id: str | None):
    """
    Ensures we have a vector store ready.
    If vector_store_id is provided, reuse it.
    If not, create a new store, upload the PDF, and return the new store's ID.

    Vector stores are permanent indexes in OpenAI that store embeddings
    of your documents for fast semantic search.
    """
    if vector_store_id:
        print("Reusing existing vector store:", vector_store_id)
        return vector_store_id

    # Create a new permanent vector store named "Geothermal Papers"
    store = client.vector_stores.create(name="Geothermal Papers")

    # Upload the PDF into the vector store and poll until the indexing is done
    with open(pdf_path, "rb") as f:
        batch = client.vector_stores.file_batches.upload_and_poll(
            vector_store_id=store.id,
            files=[f],
        )

    # Check if the upload/indexing was successful
    if batch.status != "completed":
        raise RuntimeError(
            f"Upload failed, status={batch.status}, counts={batch.file_counts}"
        )

    print("Upload completed:", batch.file_counts)
    return store.id


def ask_with_file_search(vector_store_id: str, question: str) -> str:
    """
    Sends a question to the GPT model using the Responses API,
    with File Search enabled against the given vector store.

    The `tools` list includes a file_search tool and tells the model
    which vector store(s) to use for retrieval.
    """
    resp = client.responses.create(
        model="gpt-4o",  # Model to use for answering
        input=question,  # The user's question
        tools=[{
            "type": "file_search",
            "vector_store_ids": [vector_store_id],  # Which vector store(s) to search
        }],
    )

    # The Responses API structures the output, but we can use `output_text`
    # to get the combined text answer directly.
    return resp.output_text


# --- 3. MAIN SCRIPT ---

def main():
    """
    Main function to:
    1. Ensure we have a vector store with the PDF indexed
    2. Ask a question about the PDF
    3. Print the model's answer
    """
    # Check the PDF exists locally
    assert Path(PDF_PATH).exists(), f"PDF path does not exist: {PDF_PATH}"

    # Get or create vector store ID
    vs_id = ensure_vector_store_and_upload(PDF_PATH, VECTOR_STORE_ID)

    print("Using vector store:", vs_id)

    # Define your question
    question = (
        "Summarise key risk mitigation and structured finance mechanisms in the report, "
        "include page citations"
    )

    # Ask the question and get the answer
    answer = ask_with_file_search(vs_id, question)

    # Print the answer nicely
    print("\n=== ANSWER ===\n")
    print(answer)


if __name__ == "__main__":
    main()
