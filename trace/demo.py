"""Fictional scenario designed to make source disagreement inspectable."""

DEMO = {
    'title': 'The Meridian launch',
    'questions': [
        'What is blocking the Meridian launch, and which metrics disagree?',
        'What does the team recommend before the rollout?',
        'What do we know about checkout latency and error rate?',
    ],
    'documents': [
        {'name': '01-launch-brief.md', 'text': '''# Meridian / Launch brief
Fictional demo · 21 October 2026 · Product

Meridian is a checkout redesign scheduled for a staged launch on 28 October.
The launch is blocked until checkout latency and error rate meet the release gates.
Checkout latency must remain below 500 ms at p95 during a full 30-minute load test.
Error rate must remain below 1% before the rollout can begin.
The launch gate also requires a tested rollback and a named on-call owner.
The team recommends a 5% rollout first, followed by a review after 24 hours.
The release owner is Avery Chen. Product has not approved skipping the performance gate.
'''},
        {'name': '02-performance-report.md', 'text': '''# Meridian / Performance report
Fictional demo · 22 October 2026 · Platform

The performance report covers a 10-minute staging test at 200 requests per second.
Checkout latency is 420 ms.
Error rate is 0.6%.
The staging test used a warm cache and disabled payment-provider retries.
These results do not satisfy the full 30-minute release gate.
The platform team recommends repeating the checkout load test with production-like retries and a cold cache.
'''},
        {'name': '03-incident-notes.md', 'text': '''# Meridian / Incident notes
Fictional demo · 24 October 2026 · Reliability

A production-like checkout rehearsal triggered payment-provider timeouts.
Checkout latency is 870 ms.
Error rate is 3.8%.
The retry queue is saturated when the payment provider responds slowly.
The rehearsal used a cold cache and enabled payment-provider retries.
Checkout latency and error rate exceed the release gates under these conditions.
The incident lead recommends a retry cap, jittered backoff, and a fresh 30-minute load test before launch.
Rollback was exercised successfully in staging. The on-call owner is not yet confirmed.
'''},
        {'name': '04-decision-log.md', 'text': '''# Meridian / Decision log
Fictional demo · 25 October 2026 · Release review

Decision: defer the Meridian rollout until the performance release gates pass.
The 420 ms staging measurement and 870 ms rehearsal measurement used different cache and retry settings.
The metrics are not directly comparable without a controlled repeat test.
Reliability will implement the retry cap and jittered backoff.
Platform will run the same 30-minute checkout load test in both environments.
The release owner must confirm an on-call owner before the launch review.
Recommendation: keep the tested rollback, start at 5% traffic only after gates pass, and review after 24 hours.
No final launch approval has been recorded.
'''},
    ],
}
