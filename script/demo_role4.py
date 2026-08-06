from __future__ import annotations

import os
import pandas as pd
from core.config import load_settings, require_llm_credentials
from retrieval.index import LocalEmbeddingIndex
from retrieval.agent import build_agent, run_agent_question
from core.utils import write_json


def main():
    print("=== ROLE 4: RAG & AGENT DEMO ===")
    settings = load_settings()

    # 1. Load clean CSV data
    clean_csv_path = settings.paths.clean_csv
    if not clean_csv_path.exists():
        print(f"Error: Clean CSV not found at {clean_csv_path}. Please check Role 3's output.")
        return

    print(f"Loading clean dataset from: {clean_csv_path}...")
    df = pd.read_csv(clean_csv_path)
    print(f"Total clean papers: {len(df)}")

    # 2. Build Chroma index ( papers-baseline )
    print("\n[Step 1] Building Chroma vector index...")
    index = LocalEmbeddingIndex.build(df, settings, settings.paths.embeddings_json)
    print("Vector index built successfully!")

    # 3. Test semantic search
    print("\n[Step 2] Testing Semantic Search...")
    test_query = "large language models agentic retrieval"
    print(f"Query: '{test_query}'")
    search_results = index.search(test_query, top_k=2)
    for i, res in enumerate(search_results):
        print(f"  [{i+1}] Paper ID: {res.paper_id}")
        print(f"      Title: {res.title}")
        print(f"      Similarity Score: {res.score:.4f}")

    # 4. Test exact lookup
    print("\n[Step 3] Testing Exact Lookup...")
    if len(df) > 0:
        sample_title = df.iloc[0]["title"]
        print(f"Looking up paper with title: '{sample_title}'")
        lookup_result = index.lookup(sample_title)
        if lookup_result:
            print(f"  Found Paper ID: {lookup_result['paper_id']}")
        else:
            print("  Paper not found.")

    # 5. Build RAG Agent
    print("\n[Step 4] Initializing RAG Agent...")
    try:
        require_llm_credentials(settings)
        agent = build_agent(settings, index)
        print("RAG Agent initialized successfully!")

        # Run test questions
        questions = [
            f"Who authored the paper '{sample_title}'?",
            "Tell me about the agentic retrieval augmented generation papers."
        ]

        demo_answers = []
        for q in questions:
            print(f"\nAsking Agent: '{q}'")
            ans = run_agent_question(agent, q)
            print(f"Agent response: {ans}")
            demo_answers.append({
                "question": q,
                "answer": ans
            })

        # Save answers
        write_json(settings.paths.demo_answers, demo_answers)
        print(f"\nSaved agent demo answers to: {settings.paths.demo_answers}")
    except Exception as e:
        print(f"\n[Agent Skipped] Could not run Agent: {e}")
        print("Tip: Set the correct API key in the .env file to enable the LLM Agent. The retrieval index is fully functional.")


if __name__ == "__main__":
    main()
