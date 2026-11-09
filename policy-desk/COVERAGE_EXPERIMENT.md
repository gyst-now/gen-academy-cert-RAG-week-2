# Retrieval coverage experiment

The baseline is the hybrid search on main. All four variants searched the same 119 handbook chunks with the same answer model and a five-passage limit. The original suite has 15 questions, including 11 answerable cases. The fresh suite has 10 questions, including 7 answerable cases.

Recall is the mean share of expected sections found per answerable question. Complete evidence counts questions that retrieved every expected section. Citation coverage is the mean share of expected sections cited. Route accuracy checks the response type across all questions. Citation coverage and routing do not establish claim accuracy.

## Original questions

| Variant | Recall@5 | MRR@5 | Complete evidence | Expected citations | Correct route | Mean time |
|---|---:|---:|---:|---:|---:|---:|
| Existing hybrid | 90.9% | 0.597 | 9/11 | 90.9% | 15/15 | 2.07 s |
| Dense | 90.9% | 0.848 | 9/11 | 86.4% | 15/15 | 2.01 s |
| Dense + heading diversity | 90.9% | 0.848 | 9/11 | 86.4% | 15/15 | 2.08 s |
| Dense + diversity + splitting | 90.9% | 0.848 | 9/11 | 90.9% | 15/15 | 2.23 s |

| Case | Expected sections | Hybrid ranks | Dense ranks | Dense + diversity ranks | Dense + diversity + splitting ranks |
|---|---:|---|---|---|---|
| D01 | 1 | 1 | 1 | 1 | 1 |
| D02 | 1 | 2 | 1 | 1 | 1 |
| D03 | 1 | 5 | 1 | 1 | 1 |
| D04 | 1 | 5 | 3 | 3 | 3 |
| D05 | 1 | 1 | 1 | 1 | 1 |
| D06 | 1 | 2 | 2 | 2 | 2 |
| D07 | 1 | 1 | 1 | 1 | 1 |
| X01 | 2 | 5, 2 | 2, 1 | 2, 1 | 2, 1 |
| X02 | 2 | 3, miss | 1, 3 | 1, 3 | 1, 2 |
| X03 | 2 | 1, 3 | 1, miss | 1, miss | 1, miss |
| X04 | 2 | miss, 3 | 2, miss | 2, miss | 2, miss |

## Holdout questions

| Variant | Recall@5 | MRR@5 | Complete evidence | Expected citations | Correct route | Mean time |
|---|---:|---:|---:|---:|---:|---:|
| Existing hybrid | 42.9% | 0.350 | 2/7 | 42.9% | 8/10 | 1.92 s |
| Dense | 71.4% | 0.786 | 4/7 | 71.4% | 10/10 | 1.76 s |
| Dense + heading diversity | 71.4% | 0.786 | 4/7 | 71.4% | 10/10 | 1.79 s |
| Dense + diversity + splitting | 92.9% | 0.833 | 6/7 | 92.9% | 10/10 | 2.72 s |

| Case | Expected sections | Hybrid ranks | Dense ranks | Dense + diversity ranks | Dense + diversity + splitting ranks |
|---|---:|---|---|---|---|
| H01 | 1 | 5 | 1 | 1 | 1 |
| H02 | 1 | miss | 1 | 1 | 1 |
| H03 | 2 | miss, miss | 1, 3 | 1, 3 | 1, 2 |
| H04 | 2 | 1, miss | 1, miss | 1, miss | 1, 2 |
| H05 | 2 | miss, miss | miss, 2 | miss, 2 | 2, 3 |
| H06 | 2 | 4, miss | miss, miss | miss, miss | miss, 3 |
| H07 | 1 | 1 | 1 | 1 | 1 |

## Failure analysis

- On the fresh questions, the combined variant improved complete evidence from 2/7 to 6/7. Separate searches recovered both expected sections for H04 and H05, including the older Workday correction procedure and the work handoff instructions.
- The original suite still had two incomplete cases. The combined variant recovered the extended sick-leave section for X02 but missed the planned-absence communication section for X03. It also missed the parental-leave initiation section for X04.
- A targeted review found that hybrid answered H02 with general Slack instructions instead of the documented Who’s Out? workflow. Dense retrieval found the procedure at rank one, and the combined variant cited it in the answer.
- H07 exposed a risk of relying on heading-level scores alone. Dense with heading diversity retrieved the reinstatement window but dropped a second chunk under the same heading that explains the employee’s return position. The combined variant retrieved and cited both chunks after searching the two parts separately.
- H06 still missed the expected parental-pay section in the combined run. The answer cited related parental-leave and U.S. pay passages, which did not replace the expected global statutory-pay guidance.

The combined variant is the strongest coverage candidate on these 10 fresh questions. Its average time was 0.80 seconds higher than hybrid on the fresh set, measured from the local runner against live services. The full set of generated claims was not manually graded. The branch keeps hybrid as its default so all variants can be compared explicitly.
