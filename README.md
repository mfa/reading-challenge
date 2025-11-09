# Reading Challenge

Reading Challenge tracker very roughly based on the Rory Gilmore Reading Challenge.

The personal folder is ignored in this repository.
I (@mfa) store the personal folder in a second private repository.

## Usage

```bash
# Validate slugs and movie references
uv run main.py check

# Update watched movies from IMDb CSV export
uv run main.py update-movies

# Generate statistics visualization
uv run main.py statistics
```

### Commands

#### `check`

Validates that all slugs in your personal YAML file exist in `reading-challenge.yaml` and that all movie years reference actual movies.

Options:
- `--personal-yaml`: Path to personal YAML file (default: first YAML file found in `personal/`)

Example:
```bash
uv run main.py check --personal-yaml personal/myname.yaml
```

#### `update-movies`

Updates watched movies in your personal YAML file based on a CSV export from IMDb. The CSV should contain a `Const` column with IMDb title keys (tt numbers).

Options:
- `--personal-dir`: Path to personal directory containing CSV and YAML files (default: `personal`)
- `--personal-yaml`: Name of personal YAML file relative to personal-dir (default: first YAML file found in personal-dir)

Example:
```bash
uv run main.py update-movies --personal-dir personal --personal-yaml myname.yaml
```

#### `statistics`

Generates a Mermaid diagram visualizing your reading and watching progress. The visualization includes:
- Overall progress (books read vs not read, movies watched vs not watched)
- Completion breakdown (read + all movies watched, read + some movies, read only, watched movies only, neither)
- Challenge overview (total books, books with adaptations, total adaptations)

Options:
- `--personal-yaml`: Path to personal YAML file (default: first YAML file found in `personal/`)
- `--output`: Output file for the Mermaid diagram (default: `personal/statistics.mmd`)

Example:
```bash
uv run main.py statistics --output personal/my-stats.mmd
```

The generated `.mmd` file can be viewed at [mermaid.live](https://mermaid.live) or integrated into Markdown documents that support Mermaid diagrams.


## Personal Folder

The `personal/` folder contains user-specific tracking data:

- **CSV file**: Export of your watched movies from IMDb (must contain a `Const` column with IMDb tt keys)
- **YAML file**: Your personal reading and movie watching progress

### Personal YAML Structure

The personal YAML file tracks which books you've read and which movie adaptations you've watched:

```yaml
read|watched:
  book-slug-from-reading-challenge:
    book: true  # Have you read the book?
    movies:
      1999: true  # Have you watched the 1999 adaptation?
      2005: false
```

The `update-movies` command automatically populates the `movies` section by matching your IMDb watchlist against the movie adaptations listed in `reading-challenge.yaml`.
