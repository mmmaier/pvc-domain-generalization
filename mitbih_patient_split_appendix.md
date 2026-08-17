# MIT-BIH Arrhythmia Database — Patient-Level Split (Paper Appendix)

Companion document to `mitbih_patient_split.csv`. Covers (1) the database itself,
(2) the exclusion criteria applied, (3) the patient-level train/val/test split used in
this repo, and (4) how that split was verified.

## 1. Source database

**MIT-BIH Arrhythmia Database** (PhysioNet, mitdb v1.0.0), recorded by the BIH
Arrhythmia Laboratory (Beth Israel Hospital, Boston), 1975–1979.

- 48 half-hour, two-channel ambulatory ECG excerpts from 47 subjects (one subject,
  records 201/202, contributed two records).
- Subjects: 25 men aged 32–89, 22 women aged 23–89.
- 23 records chosen at random from a pool of ~4,000 24-hour recordings from a mixed
  inpatient (~60%) / outpatient (~40%) population; the remaining 25 records were
  selected purposively to include less common but clinically significant arrhythmias.
- Digitized at 360 Hz per channel, 11-bit resolution over a 10 mV range.
- Each record independently annotated by ≥2 cardiologists, disagreements adjudicated;
  ~110,000 beat annotations in total across the database.

Sources:
- [MIT-BIH Arrhythmia Database v1.0.0 — PhysioNet](https://physionet.org/content/mitdb/1.0.0/)
- [MIT-BIH Arrhythmia Database Directory — Introduction](https://physionet.org/physiobank/database/html/mitdbdir/intro.htm)
- [MIT-BIH Arrhythmia Database Directory — Records](https://physionet.org/physiobank/database/html/mitdbdir/records.htm)

## 2. Exclusion: paced-beat records

Four of the 48 records contain a paced rhythm (demand pacemaker or complete heart
block with paced beats): **102, 104, 107, 217**. These were dropped before splitting, 
leaving **44 records / 44 patients** for the train/val/test split. This matches 
standard practice in MIT-BIH beat-classification work, where paced-rhythm 
records are excluded because a paced QRS morphology is not comparable 
to an intrinsic beat and confounds classification.

## 3. Patient-level split

| Split | # patients | Patient share | # beats | Beat share | # PVC beats | Patients |
|---|---|---|---|---|---|---|
| train | 29 | 65.9% | 66,085 | 65.8% | 5,977 | 101, 105, 111, 112, 113, 114, 117, 122, 123, 124, 200, 201, 202, 203, 205, 207, 208, 209, 210, 212, 214, 220, 221, 222, 223, 228, 230, 231, 233 |
| val | 7 | 15.9% | 14,100 | 14.0% | 1,154 | 106, 108, 115, 116, 119, 121, 219 |
| test | 8 | 18.2% | 20,234 | 20.2% | 856 | 100, 103, 109, 118, 213, 215, 232, 234 |

29 + 7 + 8 = 44 patients = 48 database records − 4 paced-beat records (102, 104, 107,
217). The split is strictly patient-level: no patient appears in more than one split.

The target split ratio was **64 / 16 / 20** (train/val/test) at the patient level.
The realized ratio is **65.9 / 15.9 / 18.2**, which is a very close approximation.

## 5. Files

- `mitbih_patient_split.csv` — one row per MIT-BIH record: split assignment, age,
  sex, per-record beat counts (total / normal / PVC / excluded-other), and the
  clinical note from the PhysioNet record directory. The 4 paced-beat records are
  included as `split = excluded_paced` (beat counts `NA`) for completeness.

Age/sex/clinical notes are as published in the PhysioNet MIT-BIH records directory;
`NR` = not reported for that record (103, 219).
