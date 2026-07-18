# Week 3 Lab — Part 2: Signed Sessions and Certificate Trust

**Lecture:** Introduction to Cryptography; Public Key Cryptography and PKI

---

## Overview

Part 1 fixed two things: how passwords are stored (bcrypt hashing) and how traffic is protected while it travels across the network (HTTPS with a self-signed certificate). Two gaps still remain, and each one teaches you a different cryptographic tool than bcrypt.

**Gap 1 — the server doesn't verify who it's talking to after login.** Right now it trusts three plaintext cookies (`authenticated`, `role`, `user_id`) and never checks whether they've been edited. You'll fix this with **HMAC signing** (Hash-based Message Authentication Code) — a technique for attaching a tamper-evident "seal" to data using a secret key that only the server knows. Anyone can still read the data underneath; signing does not hide it. But only someone holding the secret key can produce a seal that matches the data, so if an attacker changes even one character, the seal no longer matches and the server rejects it. This is a different job than bcrypt: bcrypt *hides* a password so it never has to be stored in the clear; HMAC signing doesn't hide anything, it *proves data hasn't changed* since the server produced it. You'll use Flask's built-in `session` object, which applies HMAC signing to fix both cookie tampering and a related bug called session fixation — one code change fixes both.

**Gap 2 — your certificate from Part 1 still triggers a browser warning.** It encrypts traffic correctly, but nothing on your machine has told it to trust a certificate signed by *you* instead of a recognized Certificate Authority (CA). You'll fix that by adding the certificate directly to your machine's trust store, and see exactly what "trust" means at the protocol level in the process.

---

## Tools

| Tool | Purpose |
|------|---------|
| Browser Developer Tools | Inspect and manually modify cookies |
| Flask `session` | Stores login state in a cookie that's signed instead of plaintext |
| itsdangerous | The Python library Flask's `session` uses under the hood to create and check the HMAC signature — you won't call it directly, but it's what actually does the signing |
| Keychain Access / `certmgr.msc` / `update-ca-certificates` | Add your self-signed certificate to the OS trust store |
| Terminal | Run commands, rebuild containers |

### Platform Notes

**Certificate trust tools:**
- **macOS:** Keychain Access is pre-installed (Applications → Utilities, or Spotlight search).
- **Windows:** `certmgr.msc` is pre-installed. Open it via Start → type `certmgr.msc` → Enter.
- **Linux:** `update-ca-certificates` ships with the `ca-certificates` package on Debian/Ubuntu (`sudo apt install ca-certificates` if missing).

**Docker commands** work identically across all platforms in Terminal (macOS/Linux) or Git Bash / PowerShell (Windows).

---

## Steps

### 1. Cookie Tampering, Revisited

**Why this is a different attack than Week 2, even though the mechanic looks the same:**
In Week 2 you intercepted *someone else's* valid session cookie over the network and replayed it in your own browser — the trust flaw was that the cookie alone was proof of identity, with no additional check. Today you're not stealing anything: you're logged in as yourself, with your own legitimately-issued cookies, and you're simply editing the values. The server still has no way to tell the difference between a cookie it issued and one you hand-edited, because it was never cryptographically signed in the first place. Same root cause, different exploit path — and it's the reason session data can't just live in a plaintext cookie no matter how it was obtained.

Log in as `jsmith`. Open Developer Tools → **Application → Cookies** and record the `role` and `user_id` cookie values.

Now edit both:
- Change `role` from `student` to `admin`, reload, and navigate to `/admin/users`.
- Look up another student's `user_id` from the grades page (`/grades?student_id=X`), set your `user_id` cookie to that value, reload, and navigate to `/grades`.

Document what you can now access in each case, and what server-side check (if any) was performed before granting it.

---

### 2. Test for Session Fixation

**What session fixation is and what it enables:**
Session fixation is an attack where the attacker forces a known session token onto the victim before the victim authenticates, then waits for the victim to log in. If the server does not generate a new session token upon successful authentication, the attacker's pre-known token becomes a valid authenticated session — the attacker never needed to steal anything, they established the token before authentication ever occurred. The fix is simple: force a new token to be issued the moment credentials are verified.

Record your session-related cookie values **before** logging in (they may already be set on the login page itself). Log in. Record the same cookie values **after** login.

Did the token change? If the same token is valid both before and after authentication, the application is vulnerable to session fixation. Document what you find.

---

### 3. Remediation — Cryptographically Signed Sessions

**What Flask's session mechanism does and why signing prevents forgery:**
Flask's `session` object is a dictionary backed by a cryptographically signed cookie. When you write to `session['role'] = 'student'`, Flask serializes the dictionary to JSON, then signs it using HMAC-SHA256 (via the `itsdangerous` library) with the application's `secret_key`. The resulting cookie looks like a long opaque string rather than readable text. When a request arrives, Flask recomputes the signature and compares it before reading the session data — if anything in the cookie was modified, the signature check fails and the session is rejected outright. An attacker who changes `role` in the cookie now also invalidates the signature, which the server detects and refuses. This is the same principle as the password hashes from Part 1 — a value that proves its own integrity — applied to session state instead of a password. `secrets.token_hex(32)` generates 32 bytes (256 bits) of cryptographically random data, sufficient that no attacker can guess or brute-force the key.

Replace the plaintext cookies with Flask's signed session mechanism. In `__init__.py`, set a strong secret key:

```python
import secrets
app.secret_key = secrets.token_hex(32)
```

In `auth.py`, replace `resp.set_cookie(...)` with `session[...]` assignments on login, and replace the three `resp.delete_cookie(...)` calls in the logout route with `session.clear()`:

```python
from flask import session

# login route — after verifying credentials:
session['authenticated'] = username
session['role'] = user['role']
session['user_id'] = user['user_id']
return redirect(url_for('home'))

# logout route:
session.clear()
return redirect(url_for('auth.login'))
```

Update every route that reads from `request.cookies.get(...)` to read from `session.get(...)` instead. That means `grades.py`, `enrollment.py`, `messages.py`, `documents.py`, `admin.py`, `chatbot.py`, and the home route in `__init__.py` — if any file still reads from cookies, those pages will redirect to login since identity is no longer stored there.

Also update `templates/base.html`, which reads cookies directly in Jinja to decide what links to show:

```html
{% if session.get('authenticated') %}
  Welcome, {{ session.get('authenticated') }} ({{ session.get('role', 'student') }})
  ...
  {% if session.get('role') in ['admin'] %}
```

Flask's `session` object is available in all Jinja templates automatically — no extra wiring needed. If you skip this step the navbar will be blank even though the routes themselves work.

Rebuild and verify the session cookie is now an opaque signed value rather than readable text.

---

### 4. Remediation — Session Rotation on Login

**Why clearing the session before writing to it prevents fixation:**
`session.clear()` discards the current session and causes Flask to issue a new session ID on the next response. This must happen *after* credentials are verified but *before* writing any authenticated data to the session. The sequence matters: verify credentials → clear old session → write new session data. If an attacker established a session token before authentication, that token is now orphaned — it points to a cleared session with no authenticated data, and the attacker would need to somehow intercept the *new* token instead, a much harder problem.

Add this line in the login route immediately before writing to the session:

```python
session.clear()
```

Log the session token value before and after login and confirm they differ.

---

### 5. Verify the Remediations

Repeat Steps 1–2 against the hardened application. For each:
- Document what happens now
- Confirm the attack no longer succeeds
- Paste the HTTP response or browser cookie value showing the signed, opaque session

---

### 6. Trust the Self-Signed Certificate

**What a browser trust warning is actually telling you, and what you're about to change:**
When your browser warned you about `nginx/cert.pem` in Part 1, it wasn't saying the connection is unencrypted — it was saying it can't verify *who* signed the certificate. Normally, a certificate is signed by a Certificate Authority (CA) whose own certificate is already baked into your OS or browser as a trusted root. Your browser walks the chain from the site's certificate up to that trusted root and, if it gets there, shows the padlock with no warning. Your certificate is signed by itself — there is no chain to walk, and nothing on your machine currently vouches for it. Importing the certificate into your OS's trust store adds it directly as a trusted root, which lets your machine (and only your machine) verify that chain locally, without a CA in the middle.

**macOS:**
1. Open **Keychain Access** (Applications → Utilities).
2. Select the **System** keychain in the left sidebar.
3. Drag `nginx/cert.pem` into the window, or use **File → Import Items**.
4. Double-click the newly added certificate, expand **Trust**, and set **When using this certificate** to **Always Trust**.
5. Close the panel and enter your password to confirm.

**Windows:**
1. Open `certmgr.msc`.
2. In the left tree, navigate to **Trusted Root Certification Authorities → Certificates**.
3. Right-click → **All Tasks → Import...**, and select `nginx\cert.pem`.
4. Complete the wizard, accepting the default store location (Trusted Root Certification Authorities).

**Linux:**
```bash
sudo cp nginx/cert.pem /usr/local/share/ca-certificates/huskyhub.crt
sudo update-ca-certificates
```

> **Firefox note:** Firefox maintains its own certificate store (NSS) separate from the operating system's — trusting the certificate in Keychain Access, `certmgr.msc`, or `update-ca-certificates` will **not** clear the warning in Firefox. Go to `about:preferences#privacy` → **Certificates → View Certificates → Authorities → Import**, and select `nginx/cert.pem`. Chrome, Edge, and Safari all use the OS trust store directly.

---

### 7. Verify Trust

Fully quit and reopen your browser, then navigate to `https://localhost`.

Confirm the padlock now shows with no warning. Click the padlock and view the certificate details — note that the issuer and subject are identical (your own `CN=localhost`), which is the visible fingerprint of a self-signed certificate even once it's trusted.

---

## Write-Up Questions

**Q1.** Describe the session fixation attack in your own words. What precondition must an attacker satisfy before the victim logs in, and what does session rotation prevent?

**Q2.** In Part 1 you created a self-signed certificate instead of a CA-signed one. Now that your browser shows no warning for `https://localhost`, has the actual gap you identified back then been closed, or only hidden on this one machine? To check your answer: would a classmate visiting your version of HuskyHub on their own, untouched laptop see the same warning-free padlock? Explain why or why not.

---

## Hacker Mindset Prompt

Trust, once granted, is rarely re-examined. Your browser will silently accept any certificate in its trust store on every future connection, without asking you again — and most users click through "always trust" without ever reading what they just authorized.

Reflect on:

- **Contrarian:** You imported a self-signed certificate into your trust store in under a minute. What stops an attacker with brief physical or remote access to a victim's machine from doing the same with a certificate *they* control? What would that let them do to the victim afterward?
- **Creative:** A signed session cookie is readable but tamper-proof — fine for a `role` value, but not for something genuinely sensitive. What are potential pieces of data that a cookie could store where readable, signed session cookies would not be adaquate enough? 
