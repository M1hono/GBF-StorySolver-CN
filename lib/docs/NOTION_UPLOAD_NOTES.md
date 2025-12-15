# GBF Notion Publishing Specification

## Scope
This document specifies how to publish `{character}_content/**/trans` to Notion with stable structure and deterministic sync behavior.

Canonical references:
- Workflow specification: `lib/EXTRACTION_WORKFLOW.md`
- Tool library reference: `lib/API_REFERENCE.md`
- Notion API reference and examples: `NOTION_API_PLAYBOOK.md`

## Environment constraints
- Assume dependencies already exist on this machine.
- Do not run or suggest package installation commands.

## Terminology
- Page: a Notion page (also used as a “folder” container).
- Database: a container which exposes one or more data sources.
- Data source: owns the schema (`properties`) and is the parent for rows.
- Row: a page stored inside a data source.

## Access requirements
- The integration must be shared into the target parent page.
- Authentication is provided via environment variable `NOTION_API_KEY`.

## API semantics
Use Notion API version `2025-09-03`.

### Database creation
- Required: `databases.create(initial_data_source={ properties: ... })`
- Output: `database.id` and `database.data_sources[0].id`

### Row creation
- Required: `pages.create(parent={ data_source_id: ... }, properties={...})`
- Properties must include explicit `type` where possible.

## Rendering constraints
- Database cells do not render large images or audio players.
- Media must be rendered in the row page body:
  - Cast: set row icon + append an image block
  - Voice: append an audio block (plus a fallback blue link)

## GBF asset URL policy

### Images
- Preferred stable URL: `https://gbf.wiki/Special:FilePath/<filename>`
- If using thumbnail URLs, size can be adjusted (e.g. `110px` → `200px`), but `Special:FilePath` is preferred for Notion icons/files.

### Audio
- `https://gbf.wiki/images/*.mp3` is typically playable via Notion audio blocks.

## Publishing contract

### Source scope
- Publish only `trans/` content.

### Folder purity
- Folder pages must contain no body content. They may contain only `child_page` or `child_database` blocks.

### Page mapping
- Each local Markdown file maps to exactly one Notion page.

### Table mapping
- `cast.md` and voice tables should be published as databases (index) plus row-page body blocks (media).

## Sync semantics

### Modes
- `diff`: default; update only when content differs.
- `force`: always rewrite.

### Equality definition (leaf pages)
1. Fetch page blocks.
2. Extract all plain text from all `rich_text` objects across blocks.
3. Normalize: `\r\n` → `\n`, trim trailing whitespace, collapse 3+ blank lines into 2.
4. Compare normalized text with the local desired normalized text.

### Equality definition (database rows)
1. Batch query a data source once to build a title→row snapshot map.
2. Compute a deterministic text snapshot from properties (title + rich_text + url values).
3. Compare snapshots to decide update (unless `force`).

## Endpoint sequence (typical)
1. `blocks.children.list` (resolve/create folder pages and find child databases)
2. `pages.create` (folder pages)
3. `databases.create` (inline databases via `initial_data_source`)
4. `data_sources.retrieve` (schema mapping)
5. `data_sources.query` (batch row lookup)
6. `pages.create` / `pages.update` (rows and properties)
7. `blocks.children.append` (row-page media blocks)

## Errors
- Missing columns: database schema was not created via `initial_data_source`.
- “Property does not exist”: schema mismatch; retrieve schema and map property names.
- Media not visible in database view: expected; embed media in row page body.