"""Script is used to initialize the Qdrant db backend with Azure OpenAI."""
import os

import openai
from dotenv import load_dotenv
from langchain.text_splitter import NLTKTextSplitter
from langchain_community.document_loaders import DirectoryLoader, PyPDFium2Loader, TextLoader
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.retrievers import BaseRetriever
from langchain_core.runnables import RunnablePassthrough
from langchain_openai import ChatOpenAI
from langchain_openai.embeddings import AzureOpenAIEmbeddings, OpenAIEmbeddings
from loguru import logger
from omegaconf import DictConfig
from ultra_simple_config import load_config

from agent.backend.LLMBase import LLMBase
from agent.data_model.request_data_model import RAGRequest, SearchParams
from agent.utils.utility import generate_prompt
from agent.utils.vdb import generate_collection_openai, init_vdb

load_dotenv()


class OpenAIService(LLMBase):

    """OpenAI Backend Service."""

    @load_config(location="config/main.yml")
    def __init__(self, cfg: DictConfig, collection_name: str, token: str) -> None:
        """Init the OpenAI Service."""
        super().__init__(token=token, collection_name=collection_name)

        """Openai Service."""
        if token:
            self.openai_token = token
        else:
            self.openai_token = os.getenv("OPENAI_API_KEY")

        if not self.openai_token:
            msg = "API Token not provided!"
            raise ValueError(msg)

        self.cfg = cfg

        if collection_name:
            self.collection_name = collection_name
        else:
            self.collection_name = self.cfg.qdrant.collection_name_openai

        template = load_prompt_template(prompt_name="cohere_chat.j2", task="chat")
        self.prompt = ChatPromptTemplate.from_template(template=template, template_format="jinja2")

        if self.cfg.openai_embeddings.azure:
            embedding = AzureOpenAIEmbeddings(
                azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
                deployment=self.cfg.openai_embeddings.embedding_model_name,
                openai_api_version=self.cfg.openai_embeddings.openai_api_version,
                openai_api_key=self.openai_token,
            )
        else:
            embedding = OpenAIEmbeddings(model=self.cfg.openai_embeddings.embedding_model_name, openai_api_key=self.openai_token)

        self.vector_db = init_vdb(self.cfg, self.collection_name, embedding=embedding)

    def create_collection(self, name: str) -> bool:
        """Create a new collection in the Vector Database.

        Args:
        ----
            name (str): The name of the new collection.

        """
        generate_collection_openai(self.cfg, name, self.openai_token)
        return True

    def embed_documents(self, directory: str, file_ending: str = ".pdf") -> None:
        """Embeds the documents in the given directory.

        Args:
        ----
            directory (str): PDF Directory.
            file_ending (str): File ending of the documents.

        """
        if file_ending == ".pdf":
            loader = DirectoryLoader(directory, glob="*" + file_ending, loader_cls=PyPDFium2Loader)
        elif file_ending == ".txt":
            loader = DirectoryLoader(directory, glob="*" + file_ending, loader_cls=TextLoader)
        else:
            msg = "File ending not supported."
            raise ValueError(msg)

        splitter = NLTKTextSplitter(length_function=len, chunk_size=500, chunk_overlap=75)

        docs = loader.load_and_split(splitter)

        logger.info(f"Loaded {len(docs)} documents.")
        text_list = [doc.page_content for doc in docs]
        metadata_list = [doc.metadata for doc in docs]

        for m in metadata_list:
            # only when there are / in the source
            if "/" in m["source"]:
                m["source"] = m["source"].split("/")[-1]

        self.vector_db.add_texts(texts=text_list, metadatas=metadata_list)

        logger.info("SUCCESS: Texts embedded.")

    def search(self, search: SearchParams) -> BaseRetriever:
        """Searches the documents in the Qdrant DB with a specific query.

        Args:
        ----
            search (SearchRequest): The search request object.
            filtering (Filtering): The filtering object.

        Returns:
        -------
            List[Tuple[Document, float]]: A list of search results, where each result is a tuple
            containing a Document object and a float score.

        """
        search = dict(search)
        search.pop("query")

        return self.vector_db.as_retriever(search_kwargs=search)

    def summarize_text(self, text: str) -> str:
        """Summarizes the given text using the OpenAI API.

        Args:
        ----
            text (str): The text to be summarized.
            token (str): The token for the OpenAI API.

        Returns:
        -------
            str: The summary of the text.

        """
        prompt = generate_prompt(prompt_name="openai-summarization.j2", text=text, language="de")

        openai.api_key = self.token
        response = openai.chat.completions.create(
            model=self.cfg.openai_completion.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=self.cfg.openai_completion.temperature,
            max_tokens=self.cfg.openai_completion.max_tokens,
            top_p=self.cfg.openai_completion.top_p,
            frequency_penalty=self.cfg.openai_completion.frequency_penalty,
            presence_penalty=self.cfg.openai_completion.presence_penalty,
            stop=self.cfg.openai_completion.stop,
            stream=False,
        )

        return response.choices[0].messages.content

    def generate(self, prompt: str) -> str:
        """Sent completion request to OpenAI API.

        Args:
        ----
            prompt (str): The text on which the completion should be based.

        Returns:
        -------
            str: Response from the OpenAI API.

        """
        openai.api_key = self.token
        response = openai.chat.completions.create(
            model=self.cfg.openai_completion.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=self.cfg.openai_completion.temperature,
            max_tokens=self.cfg.openai_completion.max_tokens,
            top_p=self.cfg.openai_completion.top_p,
            frequency_penalty=self.cfg.openai_completion.frequency_penalty,
            presence_penalty=self.cfg.openai_completion.presence_penalty,
            stop=self.cfg.openai_completion.stop,
            stream=False,
        )

        return response.choices[0].message.content

    def rag(self, rag: RAGRequest, search: SearchParams) -> tuple:
        """QA Function for OpenAI LLMs.

        Args:
        ----
            rag (RAGRequest): The RAG Request Object.
            search (SearchRequest): The search request object.
            filtering (Filtering): The filtering object.

        Returns:
        -------
            tuple: answer, prompt, meta_data

        """
        search_chain = self.search(search=search)
        return (
            {"context": search_chain | format_docs, "question": RunnablePassthrough()} | prompt | ChatOpenAI(model=self.cfg.openai_completion.model) | StrOutputParser()
        )


if __name__ == "__main__":
    token = os.getenv("OPENAI_API_KEY")
    query = "Was ist Attention?"
    logger.info(f"Token: {token}")

    from agent.data_model.request_data_model import SearchParams

    if not token:
        msg = "OPENAI_API_KEY is not set."
        raise ValueError(msg)

    openai_service = OpenAIService(collection_name="openai", token=token)

    rag_chain = openai_service.create_rag_chain(search_chain=retriever)

    answer = rag_chain.invoke(query)

    logger.info("Answer: {answer}")
