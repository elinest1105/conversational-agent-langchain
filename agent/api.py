"""FastAPI Backend for the Knowledge Agent."""
import os
import uuid
from typing import List

from fastapi import FastAPI, File, UploadFile
from loguru import logger
from starlette.responses import JSONResponse

from agent.backend.aleph_alpha_service import (
    embedd_documents_aleph_alpha,
    explain_completion,
    qa_aleph_alpha,
    search_documents_aleph_alpha,
)
from agent.backend.open_ai_service import (
    embedd_documents_openai,
    search_documents_openai,
)

# initialize the Fast API Application.
app = FastAPI(debug=True)


@app.get("/")
def read_root() -> str:
    """Root Message.

    :return: Welcome Message
    :rtype: string
    """
    return "Welcome to the Simple Aleph Alpha FastAPI Backend!"


def embedd_documents_wrapper(folder_name: str, aa_or_openai: str = "openai", token: str = None):
    """Call the right embedding function for the choosen backend.

    :param folder_name: _description_
    :type folder_name: str
    :param aa_or_openai: _description_, defaults to "openai"
    :type aa_or_openai: str, optional
    :param aleph_alpha_token: _description_, defaults to None
    :type aleph_alpha_token: str, optional
    :raises ValueError: _description_
    """
    if aa_or_openai == "aleph-alpha":
        # Embedd the documents with Aleph Alpha
        embedd_documents_aleph_alpha(dir=folder_name, aleph_alpha_token=token)
    elif aa_or_openai == "openai":
        # Embedd the documents with OpenAI
        embedd_documents_openai(dir=folder_name, open_ai_token=token)
    else:
        raise ValueError("Please provide either 'aleph-alpha' or 'openai' as a parameter. Other backends are not implemented yet.")


def create_tmp_folder() -> str:
    """Creates a temporary folder for files to store.

    :return: The directory name
    :rtype: str
    """
    # Create a temporary folder to save the files
    tmp_dir = f"tmp_{str(uuid.uuid4())}"
    os.makedirs(tmp_dir)
    logger.info(f"Created new folder {tmp_dir}.")
    return tmp_dir


@app.post("/embedd_documents")
async def upload_documents(files: List[UploadFile] = File(...), aa_or_openai: str = "openai", token: str = None):
    """Upload multiple documents to the backend.

    :param files: Uploaded files, defaults to File(...)
    :type files: List[UploadFile], optional
    :return: Return as JSON
    :rtype: JSONResponse
    """
    tmp_dir = create_tmp_folder()

    file_names = []

    for file in files:
        file_name = file.filename
        file_names.append(file_name)

        # Save the file to the temporary folder
        with open(os.path.join(tmp_dir, file_name), "wb") as f:
            f.write(await file.read())

    embedd_documents_wrapper(folder_name=tmp_dir, aa_or_openai=aa_or_openai, token=token)
    return JSONResponse(content={"message": "Files received and saved.", "filenames": file_names})


@app.post("/embedd_document/")
async def embedd_one_document(file: UploadFile, aa_or_openai: str = "openai", token: str = None):
    """Upload one document to the backend.

    To embedd the document in
    the database it is necessary to provide the name of the backend
    as well as the fitting token for that backend.

    :param file: File that is uploaded, should be a pdf file.
    :type file: UploadFile
    :param aa_or_openai: Backend to use, defaults to "openai"
    :type aa_or_openai: str, optional
    :param aleph_alpha_token: , defaults to None
    :type aleph_alpha_token: str, optional
    :return: Response which Files were recieved and saved.
    :rtype: JSON Response
    """
    # Create a temporary folder to save the files
    tmp_dir = create_tmp_folder()

    tmp_file_path = os.path.join(tmp_dir, str(file.filename))

    logger.info(tmp_file_path)
    print(tmp_file_path)

    with open(tmp_file_path, "wb") as f:
        f.write(await file.read())

    embedd_documents_wrapper(folder_name=tmp_dir, aa_or_openai=aa_or_openai, token=token)
    return JSONResponse(content={"message": "File received and saved.", "filenames": file.filename})


@app.get("/search")
def search(query: str, aa_or_openai: str = "openai", token: str = None, amount: int = 3) -> None:
    """Search for a query in the vector database.

    :param query: The search query
    :type query: str
    :param aa_or_openai: The LLM Provider, defaults to "openai"
    :type aa_or_openai: str, optional
    :param token: Token for the LLM Provider, defaults to None
    :type token: str, optional
    :raises ValueError: If the LLM Provider is not implemented yet
    """
    return search_db(query=query, aa_or_openai=aa_or_openai, token=token, amount=amount)


@app.get("/qa")
def question_answer(query: str = None, aa_or_openai: str = "openai", token: str = None, amount: int = 1):
    """Answer a question based on the documents in the database.

    :param query: _description_
    :type query: str
    :param aa_or_openai: _description_, defaults to "openai"
    :type aa_or_openai: str, optional
    :param token: _description_, defaults to None
    :type token: str, optional
    :param amount: _description_, defaults to 1
    :type amount: int, optional
    """
    # if the query is not provided, raise an error
    if query is None:
        raise ValueError("Please provide a Question.")

    documents = search_db(query=query, aa_or_openai=aa_or_openai, token=token, amount=amount)

    # call the qa function
    answer, prompt, meta_data = qa_aleph_alpha(query=query, documents=documents, aleph_alpha_token=token)

    return answer, prompt, meta_data


@app.post("/explain")
def explain_output(prompt: str, output: str, token: str = None):
    """Explain the output of the question answering system.

    :param prompt: _description_
    :type prompt: str
    :param answer: _description_
    :type answer: str
    :param token: _description_, defaults to None
    :type token: str, optional
    """
    # explain the output
    logger.info(f"OUtput {output}")
    explanation = explain_completion(prompt=prompt, output=output, token=token)

    return explanation


def search_db(query: str, aa_or_openai: str = "openai", token: str = None, amount: int = 3):
    """Search the database for a query.

    :param query: _description_
    :type query: str
    :param aa_or_openai: _description_, defaults to "openai"
    :type aa_or_openai: str, optional
    :param token: _description_, defaults to None
    :type token: str, optional
    :param amount: _description_, defaults to 3
    :type amount: int, optional
    :raises ValueError: _description_
    :return: _description_
    :rtype: _type_
    """
    if aa_or_openai in {"aleph-alpha", "aleph_alpha", "aa"}:
        # Embedd the documents with Aleph Alpha
        documents = search_documents_aleph_alpha(aleph_alpha_token=token, query=query, amount=amount)
    elif aa_or_openai == "openai":
        documents = search_documents_openai(open_ai_token=token, query=query, amount=amount)

        # Embedd the documents with OpenAI#
    else:
        raise ValueError("Please provide either 'aleph-alpha' or 'openai' as a parameter. Other backends are not implemented yet.")

    logger.info(f"Found {len(documents)} documents.")

    return documents
