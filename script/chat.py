from __future__ import annotations

import os
import warnings
from pathlib import Path

# Suppress annoying huggingface symlink warnings for a cleaner CLI
warnings.filterwarnings("ignore", category=UserWarning, module="huggingface_hub")

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt

from core.config import load_settings, require_llm_credentials
from retrieval.index import LocalEmbeddingIndex
from retrieval.agent import build_agent, run_agent_question

console = Console()

def main():
    console.print(Panel.fit(
        "[bold blue]🚀 Agentic RAG - Chat Demo[/bold blue]\n[green]Powered by ChromaDB, Langchain & OpenRouter[/green]", 
        border_style="blue"
    ))
    
    settings = load_settings()
    try:
        require_llm_credentials(settings)
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        return

    # Ưu tiên load index REPAIRED (sạch nhất sau khi đã sửa lỗi), nếu không có thì dùng BASELINE
    if settings.paths.repaired_embeddings_json.exists():
        index_path = settings.paths.repaired_embeddings_json
        console.print(f"[dim]Loading REPAIRED index from {index_path.name}...[/dim]")
    elif settings.paths.embeddings_json.exists():
        index_path = settings.paths.embeddings_json
        console.print(f"[dim]Loading BASELINE index from {index_path.name}...[/dim]")
    else:
        console.print("[bold red]No vector index found! Please run phase 1 first.[/bold red]")
        return
        
    try:
        with console.status("[bold yellow]Initializing AI Agent & Vector Database...[/bold yellow]", spinner="dots"):
            index = LocalEmbeddingIndex.load(settings, index_path)
            agent = build_agent(settings, index)
    except Exception as e:
        console.print(f"[bold red]Failed to initialize RAG Agent:[/bold red] {e}")
        return

    console.print("[bold green]✅ Agent is ready! Type 'exit' or 'quit' to stop.[/bold green]\n")

    while True:
        try:
            question = Prompt.ask("[bold magenta]You[/bold magenta]")
            if question.strip().lower() in ["exit", "quit", "q"]:
                break
            if not question.strip():
                continue
            
            with console.status("[bold cyan]🤖 Agent is searching and thinking...[/bold cyan]", spinner="dots"):
                answer = run_agent_question(agent, question)
            
            console.print(Panel(
                Markdown(answer), 
                title="[bold cyan]AI Assistant[/bold cyan]", 
                border_style="cyan"
            ))
        
        except KeyboardInterrupt:
            break
        except Exception as e:
            console.print(f"[bold red]Error during inference:[/bold red] {e}")

    console.print("\n[bold blue]👋 Goodbye![/bold blue]")

if __name__ == "__main__":
    main()
