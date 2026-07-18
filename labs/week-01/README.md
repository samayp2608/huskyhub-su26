# Week 1 Lab — Reconnaissance and The Hacker Mindset

**Lecture:** Introduction to Cybersecurity; AI Risk and Ethics

---

## Overview

In this lab you will deploy the HuskyHub Student Services Portal and conduct structured reconnaissance against it. You are not exploiting anything yet. The goal is to build the habit of looking at an application the way an attacker would — systematically documenting every piece of information that is exposed before a single vulnerability has been touched.

---

## Tools

| Tool | Purpose |
|------|---------|
| Docker Desktop | Deploy and run the application |
| Web Browser (Chrome or Firefox) | Interact with the application |
| Browser Developer Tools | Inspect headers, cookies, source, and network traffic |
| A notes document | Record every observation systematically |

---

## Before You Start: Opening a Terminal

Several steps in this course require a terminal — a text-based window where you type commands directly rather than clicking. If you have never used one before, here is how to open it.

**macOS:**
Press `Cmd+Space` to open Spotlight, type **Terminal**, and press Enter. Alternatively: Finder → Applications → Utilities → Terminal.

**Windows:**
This course recommends **Git Bash**, which installs alongside Git in the next section. Once installed, open the Start menu, search for **Git Bash**, and open it. Git Bash uses Unix-style commands (`cp`, `ls`, `cat`) that match all lab examples in this course.

> You may already have PowerShell or Command Prompt. Both will work for most tasks, but they behave differently in some places. When in doubt, use Git Bash.

### Installing Git

**Windows:** Download the installer from [git-scm.com/downloads](https://git-scm.com/downloads). During installation, select **Git Bash Here** and leave all other defaults. This installs both Git and Git Bash together.

**macOS:** Git is included with the Xcode Command Line Tools. If `git` is not recognized when you run it, your system will prompt you to install the tools automatically — follow the prompt.

Once your terminal is open, you are ready to set up the application.

---

## Understanding Developer Tools

Browser Developer Tools is a built-in panel that lets you see what the browser is actually sending and receiving — information that is invisible during normal browsing. You will use it throughout this course.

**Opening Developer Tools:**

| Platform | Keyboard Shortcut |
|----------|-------------------|
| Windows | `F12` or `Ctrl+Shift+I` |
| macOS | `Cmd+Option+I` |

You can also right-click anywhere on a page and select **Inspect**.

**The tabs you will use:**

| Tab | What it shows |
|-----|---------------|
| **Network** | Every HTTP request your browser sends and every response the server returns, including all headers |
| **Application** | Cookies, local storage, and session data the browser is holding for this site |
| **Sources** | JavaScript files and other resources the page loaded |
| **Elements** | The live rendered HTML (different from View Page Source — this reflects JavaScript changes) |
| **Console** | JavaScript errors and a prompt where you can run code against the current page |

---

## Platform Setup

### Installing Docker Desktop

Download Docker Desktop at [docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop/). You do not need a Docker account.

**macOS:** Open the `.dmg`, drag Docker to Applications, and launch it. Wait for the Docker icon in the menu bar to stop animating before proceeding.

**Windows:** Run the installer. When prompted, select **WSL 2** as the backend (not Hyper-V). After installation, open Docker Desktop and wait for the engine to reach "Running" status.

### Cloning the Repository

Open your terminal and run the commands for your platform.

**macOS / Linux (Terminal):**
```bash
git clone https://github.com/Coltigo/huskyhub-su26.git
cd huskyhub-su26
cp .env.example .env
docker compose up --build
```

**Windows (Git Bash — recommended):**
```bash
git clone https://github.com/Coltigo/huskyhub-su26.git
cd huskyhub-su26
cp .env.example .env
docker compose up --build
```

**Windows (PowerShell):**
```powershell
git clone https://github.com/Coltigo/huskyhub-su26.git
cd huskyhub-su26
Copy-Item .env.example .env
docker compose up --build
```

> If `docker compose` is not found on Windows, try `docker-compose` (with a hyphen). Older installations use the hyphenated form.

---

## Steps

### 1. Deploy the Application

**What Docker Compose is doing when you run `docker compose up --build`:**
Docker Compose reads the `docker-compose.yaml` file and starts multiple containers as a coordinated group. The `--build` flag tells Compose to rebuild any container images from their Dockerfiles before starting — this ensures your local source code is compiled into the running containers rather than using a stale cached image. For HuskyHub, Compose starts three containers: an **nginx** web server that handles incoming HTTP requests, a **Flask** application server that runs the Python code, and a **MySQL** database that stores all application data. These containers communicate with each other over a private Docker network, isolated from your machine's network. When all three show a "Running" status in Docker Desktop, the full request path — browser → nginx → Flask → MySQL → Flask → nginx → browser — is functional.

The database container may take up to 60 seconds to initialize before Flask can connect. Only the database container shows a separate "healthy" indicator; Flask and nginx will show "Running" without one. Wait for all three to reach Running before proceeding.

Navigate to [http://localhost:80](http://localhost:80) and log in with:

```
username: jsmith
password: password123
```

---

### 2. Explore Every Page

**Why manual exploration comes before any tool:**
Every automated scanning tool operates by sending requests to URLs it already knows about. If a page is not linked from anywhere the scanner starts, the scanner will not find it. A human walking through the application discovers pages, forms, and behaviors that no tool will enumerate automatically. You are building a mental model of the application's intended behavior — what a legitimate user does, what data flows where, what actions are possible. This model is the baseline against which you later identify deviations: actions that succeed when they should fail, data that appears when it should not, functionality that is accessible without the right credentials. The value of this step compounds across every subsequent lab.

Before using any tools, manually visit every page available to you after logging in. Take note of what each page does and what data it displays or accepts.

Navigate to each page listed below. For each one, copy the full URL from the address bar (including anything after the `?`), note every input field present, and record what data the page displays.

| Page           | Full URL                                | Input fields | Data displayed | Anything unusual? |
|----------------|-----------------------------------------|--------------|----------------|-------------------|
| Home           |http://localhost/                        |Different tab's icons |top bar with tabs, important tabs as icons |Not all tabs have icons |
| Grades         |http://localhost/grades                  |Search bar |Student grade details for different classes |Cannot find anything unusual|
| Enrollment     |http://localhost/enrollment              |Course and quarter selection, search bar, drop button |Courses list(enrolled as well as available) |No need for search course by name option |
| Messages       |http://localhost/messages                |compose message fields |The details of the recieved and sent messages |message displayed for indox but not sent |
| Advising Notes |http://localhost/messages/advising-notes |None |Advisor name, note to student, date |First column title should be advisor not student |
| Documents      |http://localhost/documents               |Upload document fields |List of uploaded documents |Cannot find anything unusual|

**As you explore, pay attention to:**  

- **ID values in the URL.** Does the address bar show something like `?student_id=3` when you view your grades? If a number in the URL appears to identify you, record it. Think about what it represents, and whether changing it might do anything.
- **Search and filter fields.** Any field that accepts text and sends it to the server is worth noting carefully.
- **File upload or download links.** Note any endpoint that serves or accepts files, including the full URL.
- **Links to pages not visible in the main navigation.** Click around — some pages link to other pages that the menu does not list.

---

### 3. Inspect HTTP Response Headers

**What HTTP response headers are and why they matter:**
Every time a web server responds to a request, it includes a set of headers before the actual content. These headers are instructions from the server to the browser — they specify things like how long to cache a page, what type of content follows, and what cookies to store. Developers frequently leave headers enabled that advertise the server software name, version number, and framework in use. For an attacker, this is free intelligence: knowing a server runs nginx 1.21.3 or Flask 2.3.2 immediately narrows down which known vulnerabilities might apply, without having to probe anything.

Open Developer Tools and go to the **Network** tab. Reload the page. Click the main document request (the first one in the list). Under **Response Headers**, record every header you see.

Connection: keep alive
Content-length: 4847
Content-type: text/html; charset=utf-8
Date: Wed, 24 Jun 2026 16:41:32 GMT
Server: nginx/1.31.2

Pay particular attention to:
- `Server`
- `X-Powered-By`
- `Set-Cookie`
- Any header that reveals a technology, version, or configuration detail

---

### 4. Inspect and Interact with Cookies

**What cookies are and what the security flags control:**
A cookie is a small piece of data the server instructs the browser to store and then send back on every subsequent request to that domain. Web applications use cookies to maintain state — the server has no memory between requests, so the cookie tells it who you are and whether you are logged in. Each cookie can carry attributes that control its security behavior. The `HttpOnly` flag prevents JavaScript on the page from reading the cookie, which would otherwise allow an XSS attack to steal it. The `Secure` flag prevents the browser from sending the cookie over an unencrypted HTTP connection. The `SameSite` attribute controls whether the browser sends the cookie on cross-site requests, which affects Cross-Site Request Forgery (CSRF) attacks. A cookie missing these flags is not broken in isolation — but each missing flag is a condition an attacker can exploit under specific circumstances.

#### Part A — Record all cookies

In Developer Tools, open the **Application** tab. Under **Storage**, expand **Cookies** and select **localhost**. For each cookie listed, record:

| Name | Value | HttpOnly | Secure | SameSite | Expires |
|------|-------|----------|--------|----------|---------|
|authenticated |jsmith |False |F  alse |Blank |Session |
|role |student |False |False |Blank |Session |
|user_id |3 |False |False |Blank |Session |

#### Part B — Examine what the values contain

Look at the names and values of the cookies. Do any of them contain information that describes who you are or what your role is in a format you can read — something like `role=student` or `user_id=3`?

Record what you find. Consider: the server reads these values back on every request and uses them to decide who you are and what you are allowed to do. If the server accepts whatever value the browser sends without any further verification, what does that mean for someone who can control what the browser sends?

#### Part C — Modify a cookie and observe the result

Double-click the **value** field of the `role` cookie in the Application panel. Change the value from `student` to `admin`. Reload the page and navigate to `/admin/users`.

Record exactly what happens. Whether access is granted or denied, both outcomes tell you something about how the application validates identity. Document your finding.
A) Here I am able to see the list of users/accounts and their roles

> Restore the original `role` cookie value before continuing.

---

### 5. View Page Source

**What page source reveals and why developers leave things in it:**
The HTML source of a page is everything the browser received from the server before rendering it. Developers frequently leave HTML comments (`<!-- notes about the code -->`), hidden form fields, and JavaScript variable assignments containing session data or internal identifiers. These are visible to any user who presses Ctrl+U — they are not hidden in any meaningful security sense. Hidden form fields in particular are a common mistake: developers sometimes use them to pass data that should never be user-controlled (like database record IDs or privilege levels) because they do not appear visually. Any data in a hidden field can be read and modified by the user before the form is submitted.

Right-click each page and select **View Page Source**. Search for:
- HTML comments (`<!-- ... -->`)
- Hidden form fields (`<input type="hidden">`)
- JavaScript variable assignments that contain user data
- Any hardcoded paths, usernames, or internal identifiers
- References to endpoints not visible in the navigation

Record at least five findings.

Comment(All pages): <!-- DB: huskyhub-db:3306 | Backend: Flask/Python -->
Comment(All pages):   <!-- App version: 1.0.0 | Environment: development | Build: 2024-01-15 -->
Hidden field(Grades page): <input type="hidden" name="student_id" value="3">
Hidden field(Enrollment page): <input type="hidden" name="enrollment_id" value="1">
                               <input type="hidden" name="enrollment_id" value="2">
Hardcoded Username and role(all pages in nav bar): Welcome, jsmith (student)

---

### 6. Map the Attack Surface

**What an attack surface is:**
An attack surface is the complete set of points where an attacker could attempt to interact with a system in an unauthorized way. For a web application, this includes every URL that accepts input, every form field that processes data, every file upload endpoint, and every external resource loaded from a CDN or third party. The more of these entry points exist, the more opportunities an attacker has. Mapping the attack surface is not an attack itself — it is the systematic inventory that makes everything else possible. A skilled attacker maps before they move.

Compile a complete list of every URL, form, input field, file upload point, and external resource (CDN scripts, stylesheets) you can find across the entire application.

URL/endpoint | HTTP Method | Accepts Input(Yes/No) | Notes

---------------------------|----------|-----|------------------------------------------------
/                          | GET      | No  | Home dashboard
/login                     | GET/POST | Yes | username + password fields, no CSRF token
/register                  | GET      | No  | New endpoint found in login page source
/logout                    | GET      | No  | Ends user session
/grades                    | GET      | Yes | student_id and search as GET params — IDOR risk
/enrollment                | GET      | Yes | search as GET param
/enrollment/add            | POST     | Yes | course_id, quarter fields
/enrollment/drop           | POST     | Yes | enrollment_id hidden field — IDOR risk
/messages                  | GET      | No  | Inbox and sent view
/messages/send             | POST     | Yes | recipient_id, subject, body — HTML allowed, XSS risk
/messages/advising-notes   | GET      | No  | Advising notes view
/documents                 | GET      | No  | Document list view
/documents/upload          | POST     | Yes | File upload, no visible file type restriction
/chatbot                   | GET/POST | Yes | textarea input — prompt injection risk, debug comment in source
/static/css/style.css      | GET      | No  | Local static file, reveals path structure
cdn.jsdelivr.net bootstrap CSS | GET  | No  | External CDN, no SRI hash
cdn.jsdelivr.net bootstrap JS  | GET  | No  | External CDN, no SRI hash

Format this as a table with columns: URL/Endpoint, HTTP Method, Accepts Input (yes/no), Notes.

This is your attack surface map. In later labs you will use this list with automated tools that probe each entry systematically; the more complete your map is now, the more complete your coverage will be then.

---

### 7. Explore as a Different User

**What comparing accounts reveals and why this matters:**
Most access control vulnerabilities are not visible from a single account. A student who only ever logs in as themselves will never notice that the grades page accepts any `student_id` value — because their own ID works correctly and they never try another. By comparing what two different-privilege accounts can see and do, you begin building intuition for what the application is *supposed* to scope to an individual and where it fails to do so. Note anything that differs: different menu items, different data visible, different error messages. Each difference is a signal about the application's access control model — whether that model is enforced correctly is what you will test in later labs.

Log out and log in with a student account:

```
username: alee
password: alexpass
```

Explore the application and note any differences from the `jsmith` account in what you can see or do. Pay attention to the cookie values for this account as well.

I think most of the information and access is same for both the students(looking at cookies confirmed that they both have the role designated as student).

Log out again and log in with an advisor account:

```
username: mwilson
password: advisor123
```

Compare what this account can access with what the student accounts could access. Note any differences in available pages, data, or actions.

The advising notes tab is different for an advisor compared to a student. The advisor is able do more than just view on the tab. In the cookies we can see that the assigned role is advisor.

Consider whether the data each account sees appears to be correctly scoped — and whether there are any ways to reach information that does not seem intended for that account.

It doesn't make sense for the advisor to be able to enroll in classes or need the AI Academic Advisor tab. Same applies for the enrollment and  grades tab. It would make more sense if these tabs were tweeked for the advisor to be able to view students' data.

---

## Write-Up Questions

Answer each question in your lab report under **Section 3: Class Principles**.

**Q1.** During your exploration, what were two or three things you noticed about the application that surprised you or felt worth paying attention to? You don't need to know exactly why they matter yet — describe what you observed and take a guess at why an attacker might find it interesting.

I didn't expect to find the dabase i  details to be in the HTML comments. This gives an attacker key information needed to hack. The second one was the similarity between the advisor and student experience. The advisor should have different tabs compared to a student. Also I feel like the security levels of a advisor's account should also be higher. The cookie values found on inspecting are worrying as well because anyone can change the role, name or student id number in it since its directly visible.

**Q2.** List the cookies the application sets and note which security flags are missing. Pick one missing flag and explain, in your own words, what you think could go wrong without it.

| Name | Value | HttpOnly | Secure | SameSite | Expires |
|------|-------|----------|--------|----------|---------|
|authenticated |jsmith |false |false |Blank |Session |
|role |student |false |false |Blank |Session |
|user_id |3 |false |false |Blank |Session |

From what I have read and understood it is an important point to notice the missing HttpOnly missing flag. This makes it possible to enter and run scripts through the input fields.


**Q3.** In Step 4, you looked at the values stored in the cookies and tried changing one. What did the cookie values tell you about how the application tracks who you are? What happened when you modified the `role` cookie, and what does that suggest about how the application makes decisions?

When I tried to change the role from student to advisor the student for the same access as an advisor. Being able to give oneself any role/access level they want just by going into the cookies section is really unsafe. This can also help gain access to other student's information just by knowing their authenticated(name/username) and thier id number. The application probably uses the values provided to it to identify a user and their access levels.

**Q4.** What assumptions does this application appear to make about who is using it? Describe at least two and explain what might happen if those assumptions turned out to be wrong.

The app is firstly assuming that a student will only log into their own account. That is why all the access information is lying around in the page source and the cookie is storing important information that can just be manipulated. It is also assuming that the user will use the application in the intended way. There are input fields that can be used to hack or manipulate the data on this application very easily.

**Q5.** Referencing the Week 1 Thursday lecture on AI Risk, identify at least one AI-related risk that you think might be present in an application like HuskyHub if it included an AI assistant. Explain your reasoning.

One risk is that the AI might reveal sensitive information if heavily prompted to do so. If the boundries for the AI aren't set up correctly there can be a huge loophole in the security system for the application.

---

## Hacker Mindset Prompt

The hacker mindset is a way of approaching systems, not just software, that is contrarian, committed, and creative. **Contrarian** means actively looking for what a system was not designed to handle: the edge case, the unintended input, the assumption the developer made without realizing it. A contrarian thinker asks "what happens if I do something the designer didn't expect?" rather than accepting the designed path. **Committed** means being willing to spend time on a problem that doesn't immediately yield. Real attackers are patient: they read documentation, build mental models, and try things methodically rather than giving up when the first attempt doesn't work. **Creative** means connecting observations that don't seem related and imagining uses for information that weren't the intended ones. A piece of data that looks harmless in isolation may be exactly what an attacker needed to complete a puzzle.

Reconnaissance is where all three traits show up at once. You are deliberately looking for what a developer did not intend to expose — every comment left in HTML, every cookie flag omitted, every endpoint discoverable from page source is information the developer assumed would go unnoticed.

Reflect on the following in your Section 4 write-up:

- **Contrarian:** What assumptions did the application developers appear to make about their users? Where did trusting those assumptions expose information?
- **Committed:** A real attacker spends hours or days on reconnaissance before exploiting anything. What would a thorough attacker do next after building the attack surface map you created today?
- **Creative:** Looking at everything you observed in this lab, what is one thing about HuskyHub that you think is worth investigating further, even if you aren't sure yet whether it's actually a vulnerability? What would you want to try?
