# Blog Security Audit and Repair Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Audit the production Django blog boundary, fix confirmed information-disclosure, source-IP spoofing, fail-open configuration, and abuse-rate issues, then publish an evidence-based audit article.

**Architecture:** Keep existing Django/DRF endpoints and response envelopes. Add security defaults at configuration boundaries, trust proxy headers only from configured local proxies, and apply scoped DRF throttles only to login and public comment creation. Publish the final report as a normal text article after deployment verification.

**Tech Stack:** Django 5.1, Django REST Framework, Simple JWT, Django test runner, Nginx/Gunicorn deployment.

---

### Task 1: Lock the audit findings with regression tests

**Files:**
- Modify: `blog/tests.py`
- Modify: `apps/user/tests.py`
- Modify: `apps/comment/tests.py`

- [x] Add tests for hidden `/api/`, preserved child routes, trusted proxy parsing, ten-failure login throttling, and ten-comment public throttling.
- [x] Run each new test before the implementation and confirm the old behavior fails.

### Task 2: Apply production boundary fixes

**Files:**
- Modify: `blog/settings.py`
- Modify: `blog/request_utils.py`
- Modify: `apps/user/views.py`
- Modify: `apps/comment/views.py`
- Modify: `blog/urls.py`

- [x] Make `DJANGO_DEBUG` default to `False`; allow the test runner to use the development key only for isolated tests.
- [x] Configure JSON-only DRF responses, trusted proxy IPs, and scoped rates of `10/minute` for login and public comments.
- [x] Ignore `X-Forwarded-For` when the direct peer is not a configured trusted proxy.
- [x] Apply scoped throttling to login and anonymous comment creation.
- [x] Return a JSON `404` from the exact `/api/` root while retaining all child routes.

### Task 3: Verify and release

**Files:**
- No additional production files.

- [x] Run the complete Django suite and deployment checks with safe temporary settings.
- [x] Push the backend change to `main`.
- [x] Back up the live URL configuration, deploy the code, restart Gunicorn, and verify `/api/` is `404`, `/api/users/` is `401`, and services are active.
- [ ] Publish the final audit article titled `我的博客安全审计并修复` only after the live verification is complete.
