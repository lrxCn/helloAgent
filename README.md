# helloAgent

<!-- load -->

langchain_community.document_loaders

<!-- chunk -->

langchain_text_splitters

<!-- save -->

langchain_qdrant.from_documents

<!-- get instance -->

QdrantVectorStore.from_existing_collection

<!-- similarity search -->

QdrantVectorStore.similarity_search

<!-- chat -->

```python
prompt = langchain_core.prompts.from_messages([
    ("system", SYSTEM_PROMPT),
    ("human", "{question}"),
])
```

```python
llm = langchain_openai(
    model=OPENAI_MODEL_NAME,
    base_url=OPENAI_BASE_URL,
    api_key=OPENAI_API_KEY,
)
```

chain = prompt | llm | langchain_core.output_parsers
