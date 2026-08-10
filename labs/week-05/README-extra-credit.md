# Extra Credit Lab — Brute Force and Attack-Detection Logging

**Builds on:** Week 4 (Logging) and Week 5 (Sessions and Authentication)

> **Note:** This is an optional extra-credit lab. It is shorter than a normal
> lab and is weighted accordingly (**6 points**).

---

## Overview

Password authentication has one unavoidable weakness: if an attacker can submit
guesses without limit, they can eventually try every password on a list. In this
lab you build a brute force attack against HuskyHub's login, watch it generate
traffic in the logs you built in Week 4, then add detection logging that turns a
pile of individual failures into a single high-priority alert. You also add a
second, subtler alert — one that fires when a login *succeeds* right after a
burst of failures, the signature of an attacker who guessed the password before
you could stop them. Finally you close the hole with account lockout and confirm
the attack no longer succeeds.

**Prerequisites:**

- **Week 4's structured JSON logging** — `flask/app/logging_config.py` and the
  `app.log` output must already be in place, including the failed-login WARNING
  event.
- **Week 3.5's HTTPS setup** — nginx now redirects all HTTP traffic to HTTPS and
  serves a self-signed certificate. Your attack script must account for this
  (see Step 2).
- **Week 3's `X-Real-IP` header** — nginx forwards the client's real IP to Flask,
  which you will use in your detection logging.

---

## Tools

| Tool | Purpose |
|------|---------|
| Python requests library | Script a brute force login attempt |
| Terminal | Run the script and read log output |
| Docker | Read the application log inside the container |

### Platform Notes

**Python:**
- macOS and Linux use `python3` and `pip3`.
- Windows uses `python` and `pip` (if Python was installed from python.org with PATH enabled).
- If you are unsure which command works, run `python --version` and `python3 --version` and use whichever responds.

**Installing the requests library:**

```bash
# macOS / Linux
pip3 install requests

# Windows
pip install requests
```

---

## Steps

### 1. Baseline the Login Response

**How to tell a successful login from a failed one over HTTP:**
When you submit the login form in a browser, a successful login returns HTTP 302
(a redirect to the home page) and a failed login returns HTTP 200 (the login page
is simply re-rendered with an error message). A script cannot "see" the page the
way you do, but it can read the status code. This single distinction — 302 means
success, 200 means failure — is the entire basis for an automated attack. Before
automating anything, confirm the signal by hand.

Log in once with a wrong password and once with a correct password while watching
the Network tab in Developer Tools. Record the HTTP status code returned in each
case. Confirm that a correct password produces a 302 and a wrong password produces
a 200.

> **Tip:** In the Network tab, disable "Preserve log" off and make sure you are
> looking at the request to `/login` itself (the POST), not the page it redirects
> to afterward.

---

### 2. Script a Brute Force Attack

**What the requests library does and why `allow_redirects=False` matters:**
The `requests` library lets Python make HTTP requests programmatically.
`requests.post(url, data=...)` sends an HTTP POST with form data — exactly what
your browser does when you submit the login form. `allow_redirects=False` is
critical: on a successful login the server returns 302, and by default `requests`
would silently *follow* that redirect and report the final 200 from the home
page, hiding the signal you need. With `allow_redirects=False`, the script stops
at the 302 and you can read it directly.

**Why the target is `https://` and why we disable certificate verification:**
Since Week 3, nginx redirects every plain-HTTP request to HTTPS. If you point
the script at `http://localhost/login`, the first thing you get back is a `301`
redirect to the HTTPS URL — you never reach the login handler, so you never see a
302 or 200. Target `https://localhost/login` directly. Because the certificate is
self-signed (not issued by a public authority), `requests` will refuse the
connection unless you pass `verify=False`. That is acceptable here because *you*
control this server; never disable verification against a server you do not own.

Write a Python script using the `requests` library that:
1. Reads a wordlist of passwords (use `labs/week-05/wordlist.txt`)
2. POSTs to `/login` for the username `tbrown` with each password in the list
3. Checks the response for a successful login redirect (302)
4. Stops and prints the password when found

```python
import time
import requests
import urllib3

# The server uses a self-signed certificate, so we turn off verification.
# Silence the warning that requests prints every time we do this.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

TARGET = "https://localhost/login"
USERNAME = "tbrown"

attempts = 0
start = time.time()

with open("labs/week-05/wordlist.txt") as f:
    for line in f:
        password = line.strip()
        if not password:
            continue
        attempts += 1
        r = requests.post(
            TARGET,
            data={"username": USERNAME, "password": password},
            allow_redirects=False,   # stop at the 302 instead of following it
            verify=False,            # self-signed cert; see note above
        )
        if r.status_code == 302:
            print(f"[+] Found after {attempts} attempts: {password}")
            break
        else:
            print(f"[-] Tried ({r.status_code}): {password}")

elapsed = time.time() - start
print(f"[*] {attempts} requests in {elapsed:.2f}s "
      f"({attempts / elapsed:.1f} req/s)")
```

Save this as `brute.py` and run it:

**macOS / Linux:**
```bash
python3 brute.py
```

**Windows:**
```powershell
python brute.py
```

Record: how many attempts before the password was found, and roughly how many
requests per second the script achieved (the script prints both).

---

### 3. Observe the Attack in Your Logs

**Why your attack is already partly visible:**
In Week 4 you added a WARNING-level log event for every failed login. Your brute
force script just generated one failed-login entry for every wrong password it
tried — potentially dozens or hundreds of them. The raw material for detecting
this attack already exists in your logs. The problem, as you are about to see, is
that it does not yet *stand out*: a brute force attempt looks like an ordinary
pile of WARNING entries, indistinguishable from a few users mistyping their
passwords.

Read the application log and find the entries your script produced:

```bash
docker exec -it huskyhub-su26-huskyhub-flask-1 cat /var/log/huskyhub/app.log
```

In your report:
- Paste two or three of the failed-login entries generated by your attack.
- Note what information each entry currently contains, and what is *missing*
  that would help an analyst realize these failures are a coordinated attack
  rather than isolated typos (for example: where the requests came from, and how
  rapidly they arrived).

---

### 4. Add Attack-Detection Logging

**What separates a log event from an alert:**
An individual failed login is worth recording but is not, on its own, worth
waking anyone up over — people mistype passwords constantly. What matters for
detection is the *pattern*: many failures against one account, arriving quickly,
from one source. This step makes that pattern visible. First, you enrich every
failed-login record with the source IP address so failures can be attributed to
an origin. Then you emit two distinct, named events: a high-severity CRITICAL
alert the moment failures cross the lockout threshold, and a WARNING when a login
*succeeds* immediately after a run of failures. Monitoring systems alert on
severity and can filter on named event types, so promoting these signals out of
the WARNING noise is what turns your logs into a usable alarm.

**4a. Carry the new fields through the formatter.**
In Week 4 your `JSONFormatter` included optional fields (like `user` and
`endpoint`) only when the log call attached them. Add the same treatment for
three new fields — `source_ip`, `event`, and `failed_attempts` — in
`flask/app/logging_config.py`:

```python
if hasattr(record, "source_ip"):
    log_entry["source_ip"] = record.source_ip
if hasattr(record, "event"):
    log_entry["event"] = record.event
if hasattr(record, "failed_attempts"):
    log_entry["failed_attempts"] = record.failed_attempts
```

**4b. Capture the source IP.**
At the top of the login route, read the client's real IP address. nginx forwards
it in the `X-Real-IP` header (configured back in Week 3); fall back to
`request.remote_addr` if the header is absent:

```python
source_ip = request.headers.get("X-Real-IP", request.remote_addr)
```

**4c. Enrich the failed-login event.**
Update your Week 4 failed-login WARNING so it includes the source IP:

```python
current_app.logger.warning(
    "Failed login",
    extra={"user": username, "endpoint": "/login", "source_ip": source_ip},
)
```

**4d. Emit a distinct brute-force alert.**
When a user's failed-attempt count reaches the lockout threshold (you will wire
up the counter in Step 5), log a single CRITICAL event with a named `event` type
so it can be filtered out of the noise:

```python
current_app.logger.critical(
    "Brute force detected — account locked",
    extra={
        "event": "brute_force_detected",
        "user": username,
        "source_ip": source_ip,
        "failed_attempts": attempts,
    },
)
```

**4e. Flag a successful login that follows a burst of failures.**
Lockout stops an attacker who keeps guessing — but what if the attacker guesses
the *right* password before hitting the threshold? That login succeeds and, with
only the logging you have so far, looks completely ordinary. The clue is the
counter: the `failed_attempts` value still holds the number of consecutive
failures that came immediately *before* this success. A legitimate user
occasionally fumbles a password once or twice; a rapid run of failures ending in
a success is the fingerprint of an automated guess that beat the lockout. When a
login succeeds and that pre-reset count is at or above a suspicion threshold
(use 3), emit a WARNING before you reset the counter:

```python
if user["failed_attempts"] >= 3:
    current_app.logger.warning(
        "Successful login after repeated failures",
        extra={
            "event": "successful_login_after_failures",
            "user": username,
            "source_ip": source_ip,
            "failed_attempts": user["failed_attempts"],
        },
    )
```

This is a WARNING, not a CRITICAL: unlike the lockout event, the login was *not*
blocked, so you cannot be certain it was malicious — it is investigate-worthy,
not automatically alarming. The named `event` still lets an analyst pull every
one of these out of the log in a single query.

> At this point neither the CRITICAL nor this WARNING will fire yet, because
> nothing is counting failures. Step 5 adds the counter that drives the lockout
> and both alerts.

---

### 5. Remediate — Account Lockout

**What lockout prevents, and why the error message stays generic:**
Without account lockout a brute force script can submit unlimited guesses at no
cost. Lockout imposes a rate limit by disabling the account after a threshold of
failures, forcing a time penalty that makes online brute force impractical. The
error message must stay generic — identical whether the password was wrong, the
account does not exist, or the account is locked. If the server announced
"account locked," it would confirm to the attacker that the username is real and
that they had been making progress. A response that looks the same in every
failure case denies the attacker that confirmation.

Add `failed_attempts` and `lockout_until` columns to the `users` table. Run this
against the running database (for example with
`docker exec -it huskyhub-su26-huskyhub-db-1 mysql -u root -p huskyhub`):

```sql
ALTER TABLE users
  ADD COLUMN failed_attempts INT NOT NULL DEFAULT 0,
  ADD COLUMN lockout_until DATETIME NULL;
```

In the login route, add logic that:
- **Checks `lockout_until` before attempting authentication.** If the account is
  currently locked (`lockout_until` is set and still in the future), reject the
  attempt with the generic error — do not even check the password.
- **On a failed login, increments `failed_attempts`** for that account.
- **When `failed_attempts` reaches 5**, sets
  `lockout_until = NOW() + INTERVAL 15 MINUTE` and fires the
  `brute_force_detected` CRITICAL event from Step 4d.
- **On a successful login**, first runs the Step 4e check (fire the
  `successful_login_after_failures` WARNING if `failed_attempts >= 3`), then
  resets `failed_attempts` to 0 and clears `lockout_until`.
- **Returns a generic error message** that does not distinguish a wrong password
  from a locked account from a nonexistent user.

---

### 6. Verify the Remediation

Re-run `brute.py` against the hardened application. In your report:

- **Show the lockout works.** Confirm the account locks after 5 attempts and the
  remaining wordlist entries no longer succeed (every request from attempt 6
  onward returns the failure status, even though the correct password is still
  ahead in the list).
- **Paste the CRITICAL alert.** Read `app.log` and paste the single
  `brute_force_detected` entry. Confirm it includes the `source_ip`, `user`, and
  `failed_attempts` fields.
- **Trigger and paste the success-after-failures alert.** In the browser, log in
  as a user you know the password for: enter the *wrong* password three times,
  then the *correct* password once. Read `app.log` and paste the
  `successful_login_after_failures` WARNING. Confirm it records the
  `failed_attempts` count that preceded the success.
- **Confirm the generic error.** Verify the message returned to the client is the
  same in every failure case: wrong password, nonexistent user, and locked
  account.

```bash
docker exec -it huskyhub-su26-huskyhub-flask-1 cat /var/log/huskyhub/app.log
```

> If you locked `tbrown` out and want to test again before the 15 minutes
> elapse, clear the lockout manually:
> `UPDATE users SET failed_attempts = 0, lockout_until = NULL WHERE username = 'tbrown';`

---

## Write-Up Questions

**Q1.** The `successful_login_after_failures` event (Step 4e) is a WARNING, while
`brute_force_detected` (Step 4d) is a CRITICAL. Justify that difference. What is
the analyst *certain* of in the CRITICAL case that they are only *suspicious* of
in the WARNING case?

**Q2.** Your account lockout triggers after 5 failed attempts **on a single
account**. Consider an attacker who instead tries one common password (say,
`Spring2026!`) against 500 different usernames — a technique called *password
spraying*. Would your per-account lockout detect or stop this attack? Which field
in your enriched log (Step 4) would let an analyst catch it, and what would they
look for?

**Q3.** Your lockout returns the same generic error message whether the password
is wrong or the account is locked. Why? What specific information would you leak
to an attacker if the message said "account temporarily locked" instead?

---

## Hacker Mindset Prompt

Account lockout stops brute force at the front door, but a committed attacker
rarely stands there guessing. They obtain a leaked credential database, crack it
offline where no lockout or logging can see them, and then log in once with the
right password — an event your detection logging might record only as a
`successful_login_after_failures` WARNING at best, or as a perfectly ordinary
successful login at worst.

Reflect on:

- **Contrarian:** Your logs are now good enough to detect a brute force attack in
  progress. But logging is *detection*, not *prevention* — it records the attack,
  it does not stop it. Which control in this lab actually prevents the attack, and
  what does the logging add that prevention alone does not?
- **Committed:** An attacker who steals a database of password hashes cracks them
  offline, at billions of guesses per second, with none of your defenses in play.
  Describe why offline cracking defeats account lockout entirely, and what control
  from an earlier lab is the real defense against it.
