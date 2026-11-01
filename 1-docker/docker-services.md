# Docker Compose Services

## Location: `/home/ubuntu/Workspace/authelia/docker-compose.yml`

### Service: `authelia`
- **Image**: `authelia/authelia:latest`
- **Container Name**: `authelia`
- **Restart Policy**: `unless-stopped`
- **Exposed Port**: `9091`
- **Environment Variables**:
  - `DATABASE_TYPE=sqlite3`
  - `SQLITE3_DATABASE=/config/authelia.db`
  - `JWT_SECRET` (random - needs rotation)
  - `COOKIE_SAME_SITE=lax`
  - `LOG_LEVEL=info`
- **Volumes**: `./config:/config`, `./data:/data`
- **Dependencies**: `redis`

### Service: `redis`
- **Image**: `redis:7-alpine`
- **Container Name**: `authelia-redis`
- **Restart Policy**: `unless-stopped`
- **Command**: `["--save", "", "--appendonly", "no"]`
- **Purpose**: Redis cache/database for Authelia
- **Exposed Port**: `6379/tcp`

### Service: `mailpit`
- **Image**: `axllent/mailpit:latest`
- **Container Name**: `mailpit`
- **Restart Policy**: `unless-stopped`
- **Environment Variables**:
  - `MP_DATA_FILE=/data/mailpit.db`
  - `MP_SMTP_BIND_ADDR=0.0.0.0:1025`
  - `MP_UI_BIND_ADDR=0.0.0.0:8025`
  - `MP_MAX_MESSAGES=5000`
- **Volumes**: `./data/mailpit:/data`
- **Purpose**: Email testing and debugging
- **Exposed Ports**: `1025/tcp` (SMTP), `8025/tcp` (UI), `1110/tcp` (metrics)

### Service: `snappymail`
- **Image**: `djmaze/snappymail:latest`
- **Container Name**: `snappymail`
- **Restart Policy**: `unless-stopped`
- **Exposed Port**: `8888`
- **Volumes**: `./data/snappymail:/snappymail/data`
- **Dependencies**: `mailpit`
- **Purpose**: Webmail client with interactive compose

### Service: `nginx` (authelia-nginx)
- **Image**: `nginx:alpine`
- **Container Name**: `authelia-nginx`
- **Restart Policy**: `unless-stopped`
- **Ports**: `80:80`, `443:443`
- **Volumes**: 
  - `./nginx/default.conf:/etc/nginx/conf.d/default.conf:ro`
  - `./nginx/ssl:/etc/nginx/ssl:ro`
- **Dependencies**: `authelia`, `mailpit`, `snappymail`
- **Purpose**: Reverse proxy with SSL termination and Authelia SSO

## Startup Script
- **Location**: `/home/ubuntu/Workspace/authelia/start.sh`
- **Command**: `docker compose up -d`
- **Wait**: 3 seconds then `docker compose ps`
- **URLs provided**: 
  - Web Portal: `https://auth.rohan.run.place`
  - Health check: `https://auth.rohan.run.place/api/health`
  - Default users: `admin`, `user`