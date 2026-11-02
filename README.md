# Vasu Job Search Automation - Phase 1

This is the local-first Phase 1 dry-run system.

What it does:
- loads synthetic jobs only
- normalizes and deduplicates jobs
- scores jobs with configurable 0-100 weights
- evaluates screening questions against the approved truth store
- prepares dry-run application packages
- creates an approval queue
- writes structured logs
- stores results in SQLite
- generates a daily markdown report

What it does not do:
- no LinkedIn, Indeed, or company portal connection
- no Playwright or Selenium
- no browser form filling
- no real credentials
- no real application submission
- no auto-apply

Run:

```bat
D:\VASU_JOB_SEARCH_AUTOMATION\RUN_PHASE1_DRY_RUN.bat
```

Run tests:

```bat
D:\VASU_JOB_SEARCH_AUTOMATION\00_README_AND_LAUNCHERS\RUN_TESTS.bat
```

Important source limitation:
- The approved pasted career profile is included as the initial verified truth source.
- An approved Master Resume file was not found during setup, so resume-backed evidence is marked as required input before future phases.

