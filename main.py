#!/usr/bin/env python3
import csv
import sys
from pathlib import Path
from typing import Optional

import typer
from ruamel.yaml import YAML
from typing_extensions import Annotated

app = typer.Typer()
yaml = YAML()
yaml.preserve_quotes = True
yaml.default_flow_style = False


@app.command()
def check(
    personal_yaml: Annotated[
        Optional[Path],
        typer.Option(
            help="Path to personal YAML file (default: first YAML in personal/)"
        ),
    ] = None,
):
    """
    Validate that all slugs in personal YAML file exist in reading-challenge.yaml
    and that all movie years reference actual movies.
    """
    # Find first YAML file if not specified
    if personal_yaml is None:
        personal_dir = Path("personal")
        if not personal_dir.exists():
            print(f"❌ Personal directory not found: {personal_dir}")
            raise typer.Exit(code=1)

        yaml_files = sorted(personal_dir.glob("*.yaml"))
        if not yaml_files:
            print(f"❌ No YAML files found in {personal_dir}/")
            raise typer.Exit(code=1)

        personal_yaml = yaml_files[0]
        print(f"Using {personal_yaml}")

    if not personal_yaml.exists():
        print(f"❌ Personal YAML file not found: {personal_yaml}")
        raise typer.Exit(code=1)

    # Read the main books file
    books_file = Path("reading-challenge.yaml")
    if not books_file.exists():
        print(f"❌ Books file not found: {books_file}")
        raise typer.Exit(code=1)

    with open(books_file, "r") as f:
        books_data = yaml.load(f)

    # Extract all valid slugs
    valid_slugs = {book["slug"] for book in books_data["books"]}

    # Read the user file
    with open(personal_yaml, "r") as f:
        user_data = yaml.load(f)
        read_watched = user_data["read|watched"]
        user_slugs = list(read_watched.keys())

    # Validate all slugs
    invalid_slugs = []
    for slug in user_slugs:
        if slug not in valid_slugs:
            invalid_slugs.append(slug)

    # Validate movie years reference actual movies in the book entries
    invalid_movies = []
    for slug, data in read_watched.items():
        if "movies" in data and data["movies"]:
            # Get the book entry from reading-challenge.yaml
            book_entry = next(
                (b for b in books_data["books"] if b["slug"] == slug), None
            )
            if book_entry and "movies" in book_entry:
                valid_movie_years = {m["year"] for m in book_entry["movies"]}
                user_movie_years = set(data["movies"].keys())
                invalid_years = user_movie_years - valid_movie_years
                if invalid_years:
                    invalid_movies.append(
                        f"{slug}: {', '.join(map(str, invalid_years))}"
                    )

    if invalid_slugs:
        print(f"❌ Found {len(invalid_slugs)} invalid slug(s):")
        for slug in invalid_slugs:
            print(f"  - {slug}")
        raise typer.Exit(code=1)

    if invalid_movies:
        print(f"❌ Found invalid movie years:")
        for msg in invalid_movies:
            print(f"  - {msg}")
        raise typer.Exit(code=1)

    print(f"✅ All {len(user_slugs)} slugs are valid!")
    if invalid_movies == [] and any("movies" in data for data in read_watched.values()):
        print(f"✅ All movie references are valid!")


@app.command()
def update_movies(
    personal_dir: Annotated[
        Path,
        typer.Option(help="Path to personal directory containing CSV and YAML files"),
    ] = Path("personal"),
    personal_yaml: Annotated[
        Optional[str],
        typer.Option(
            help="Name of personal YAML file (default: first YAML in personal_dir)"
        ),
    ] = None,
):
    """
    Update watched movies in personal YAML file based on CSV file of watched movies.
    Expects a CSV file with IMDb data (containing 'Const' column with tt keys).
    """
    if not personal_dir.exists():
        print(f"❌ Personal directory not found: {personal_dir}")
        raise typer.Exit(code=1)

    # Find first YAML file if not specified
    if personal_yaml is None:
        yaml_files = sorted(personal_dir.glob("*.yaml"))
        if not yaml_files:
            print(f"❌ No YAML files found in {personal_dir}/")
            raise typer.Exit(code=1)
        personal_yaml_path = yaml_files[0]
        print(f"Using {personal_yaml_path.name}")
    else:
        personal_yaml_path = personal_dir / personal_yaml

    if not personal_yaml_path.exists():
        print(f"❌ Personal YAML file not found: {personal_yaml_path}")
        raise typer.Exit(code=1)

    # Find CSV files in personal folder
    csv_files = sorted(personal_dir.glob("*.csv"))

    if not csv_files:
        print(f"❌ No CSV files found in {personal_dir}/ folder")
        raise typer.Exit(code=1)

    csv_file = csv_files[0]
    print(f"Using {csv_file.name}")

    # Read the CSV of watched movies
    watched_tt_keys = set()
    try:
        with open(csv_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if "Const" in row:
                    tt_key = row["Const"]
                    watched_tt_keys.add(tt_key)
                else:
                    print("❌ CSV missing 'Const' column")
                    raise typer.Exit(code=1)
    except Exception as e:
        print(f"❌ Error reading CSV: {e}")
        raise typer.Exit(code=1)

    print(f"{len(watched_tt_keys)} watched movies")

    # Read the main books file
    books_file = Path("reading-challenge.yaml")
    if not books_file.exists():
        print(f"❌ Books file not found: {books_file}")
        raise typer.Exit(code=1)

    with open(books_file, "r") as f:
        books_data = yaml.load(f)

    # Build a mapping: tt_key -> (slug, year)
    tt_to_book_movie = {}
    books_with_movies = 0
    total_movies = 0

    for book in books_data["books"]:
        if "movies" in book:
            books_with_movies += 1
            for movie in book["movies"]:
                total_movies += 1
                # Get tt-key directly (now stored as tt-key instead of full URL)
                tt_key = movie["imdb"]
                tt_to_book_movie[tt_key] = {
                    "slug": book["slug"],
                    "year": movie["year"],
                    "title": movie["title"],
                }

    print(f"{total_movies} movies across {books_with_movies} books")

    # Read the user file
    with open(personal_yaml_path, "r") as f:
        user_data = yaml.load(f)
        read_watched = user_data["read|watched"]

    # Find matches
    matches = []
    for tt_key in watched_tt_keys:
        if tt_key in tt_to_book_movie:
            info = tt_to_book_movie[tt_key]
            matches.append(
                {
                    "tt": tt_key,
                    "slug": info["slug"],
                    "year": info["year"],
                    "title": info["title"],
                }
            )

    print(f"{len(matches)} matches found\n")

    if matches:
        # Update user.yaml
        changes_made = 0
        for match in matches:
            slug = match["slug"]
            year = match["year"]

            # Initialize entry if it doesn't exist
            if slug not in read_watched:
                read_watched[slug] = {"book": False}

            # Initialize movies section if it doesn't exist
            if "movies" not in read_watched[slug]:
                read_watched[slug]["movies"] = {}

            # Mark movie as watched if not already set to True
            if (
                year not in read_watched[slug]["movies"]
                or not read_watched[slug]["movies"][year]
            ):
                read_watched[slug]["movies"][year] = True
                changes_made += 1
                print(f"✓ {slug} ({year})")

        if changes_made > 0:
            # Write back to user.yaml
            with open(personal_yaml_path, "w") as f:
                yaml.dump(user_data, f)

            print(f"\nUpdated {changes_made} movies")
        else:
            print("All movies already marked")


@app.command()
def statistics(
    personal_yaml: Annotated[
        Optional[Path],
        typer.Option(
            help="Path to personal YAML file (default: first YAML in personal/)"
        ),
    ] = None,
    output: Annotated[
        Path, typer.Option(help="Output file for Mermaid diagram")
    ] = Path("personal/statistics.mmd"),
):
    """
    Generate a Mermaid diagram with statistics about books read and movies watched.
    """
    # Find first YAML file if not specified
    if personal_yaml is None:
        personal_dir = Path("personal")
        if not personal_dir.exists():
            print(f"❌ Personal directory not found: {personal_dir}")
            raise typer.Exit(code=1)

        yaml_files = sorted(personal_dir.glob("*.yaml"))
        if not yaml_files:
            print(f"❌ No YAML files found in {personal_dir}/")
            raise typer.Exit(code=1)

        personal_yaml = yaml_files[0]
        print(f"Using {personal_yaml}")

    if not personal_yaml.exists():
        print(f"❌ Personal YAML file not found: {personal_yaml}")
        raise typer.Exit(code=1)

    # Read the main books file
    books_file = Path("reading-challenge.yaml")
    if not books_file.exists():
        print(f"❌ Books file not found: {books_file}")
        raise typer.Exit(code=1)

    with open(books_file, "r") as f:
        books_data = yaml.load(f)

    # Read the personal file
    with open(personal_yaml, "r") as f:
        user_data = yaml.load(f)
        read_watched = user_data["read|watched"]

    # Calculate statistics
    total_books = len(books_data["books"])
    books_with_adaptations = sum(
        1 for book in books_data["books"] if "movies" in book and book["movies"]
    )
    total_adaptations = sum(
        len(book["movies"]) for book in books_data["books"] if "movies" in book
    )

    # Create lookup for books with their adaptations
    books_lookup = {book["slug"]: book for book in books_data["books"]}

    # Analyze user progress
    books_read = 0
    books_not_read = 0
    movies_watched_count = 0
    total_available_movies = 0

    # Completion categories
    read_all_movies_watched = 0  # Read book + watched all adaptations
    read_some_movies_watched = 0  # Read book + watched some adaptations
    read_no_movies_watched = 0  # Read book + no movies watched
    not_read_movies_watched = 0  # Not read + watched movies
    neither = 0  # Not read + no movies watched

    for book_slug, book_data in read_watched.items():
        book_entry = books_lookup.get(book_slug)
        if not book_entry:
            continue

        book_read = book_data.get("book", False)
        user_movies = book_data.get("movies", {})
        watched_movies = sum(1 for watched in user_movies.values() if watched)

        # Count available adaptations
        available_adaptations = len(book_entry.get("movies", []))
        total_available_movies += available_adaptations

        if book_read:
            books_read += 1
        else:
            books_not_read += 1

        movies_watched_count += watched_movies

        # Categorize
        if book_read and available_adaptations > 0:
            if watched_movies == available_adaptations:
                read_all_movies_watched += 1
            elif watched_movies > 0:
                read_some_movies_watched += 1
            else:
                read_no_movies_watched += 1
        elif book_read and available_adaptations == 0:
            read_no_movies_watched += 1
        elif not book_read and watched_movies > 0:
            not_read_movies_watched += 1
        else:
            neither += 1

    # Books not in personal yaml are not read
    tracked_slugs = set(read_watched.keys())
    all_slugs = {book["slug"] for book in books_data["books"]}
    untracked_books = len(all_slugs - tracked_slugs)
    neither += untracked_books
    books_not_read += untracked_books

    # Calculate percentages
    books_read_pct = (books_read / total_books * 100) if total_books > 0 else 0
    books_not_read_pct = 100 - books_read_pct
    movies_watched_pct = (
        (movies_watched_count / total_adaptations * 100) if total_adaptations > 0 else 0
    )
    movies_not_watched_pct = 100 - movies_watched_pct

    # Generate Sankey diagram showing flow of reading/watching progress
    mermaid = f"""%%{{init: {{'theme':'base'}}}}%%
sankey-beta

%% Books flow
All Books,Books Read,{books_read}
All Books,Books Not Read,{books_not_read}

%% Books Read breakdown
Books Read,Read + All Movies,{read_all_movies_watched}
Books Read,Read + Some Movies,{read_some_movies_watched}
Books Read,Read Only,{read_no_movies_watched}

%% Books Not Read breakdown
Books Not Read,Movies Only,{not_read_movies_watched}
Books Not Read,Neither,{neither}

%% Movies flow
All Movies,Movies Watched,{movies_watched_count}
All Movies,Movies Not Watched,{total_adaptations - movies_watched_count}
"""

    # Write single file
    with open(output, "w") as f:
        f.write(mermaid)

    # Print summary
    print(f"\n📊 Statistics Summary")
    print(f"{'='*50}")
    print(f"Total Books: {total_books}")
    print(f"Books Read: {books_read} ({books_read_pct:.1f}%)")
    print(f"Books Not Read: {books_not_read} ({books_not_read_pct:.1f}%)")
    print(f"\nTotal Movie Adaptations: {total_adaptations}")
    print(f"Movies Watched: {movies_watched_count} ({movies_watched_pct:.1f}%)")
    print(
        f"Movies Not Watched: {total_adaptations - movies_watched_count} ({movies_not_watched_pct:.1f}%)"
    )
    print(f"\n✅ Completion Breakdown:")
    print(f"  📖🎬 Read + Watched All Movies: {read_all_movies_watched}")
    print(f"  📖🎬 Read + Watched Some Movies: {read_some_movies_watched}")
    print(f"  📖 Read Book Only: {read_no_movies_watched}")
    print(f"  🎬 Watched Movies Only: {not_read_movies_watched}")
    print(f"  ❌ Neither Read Nor Watched: {neither}")
    print(f"\n✅ Mermaid diagram saved to: {output}")
    print(f"\nView online: https://mermaid.live")
    print(
        f"Convert to SVG: mmdc -i {output} -o {output.with_suffix('.svg')} -b transparent"
    )


if __name__ == "__main__":
    app()
