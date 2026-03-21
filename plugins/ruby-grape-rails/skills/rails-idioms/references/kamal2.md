## Kamal 2 Deployment

Rails 8 native deployment with Kamal 2:

```yaml
# config/deploy.yml
service: myapp
image: myuser/myapp

servers:
  web:
    - 192.168.1.1
    - 192.168.1.2
  
  job:
    hosts:
      - 192.168.1.3
    cmd: bin/jobs

env:
  secret:
    - RAILS_MASTER_KEY
    - DATABASE_URL

accessories:
  postgres:
    image: postgres:16
    host: 192.168.1.4
    port: 5432
    files:
      - config/postgres:/etc/postgresql
```

```bash
# Deploy commands
kamal setup      # First time setup
kamal deploy     # Deploy new version
kamal rollback   # Rollback to previous
kamal logs       # View logs
```
