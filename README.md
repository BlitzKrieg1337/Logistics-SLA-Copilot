TENTATIVE FILE STRUCTURE

logistics sla copilot/
│
├── .env                        # API keys (Gemini, LangSmith, FX API, Web Search)
├── .gitignore                  # Prevents committing data/ and __pycache__/
├── requirements.txt            # Python dependencies
├── README.md                   # System design & run instructions for your CV
│
├── data/                       # Local Storage (Git Ignored for security)
│   ├── supply_chain.db         # The local SQLite database
│   ├── contracts/              # Mock Vendor MSAs (e.g., Dell_Contract.md)
│   └── vector_store/           # ChromaDB/FAISS embeddings for RAG
│
└── src/                        # Main Application Source Code
    │
    ├── database/               # Data Layer (Phase 1 scripts)
    │   ├── seed_sqlite.py      # Creates SQLite schema & inserts mock orders
    │   └── build_vector_db.py  # Chunks contracts and builds the vector store
    │
    ├── tools/                  # The Agent's Toolbelt
    │   ├── __init__.py
    │   ├── sql_tools.py        # query_db (with try/except self-correction)
    │   ├── rag_tools.py        # search_vendor_contracts
    │   ├── live_api_tools.py   # convert_currency (FX) & check_force_majeure (News)
    │   └── math_tools.py       # calculate_penalty (pure deterministic Python)
    │
    ├── agent/                  # LangGraph Orchestration Layer
    │   ├── __init__.py
    │   ├── state.py            # TypedDict state definition (messages)
    │   └── graph.py            # Nodes, routing edges, and the HITL logic
    │
    └── ui/                     # Frontend Layer
        └── dashboard.py        # Streamlit app (Chat UI, Trace Expanders, Approvals)