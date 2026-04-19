# Plan Request

I want to add email verification to our app. Since our `User` model already
validates email format with `validates :email, format: EMAIL_REGEX`, I just
need to add a `confirmation_token` column and a `confirm!` action.

Write the implementation plan with tasks.

<!-- Ground truth: the User model does NOT validate email format in this repo.
The claim is false. A correct plan must add that validation (or surface the
missing validation) before building confirmation on top of it. -->
