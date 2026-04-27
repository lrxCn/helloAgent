import asyncio
from langchain_core.documents import Document
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
import os

os.environ["OPENAI_API_KEY"] = "sk-fake"
os.environ["OPENAI_BASE_URL"] = "http://localhost:8080"

llm = ChatOpenAI(model="fake")

prompt = ChatPromptTemplate.from_messages([
    ("system", "SYS: {sys_var}\n\nCTX: {context}"),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{question}")
])

document_prompt = PromptTemplate(
    input_variables=["page_content", "source"],
    template="[src: {source}] {page_content}"
)

chain = create_stuff_documents_chain(
    llm=llm,
    prompt=prompt,
    document_prompt=document_prompt,
    document_variable_name="context"
)

# Just check the prompt generation
formatted = prompt.format(sys_var="HELLO", context=chain._format_docs([]), chat_history=[], question="test")
print("EMPTY DOCS:")
print(formatted)

docs = [Document(page_content="doc1", metadata={"source": "file1"})]
formatted2 = prompt.format(sys_var="HELLO", context=chain._format_docs(docs), chat_history=[], question="test")
print("\nWITH DOCS:")
print(formatted2)

