## Rails 8 Checklist

When upgrading or creating a new Rails 8 app:

- [ ] Use Propshaft instead of Sprockets (new apps)
- [ ] Evaluate Solid Queue vs Sidekiq
- [ ] Evaluate Solid Cache vs Redis
- [ ] Evaluate Solid Cable vs Redis
- [ ] Use built-in authentication generator for new apps
- [ ] Enable YJIT (Rails 7.2+ enables by default on Ruby 3.3+)
- [ ] Configure Thruster for production
- [ ] Set up Kamal 2 for deployment
- [ ] Use async queries where beneficial
- [ ] Review callback usage - prefer explicit service objects
- [ ] Set up `config/ci.rb` for local CI
