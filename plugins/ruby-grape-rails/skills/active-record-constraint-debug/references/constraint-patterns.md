# Constraint Debugging Patterns

## Unique Constraint Violations

### Pattern 1: Race Condition (Double Submit)

**Symptom**: `ActiveRecord::RecordNotUnique` error on user action, works on retry.

**Root cause**: Two concurrent requests insert the same unique value.

**Fix**: Upsert pattern

```ruby
def create_or_update_link(attrs)
  Link.upsert(
    attrs,
    on_duplicate: :update,
    update_only: [:updated_at],
    unique_by: :url
  )
end
```

### Pattern 2: Shared Data via Nested Attributes

**Symptom**: Inserting parent records that share child associations fails on the second parent.

**Root cause**: `accepts_nested_attributes_for` builds separate INSERT for each parent's children. If two parents reference the same child (e.g., same URL), the second INSERT violates the unique constraint.

**Fix**: Deduplicate before building associations.

Reject the per-contact loop — each call rebuilds child rows that
collide on the unique URL constraint:

```ruby
contacts.each do |contact|
  contact.update(links: extract_links(contact.text))
end
```

Deduplicate links first, batch-insert with conflict skip, then
associate:

```ruby
all_links = contacts.flat_map { |c| extract_links(c.text) }.uniq { |l| l.url }
link_ids  = Link.insert_all(all_links, on_conflict: :nothing, returning: :id).rows.flatten
link_map  = Link.where(id: link_ids).index_by(&:url)

contacts.each do |contact|
  contact_link_ids = extract_links(contact.text).map { |l| link_map[l.url]&.id }.compact
  contact.update(link_ids: contact_link_ids)
end
```

### Pattern 3: Bulk Insert with Duplicates

**Symptom**: `insert_all` fails when input data has duplicate values for a unique column.

**Fix**: Deduplicate input or push the conflict resolution to the DB.

Pre-dedup in Ruby:

```ruby
unique_records = records.uniq { |r| r[:email] }
```

Or skip conflicts at insert time:

```ruby
User.insert_all(records, on_conflict: :nothing, unique_by: :email)
```

## Foreign Key Violations

### Pattern 1: Orphaned Reference

**Symptom**: Insert/update fails because referenced record doesn't exist.

**Root cause**: Parent record was deleted between validation and insert, or ID was passed incorrectly.

**Fix**: Check existence in transaction

```ruby
ActiveRecord::Base.transaction do
  parent = Parent.find_by(id: parent_id)
  if parent.nil?
    raise ActiveRecord::Rollback, :parent_not_found
  end
  
  Child.create!(parent_id: parent.id, **attrs)
end
```

### Pattern 2: Cascade Delete Surprise

**Symptom**: Deleting a parent silently deletes children (or fails if no cascade).

**Check migration**: confirm `on_delete` semantics.

| `on_delete:` | DB action |
|---|---|
| `:cascade` | Delete children with parent |
| `:restrict` | Block parent delete while children exist |
| `:nullify` | Set child FK to NULL |
| `:nothing` | Defer to DB default |

```ruby
add_reference :children, :parent, foreign_key: { on_delete: :cascade }
add_reference :children, :parent, foreign_key: { on_delete: :restrict }
add_reference :children, :parent, foreign_key: { on_delete: :nullify }
add_reference :children, :parent, foreign_key: { on_delete: :nothing }
```

## Check Constraint Violations

### Pattern 1: Enum Mismatch

**Symptom**: Insert fails on check constraint for an enum field.

**Root cause**: Value not in the allowed list defined in migration.

**Debug**: confirm model enum values match the migration check
constraint exactly. The two declarations are independent — drift
between them is the usual root cause.

Model:

```ruby
enum status: { draft: 'draft', active: 'active', archived: 'archived' }
```

Migration:

```ruby
add_check_constraint :items, "status IN ('draft', 'active', 'archived')", name: 'status_must_be_valid'
```

### Pattern 2: Range Violation

**Symptom**: Value fails a range check constraint.

**Debug**: Read the constraint definition in migration

```bash
grep -r "add_check_constraint\|add_index.*unique" db/migrate/
```

## Debugging Techniques

### Inspect the validation error

```ruby
begin
  Entity.create!(**attrs)
rescue ActiveRecord::RecordNotUnique => e
  logger.info "Entity already exists: #{e.message}"
  :already_exists
rescue ActiveRecord::RecordInvalid => e
  logger.error "Validation failed: #{e.record.errors.full_messages.join(', ')}"
  raise
end
```

### Find the colliding row

```ruby
Entity.where(unique_field: value).to_a
```

### Trace with runtime tooling (when available)

```
mcp__tidewave__execute_sql_query "SELECT * FROM table WHERE unique_col = 'value'"
mcp__tidewave__project_eval "Entity.where(field: value).to_a"
```

## Prevention Patterns

### Always handle constraint errors at the boundary

```ruby
def create_entity(attrs)
  Entity.create!(attrs)
rescue ActiveRecord::RecordNotUnique
  :already_exists
rescue ActiveRecord::RecordInvalid => e
  { error: e.record.errors.full_messages }
end
```

### Upsert for idempotency

```ruby
def upsert_entity(attrs)
  Entity.upsert(
    attrs,
    on_conflict: :update,
    conflict_target: :external_id,
    returning: true
  )
end
```

### Layer model validation with DB constraint

Validation gives fast feedback; the DB constraint guarantees the
invariant under concurrent writes.

```ruby
class Entity < ApplicationRecord
  validates :email, presence: true
  validates :email, uniqueness: true
end
```
