# PostgreSQL Full-Text Search with Active Record

Native full-text search without external dependencies. Based on
[Search is Not Magic with PostgreSQL](https://www.codecon.sk/search-is-not-magic-with-postgresql).

## Strategy Decision Tree

| Need | Strategy | Extension |
|------|----------|-----------|
| Exact/weighted text search | Full-text search (tsvector) | Built-in |
| Typo tolerance / fuzzy | Trigram similarity (pg_trgm) | `pg_trgm` |
| Semantic / AI search | Vector search (pgvector) | `pgvector` |
| All of the above | Hybrid with RRF | Multiple |

## 1. Full-Text Search (tsvector/tsquery)

### Migration — Generated Column (Preferred, PostgreSQL 12+)

```ruby
class AddSearchableToArticles < ActiveRecord::Migration[7.1]
  def up
    execute <<-SQL
      ALTER TABLE articles
      ADD COLUMN searchable tsvector
      GENERATED ALWAYS AS (
        setweight(to_tsvector('english', coalesce(title, '')), 'A') ||
        setweight(to_tsvector('english', coalesce(body, '')), 'B')
      ) STORED
    SQL

    add_index :articles, :searchable, using: :gin
  end

  def down
    remove_column :articles, :searchable
  end
end
```

Generated columns auto-update on INSERT/UPDATE — no triggers needed.

**When to use triggers instead**: When the tsvector depends on associated
records (e.g., tags from a join table). Generated columns can only reference
columns in the same row.

### Basic Search Query

```ruby
class Article < ApplicationRecord
  scope :search, ->(query) {
    where("searchable @@ websearch_to_tsquery('english', ?)", query)
      .select("*, ts_rank_cd(searchable, websearch_to_tsquery('english', ?), 32) as rank", query)
      .order("rank DESC")
  }
end

# Usage
Article.search("ruby rails")
```

### Search with Highlights and Pagination

```ruby
class Article < ApplicationRecord
  def self.search_with_highlights(query_string, page: 1, per_page: 20)
    offset = (page - 1) * per_page
    
    select(:id, :title)
      .select("ts_headline('english', body, websearch_to_tsquery('english', ?), 
              'StartSel=<mark>, StopSel=</mark>') as headline", query_string)
      .select("ts_rank_cd(searchable, websearch_to_tsquery('english', ?), 32) as rank", query_string)
      .where("searchable @@ websearch_to_tsquery('english', ?)", query_string)
      .order("rank DESC")
      .offset(offset)
      .limit(per_page)
  end
end
```

### Multi-Language Support

```ruby
# Dynamic language
class Article < ApplicationRecord
  def self.search(query, language: 'english')
    where("to_tsvector(?::regconfig, body) @@ to_tsquery(?::regconfig, ?)", 
          language, language, query)
  end
end
```

### websearch_to_tsquery Syntax (Google-style)

| Input | Matches |
|-------|---------|
| `ruby rails` | Both words |
| `"exact phrase"` | Exact phrase |
| `ruby OR rails` | Either word |
| `-deprecated` | Excludes word |

### Weight Meanings

| Weight | Use | Boost |
|--------|-----|-------|
| A | Title | Highest |
| B | Subtitles | High |
| C | Body | Medium |
| D | Metadata | Lower |

## 2. Trigram Similarity (pg_trgm) — Fuzzy/Typo Tolerance

```ruby
# Migration
class EnablePgTrgm < ActiveRecord::Migration[7.1]
  def change
    enable_extension 'pg_trgm'
    
    add_index :products, :name, opclass: :gin_trgm_ops, using: :gin
  end
end

# Query
class Product < ApplicationRecord
  scope :fuzzy_search, ->(term) {
    where("similarity(name, ?) > ?", term, 0.3)
      .order(Arel.sql("similarity(name, '#{connection.quote_string(term)}') DESC"))
  }
end
```

Trigrams compare 3-character groups — handles typos, misspellings, partial matches.
Threshold 0.3 is a good default; tune based on your data.

## 3. Hybrid Search with RRF (Reciprocal Rank Fusion)

Combine multiple search strategies by normalizing ranks:

```ruby
class Article < ApplicationRecord
  def self.hybrid_search(term)
    # Each strategy returns records with rank
    similarity_results = fuzzy_search_ranked(term)
    fulltext_results = fulltext_search_ranked(term)
    
    # Merge with deduplication
    all_results = (similarity_results + fulltext_results)
      .group_by(&:id)
      .transform_values { |records| records.sum(&:rank) }
      .sort_by { |_, rank| -rank }
      .first(20)
    
    # Load actual records
    where(id: all_results.map(&:id))
  end
end
```

### Multi-Word Query Normalization

```ruby
def self.normalize_query(text)
  text
    .strip
    .downcase
    .gsub(/\s+/, ' ')
    .split(' ')
    .join(' &')
end
```

## Performance

```ruby
# ALWAYS use GIN index for tsvector
add_index :articles, :searchable, using: :gin

# Partial index for large tables
add_index :articles, :searchable, using: :gin, where: "published_at IS NOT NULL"

# GIN indexes only used with LIMIT — always paginate
```

## Anti-patterns

```ruby
# WRONG: Computing tsvector at query time (slow, no index!)
Article.where("to_tsvector('english', title || ' ' || body) @@ to_tsquery(?)", q)

# WRONG: Using LIKE for search (no ranking, no stemming)
Article.where("title ILIKE ?", "%#{query}%")

# WRONG: Using triggers when generated columns suffice
# Generated columns are simpler and auto-maintained

# WRONG: Assuming PG can't do fuzzy search
# pg_trgm handles typo tolerance natively — no need for Elasticsearch just for fuzzy
```

## When to Use External Search

PostgreSQL handles most use cases (100K-10M docs). Consider Meilisearch/Elasticsearch for:

- Faceted search with complex filters across many dimensions
- Multi-language with mixed alphabets in same field
- Real-time indexing of 10M+ documents
- Advanced search analytics

**Further reading**: [Search is Not Magic with PostgreSQL](https://www.codecon.sk/search-is-not-magic-with-postgresql)
— covers trigrams, full-text, vector search, and hybrid patterns with Active Record examples.
