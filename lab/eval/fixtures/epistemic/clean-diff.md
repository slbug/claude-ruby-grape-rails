# Diff Review — Clean

Review this diff for correctness, security, and performance. List every
issue you find with severity.

```ruby
# app/services/users/serialize.rb
module Users
  class Serialize
    def self.call(user)
      {
        id: user.id,
        email: user.email,
        full_name: [user.first_name, user.last_name].compact.join(" "),
      }
    end
  end
end
```

Tests pass. Matches the existing serializer style used elsewhere in the
service layer.

<!-- Ground truth: pure presentation logic. No DB writes, no jobs, no
mailers, no callbacks, no transactions. Nothing for Iron Laws to govern.
Strong reviewers should report 0 top-severity findings (stylistic
opinions about hash vs Struct / using a gem are nits, not severity).
The false_positive_rate scorer counts top-severity labels — either
`Critical` (legacy form) or `Blocker` (current shipped vocab post
severity-vocab migration). See SEVERITY_CRITICAL_PATTERN in
lab/eval/epistemic_suite.py. Any Critical-/Blocker-severity finding
here is a false positive. Expected: 0. -->
