# Encrypted secrets

This repository is **public**. Every credential lives in a single
`age`-encrypted tarball:

```
Infra/secrets/homelab-secrets.tar.gz.age
```

The age **private** key is not in the repo and must never be committed.

| Item | Location |
|---|---|
| age public key (safe to publish) | `Infra/secrets/age.pub` |
| age private key (canonical) | OCI Object Storage — bucket `a1-brain-secrets`, object `age.key` |
| age private key (runtime copy) | `~/.config/a1-brain/age.key` on `a1-agent`, mode `600` |

A public key can encrypt but not decrypt, so committing `age.pub` is safe.
The bucket is `NoPublicAccess` and versioned; the object is encrypted at
rest by OCI.

## Restore the private key

Run from WSL, where the OCI CLI is configured:

```bash
oci os object get \
  --namespace bmlkffhaqbbq \
  --bucket-name a1-brain-secrets \
  --name age.key \
  --file ~/.config/a1-brain/age.key
chmod 600 ~/.config/a1-brain/age.key
```

Then copy it to the host if you are rebuilding:

```bash
scp ~/.config/a1-brain/age.key a1:~/.config/a1-brain/age.key
```

## Use

```bash
# list what is inside
Infra/scripts/secrets.sh list

# decrypt into a directory
Infra/scripts/secrets.sh extract /tmp/homelab-secrets

# rebuild the bundle from the live configs on a1-agent
Infra/scripts/backup.sh
```

`backup.sh` takes consistent SQLite snapshots of `authelia.db` and
`lldap/users.db`, then calls `secrets.sh build`. Nothing is ever written to
the repository in plaintext.

## What is inside

- Authelia `configuration.yml`, `users.yml`, `authelia.db`, OIDC keys
- LLDAP config and `users.db`
- Docker-Mailserver account/masters files
- SnappyMail domain configs
- **all** nginx TLS private keys and client certificates
- nginx `default.conf`
- browser `.env` (gateway `ADMIN_TOKEN`) and compose file
- AdGuard Home config
- Paperclip config

## Rules

1. Never commit a plaintext `.key`, `.pem`, `.p12`, `.db`, `.sql` or `.env`.
   `.gitignore` blocks them; do not bypass it.
2. Rotate a credential by editing the live config, then re-running
   `backup.sh`. The new value is encrypted into the bundle.
3. The bundle is only as strong as the private key. Treat
   `~/.config/a1-brain/age.key` and the OCI object as the crown jewels.
4. Encryption protects *new* values. Any secret that was ever committed in
   plaintext must be rotated, because the old value is already public.
