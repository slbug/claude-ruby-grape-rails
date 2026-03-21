# Investigation Output Template

Create `.claude/plans/{slug}/research/investigation.md`:

````markdown
# Bug Investigation: $ARGUMENTS

## Error

```
{exact error message}
```

## Reproduction

```bash
{command to reproduce}
```

## Ralph Wiggum Checklist

- [x] File saved? YES
- [x] Syntax valid? YES (`ruby -c` passes)
- [ ] Correct method name? **NO - FOUND IT**
- [ ] Data exists? Not checked

## Root Cause

**What's wrong**: Calling `params[:user_id]` but form sends `user_id` as string key

**Where**: app/controllers/users_controller.rb:45

**Why missed**: Strong params not permitting the field, so it's filtered out

## Fix

```ruby
# Before
def user_params
  params.require(:user).permit(:name, :email)
  # user_id was missing from permitted params!
end

# After
def user_params
  params.require(:user).permit(:name, :email, :user_id)
end
```

## Prevention

- Add test with external API mock
- Add typespec to catch at compile time
````
