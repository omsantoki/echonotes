# Checklist: Requirements Quality — Accounts & Multi-Tenancy

<!-- Spec Kit artifact: specs/002-accounts-multitenancy/checklists/requirements.md
A "unit test for the spec." Run before /speckit.plan to catch gaps. -->

## Completeness
- [ ] Every user story has acceptance criteria (US-8…US-14)
- [ ] Core vs Strong vs Stretch clearly tiered (signup/OTP/login/isolation = Core)
- [ ] All functional requirements (FR-14…FR-31) traceable to a user story and a T1xx task
- [ ] Non-goals explicitly stated (no teams/roles/SSO this round)

## Clarity / ambiguity
- [ ] No unresolved [NEEDS CLARIFICATION] remain (see research.md)
- [ ] "owner", "session token", "verified", "single-use token" defined unambiguously
- [ ] Hasher, session mechanism, and Google verification path decided

## Constitution alignment
- [ ] Tenant isolation required everywhere; 404 (not 403) for non-owned (Art. X)
- [ ] No plaintext passwords / OTPs / tokens; secrets via env only (Art. X)
- [ ] Owner filter pushed into the storage layer, not just routes (Art. X)
- [ ] Per-course persistence preserved, now per-user (Art. V)
- [ ] Core merge (001) untouched; accounts wrap it (Art. I)
- [ ] Audio still never persisted (Art. IV)

## Demo readiness
- [ ] Success metrics defined and observable (two-user isolation; OTP-in-log signup)
- [ ] New user signs up → processes the real demo lecture (Art. VIII)
- [ ] Deploy env (JWT/SMTP/Google/migration) is a tracked task

## Local-first / risk coverage
- [ ] Whole flow runs with blank SMTP/OAuth/JWT (console email, dev secret, hidden Google button)
- [ ] Email-enumeration risk mitigated (uniform signup / forgot / login responses)
- [ ] OTP brute-force + token replay mitigated (TTL, attempt limit, single-use, hashed)
- [ ] Google token spoofing mitigated (server-side cert + audience + issuer check)
- [ ] Legacy "common" courses migrated, not dropped (bootstrap owner)
