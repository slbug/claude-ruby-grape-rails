## Performance Tips

1. **Use `turbo_frame_tag` with `loading: "lazy"`** for below-fold content
2. **Debounce form submissions** with Stimulus to avoid excessive requests
3. **Cache partials** that don't change frequently
4. **Use `turbo_stream_from`** with specific scopes to minimize broadcasts
5. **Limit broadcast frequency** - batch updates when possible
6. **Eager load associations** in turbo stream responses

```ruby
# app/controllers/comments_controller.rb
def create
  @comment = @post.comments.create!(comment_params)
  
  respond_to do |format|
    format.turbo_stream do
      # Eager load user for the partial
      @comment = Comment.includes(:user).find(@comment.id)
      render turbo_stream: turbo_stream.append("comments", @comment)
    end
  end
end
```
