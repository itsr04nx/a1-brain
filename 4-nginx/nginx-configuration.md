# Nginx Reverse Proxy Configuration

## Location: `/home/ubuntu/Workspace/authelia/nginx/default.conf`

### Overview
Nginx reverse proxy with SSL termination and Authelia SSO authentication for all backend services.

### SSL Certificates
- **Certificate**: `/etc/nginx/ssl/authelia.crt`
- **Key**: `/etc/nginx/ssl/authelia.key`
- **Client CA**: `/etc/nginx/ssl/client-ca.crt`
- **Client CA Key**: `/etc/nginx/ssl/client-ca.key`
- **Client Certs Directory**: `/etc/nginx/ssl/client-certs/`

### TLS Configuration
- **Protocols**: `TLSv1.2`, `TLSv1.3`
- **Ciphers**: `HIGH:!aNULL:!MD5`
- **Client Certificate Verification**: `ssl_verify_client optional` (mTLS optional)

### Server Blocks

#### 1. Default HTTP → HTTPS Redirect
```nginx
server {
    listen 80;
    listen [::]:80;
    server_name _;
    return 301 https://$host$request_uri;
}
```

#### 2. Default HTTPS → 404 (Unmatched Hosts)
```nginx
server {
    listen 443 ssl;
    listen [::]:443 ssl;
    server_name _;
    ssl_certificate /etc/nginx/ssl/authelia.crt;
    ssl_certificate_key /etc/nginx/ssl/authelia.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    return 404;
}
```

#### 3. Authelia Authentication Portal
```nginx
server {
    listen 443 ssl;
    listen [::]:443 ssl;
    server_name auth.rohan.run.place;
    
    ssl_certificate /etc/nginx/ssl/authelia.crt;
    ssl_certificate_key /etc/nginx/ssl/authelia.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_client_certificate /etc/nginx/ssl/client-ca.crt;
    ssl_verify_client optional;
    
    proxy_set_header Host $http_host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-Host $http_host;
    proxy_set_header X-Forwarded-Uri $request_uri;
    proxy_set_header X-Forwarded-Ssl on;
    proxy_redirect http:// $scheme://;
    proxy_http_version 1.1;
    
    location / {
        proxy_pass http://authelia:9091;
    }
    
    location /api/verify {
        proxy_pass http://authelia:9091;
    }
    
    location /api/authz/ {
        proxy_pass http://authelia:9091;
    }
}
```

#### 4. OpenHands (Behind SSO / Client Cert)
```nginx
server {
    listen 443 ssl;
    listen [::]:443 ssl;
    server_name openhands.rohan.run.place;
    
    ssl_certificate /etc/nginx/ssl/authelia.crt;
    ssl_certificate_key /etc/nginx/ssl/authelia.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_client_certificate /etc/nginx/ssl/client-ca.crt;
    ssl_verify_client optional;
    
    location /internal/authelia/authz {
        internal;
        if ($ssl_client_verify = SUCCESS) {
            return 200;
        }
        proxy_pass http://authelia:9091/api/authz/auth-request;
        proxy_pass_request_body off;
        proxy_set_header Content-Length "";
        proxy_set_header X-Original-Method $request_method;
        proxy_set_header X-Original-URL $scheme://$http_host$request_uri;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $http_host;
        proxy_set_header X-Forwarded-URI $request_uri;
        proxy_set_header X-Forwarded-For $remote_addr;
    }
    
    location / {
        auth_request /internal/authelia/authz;
        auth_request_set $user $upstream_http_remote_user;
        auth_request_set $groups $upstream_http_remote_groups;
        auth_request_set $name $upstream_http_remote_name;
        auth_request_set $email $upstream_http_remote_email;
        auth_request_set $redirection_url $upstream_http_location;
        error_page 401 =302 $redirection_url;
        
        proxy_pass http://100.72.142.64:3000;
        proxy_set_header Host $http_host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-SSL-Client-Verify $ssl_client_verify;
        proxy_set_header X-SSL-Client-DN $ssl_client_s_dn;
        proxy_set_header Remote-User $user;
        proxy_set_header Remote-Groups $groups;
        proxy_set_header Remote-Name $name;
        proxy_set_header Remote-Email $email;
        
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

#### 5. Mailpit / Webmail (Behind SSO / Client Cert)
- **Mailpit** (`mail.rohan.run.place`): proxies to `mailpit:8025`
- **SnappyMail** (`webmail.rohan.run.place`): proxies to `snappymail:8888`

### Alternative Nginx Config
- **Location**: `/home/ubuntu/Workspace/nginx/default.conf`
- **Purpose**: Simpler config for `auth.rohan.run.place` only
- **Note**: Uses `authelia:9090` (different port than the compose file's `9091`)

---
*Generated on: Sun Nov 01 2026*