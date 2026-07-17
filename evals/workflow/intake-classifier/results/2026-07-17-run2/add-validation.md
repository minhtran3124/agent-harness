Lane: normal
Confidence: high
Reason: Modifies existing WatchlistService.create behavior (flag 8) with no prior test on the affected path (flag 9) across two files (service + test), so it clears tiny's ≤1-file bar but no hard gate fires — adding validation does not trip the "weakening validation" gate.
Flags: existing-behavior, weak-proof
Escalate: no
