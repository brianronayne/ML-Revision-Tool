from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich import box

console = Console()


def show_question(card: dict, index: int, total: int) -> None:
    source = card.get("source", "")
    header = f"[dim]{source}[/dim]  [bold cyan]{index}/{total}[/bold cyan]"
    console.print(Panel(f"\n[bold]{card['question']}[/bold]\n", title=header, border_style="cyan"))


def show_answer(card: dict) -> None:
    console.print(Panel(f"\n{card['answer']}\n", title="[green]Answer[/green]", border_style="green"))


def prompt_reveal() -> None:
    console.print("[dim]Press [bold]Enter[/bold] to reveal answer...[/dim]", end="")
    input()


def prompt_rating() -> int:
    console.print(
        "\n  [red][1] Again[/red]  [yellow][2] Hard[/yellow]  [green][3] Good[/green]\n",
        end="",
    )
    while True:
        choice = input("  Rating: ").strip()
        if choice in ("1", "2", "3"):
            return int(choice)
        console.print("  [dim]Enter 1, 2, or 3.[/dim]")


def show_session_stats(seen: int, again: int, hard: int, good: int) -> None:
    console.rule("[bold]Session Complete[/bold]")
    table = Table(box=box.SIMPLE, show_header=False)
    table.add_row("[cyan]Cards reviewed[/cyan]", str(seen))
    table.add_row("[green]Good[/green]", str(good))
    table.add_row("[yellow]Hard[/yellow]", str(hard))
    table.add_row("[red]Again[/red]", str(again))
    console.print(table)


def show_deck_stats(stats: dict) -> None:
    console.rule("[bold]Deck Stats[/bold]")
    table = Table(box=box.SIMPLE, show_header=False)
    table.add_row("[cyan]New cards[/cyan]", str(stats["new"]))
    table.add_row("[bold]Due now[/bold]", str(stats["due"]))
    table.add_row("Bucket 0 (learning)", str(stats["bucket_0"]))
    table.add_row("Bucket 1 (hard)", str(stats["bucket_1"]))
    table.add_row("Bucket 2 (known)", str(stats["bucket_2"]))
    console.print(table)


def show_no_cards() -> None:
    console.print(Panel("[green]Nothing due right now. Come back later![/green]", border_style="green"))


def show_tags(tag_counts: dict) -> None:
    console.rule("[bold]Tags[/bold]")
    table = Table(box=box.SIMPLE)
    table.add_column("Tag", style="cyan")
    table.add_column("Cards", justify="right")
    for tag, count in tag_counts.items():
        table.add_row(tag, str(count))
    console.print(table)
    console.print("[dim]Filter with:[/dim] python src/main.py review --tag <name>")


def show_unknown_tag(tag: str, available: dict) -> None:
    console.print(f"[red]No cards tagged '{tag}'.[/red]")
    console.print(f"[dim]Available tags:[/dim] {', '.join(available)}")


def show_subjects(subject_counts: dict) -> None:
    console.rule("[bold]Subjects[/bold]")
    table = Table(box=box.SIMPLE)
    table.add_column("Subject", style="cyan")
    table.add_column("Cards", justify="right")
    for subject, count in subject_counts.items():
        table.add_row(subject, str(count))
    console.print(table)
    console.print("[dim]Filter with:[/dim] python src/main.py review --subject \"<name>\"")


def show_unknown_subject(subject: str, available: dict) -> None:
    console.print(f"[red]No subject '{subject}'.[/red]")
    console.print(f"[dim]Available subjects:[/dim] {', '.join(available)}")
