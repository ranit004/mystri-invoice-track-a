# ClearLedger Security Policy & Architecture Boundaries

## Local Demo Scope
ClearLedger is currently configured for local-only assessment and demo execution. The built-in HTTP server binds exclusively to loopback address `127.0.0.1`.

> [!WARNING]
> Do not bind or expose this development application to external network interfaces without implementing production security controls.

## Production Network Deployment Requirements
For network or enterprise deployment, the following controls are mandatory:
1. **Transport Security:** Enforce HTTPS with TLS 1.3 encryption.
2. **Authentication & Authorization:** Implement multi-tenant authentication (e.g., OAuth2 / OIDC) and role-based access control (RBAC).
3. **Session & Token Management:** Secure, HTTP-only, SameSite cookies with CSRF token validation on all state-mutating requests.
4. **Rate Limiting & DoS Mitigation:** Web Application Firewall (WAF) and request rate limiting per client IP / user identity.
5. **Database Isolation & Scaling:** Production PostgreSQL with encrypted connections, least-privilege user credentials, and regular database backups.

## File Permissions & Windows Limitations
- **POSIX Environments (Linux / macOS):** File permissions are enforced via standard POSIX `chmod` (`0700` for `.local/` directory and `0600` for `clearledger.sqlite3`).
- **Windows Environments:** POSIX `chmod` is not supported on Windows NTFS/FAT filesystems and cannot enforce per-user access control lists (ACLs). On Windows, ClearLedger attempts a best-effort restrictive ACL application using the standard Windows utility `icacls <path> /grant:r "%USERNAME%:F"`.
- **Limitation Note:** Any failure during `icacls` execution is handled gracefully without blocking application startup or failing local demo execution. Windows per-user file isolation is best-effort and is not guaranteed across all Windows domain setups or permissions configurations.

## TypeSafe AI Integration Boundary
TypeSafe AI primitives must adhere strictly to the following security boundaries:
- **No Direct Financial Mutation:** TypeSafe AI models are strictly prohibited from performing financial calculations, payment matching, identity creation, or database writes. Financial arithmetic remains 100% deterministic Python code.
- **Server-Side API Credentials:** API keys must remain strictly in server-side environment variables and must never be exposed to browser clients.
- **Data Minimization:** Only minimal, non-financial text context (e.g. support notes or anomaly descriptions) may be passed to model primitives.
- **Advisory Output Only:** Model judgments are advisory; low-confidence results require human operator review.
