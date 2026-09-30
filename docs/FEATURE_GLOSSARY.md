# RRM-XGB Feature Glossary

Auto-generated from `rrm_features/feature_manifest.json` (465 features, extracted by `data_prep/extract_rrm_features.py`). Band edges: [0.5, 4.0, 8.0, 16.0, 32.0, 45.0] Hz (Butterworth order 4, zero-phase `sosfiltfilt`). Morphology window: -200 to 300 ms around each beat's R peak. Positions: `prev`/`curr`/`next` = previous/target/next beat in the recording.

**Tag legend** (added for feature-group design, not part of the original manifest):
- `amplitude-scale-sensitive` vs `ratio/normalized` vs `timing, calibration-invariant`: whether the feature is a raw physical-unit amplitude/energy/area statistic (device-gain-dependent), a dimensionless ratio/normalized difference, or an RR-interval duration in seconds (device-independent since it only depends on the sampling clock, not signal amplitude). **`amplitude-scale-sensitive` features are the ones implicated in the MIT-BIH→NAKO transfer collapse** (see project findings) — note that even `ratio/normalized` and RR-timing features can individually show distributional shift between datasets ("threshold saturation"), but this alone did not cause the collapse; it was specifically the amplitude-scale features that did, in large simultaneous numbers.
- `freq-band` vs `broadband-only`: whether the feature depends on the 5-band Butterworth decomposition, or only on the unfiltered broadband signal.
- `uses-neighbor` vs `single-beat`: whether the feature needs the previous/next beat's own window (NaN when that neighbor's R peak falls outside the stored 5s window), or only the target beat.


---
## 1. `rr__` — RR-Interval Timing (10 features)

Local rhythm timing around the target beat. `m1`/`p1` = RR interval to the immediately previous/next beat; `m2`/`p2` = one interval further out (i.e. `[m2,m1,p1,p2]` is one contiguous local 4-interval sequence). All are computed in seconds or as dimensionless ratios of these intervals.

| Feature | Tags | Description |
|---|---|---|
| `rr__prev_s` | timing, calibration-invariant, broadband-only, uses-neighbor | RR interval to the previous beat (s) |
| `rr__next_s` | timing, calibration-invariant, broadband-only, uses-neighbor | RR interval to the next beat (s) |
| `rr__prevprev_s` | timing, calibration-invariant, broadband-only, uses-neighbor | RR interval between beat[-2] and beat[-1] (s) |
| `rr__nextnext_s` | timing, calibration-invariant, broadband-only, uses-neighbor | RR interval between beat[+1] and beat[+2] (s) |
| `rr__local_mean_s` | timing, calibration-invariant, broadband-only, uses-neighbor | Mean of the 4 local RR intervals (prevprev,prev,next,nextnext) (s) |
| `rr__local_median_s` | timing, calibration-invariant, broadband-only, uses-neighbor | Median of the 4 local RR intervals (s) |
| `rr__ratio_next_over_prev` | timing, calibration-invariant, broadband-only, uses-neighbor | RR_next / RR_prev -- local rhythm acceleration(<1)/deceleration(>1) around the target beat (ratio) |
| `rr__local_asymmetry` | timing, calibration-invariant, broadband-only, uses-neighbor | (RR_prev-RR_next)/(RR_prev+RR_next), bounded in [-1,1]; >0 means the beat arrived late relative to its follower (ratio) |
| `rr__rel_dev_prev_from_local` | timing, calibration-invariant, broadband-only, uses-neighbor | Relative deviation of the coupling interval (RR_prev) from the local mean RR -- how premature the beat is (ratio) |
| `rr__rel_dev_next_from_local` | timing, calibration-invariant, broadband-only, uses-neighbor | Relative deviation of RR_next from the local mean RR -- captures e.g. a post-PVC compensatory pause (ratio) |

---
## 2. `bb__` / `band__` — Absolute Morphology (117 features)

Physical-unit statistics computed on a short morphology window (-200..300 ms around the R peak) of the **prev/curr/next** beat, on the **broadband** (unfiltered) signal (`bb__`, 9 stats) and on each of the **5 Butterworth sub-bands** (`band__<band>__`, 6 stats each — broadband-only gets 2 extra slope/derivative stats). Naming: `bb__<pos>__<stat>` or `band__<band>__<pos>__<stat>`.

**Statistic formulas** (x = the windowed signal, or its band-filtered version):

| Stat | Formula |
|---|---|
| `p2p` | max(x) - min(x)  (peak-to-peak amplitude) |
| `max_abs_amp` | max(|x|)  (largest absolute sample value) |
| `rms` | sqrt(mean(x^2))  (root-mean-square amplitude) |
| `energy` | sum(x^2)  (signal energy) |
| `abs_area` | sum(|x|)  (integral of the absolute value, i.e. area under |x|) |
| `waveform_length` | sum(|diff(x)|)  (cumulative absolute sample-to-sample change) |
| `max_pos_slope` | max(diff(x))  (steepest upward step) |
| `max_neg_slope` | min(diff(x))  (steepest downward step) |
| `max_abs_deriv` | max(|diff(x)|)  (largest absolute sample-to-sample step, either direction) |

**Broadband (`bb__`), 9 stats × 3 positions = 27 features:**

| Position | Stats computed |
|---|---|
| `prev` | `bb__prev__{abs_area, energy, max_abs_amp, max_abs_deriv, max_neg_slope, max_pos_slope, p2p, rms, waveform_length}` — amplitude-scale-sensitive, broadband-only, uses-neighbor |
| `curr` | `bb__curr__{abs_area, energy, max_abs_amp, max_abs_deriv, max_neg_slope, max_pos_slope, p2p, rms, waveform_length}` — amplitude-scale-sensitive, broadband-only, single-beat |
| `next` | `bb__next__{abs_area, energy, max_abs_amp, max_abs_deriv, max_neg_slope, max_pos_slope, p2p, rms, waveform_length}` — amplitude-scale-sensitive, broadband-only, uses-neighbor |

**Per-band (`band__`), 6 stats × 5 bands × 3 positions = 90 features:**

| Band | Hz range | Stats × positions |
|---|---|---|
| `0p5_4` | 0.5-4 Hz | `band__0p5_4__{prev,curr,next}__{abs_area,energy,max_abs_amp,p2p,rms,waveform_length}` |
| `4_8` | 4-8 Hz | `band__4_8__{prev,curr,next}__{abs_area,energy,max_abs_amp,p2p,rms,waveform_length}` |
| `8_16` | 8-16 Hz | `band__8_16__{prev,curr,next}__{abs_area,energy,max_abs_amp,p2p,rms,waveform_length}` |
| `16_32` | 16-32 Hz | `band__16_32__{prev,curr,next}__{abs_area,energy,max_abs_amp,p2p,rms,waveform_length}` |
| `32_45` | 32-45 Hz | `band__32_45__{prev,curr,next}__{abs_area,energy,max_abs_amp,p2p,rms,waveform_length}` |

All `band__`/`bb__` features are tagged `absolute-scale` — this is the family most implicated in the cross-device amplitude-scale mismatch found in the MIT-BIH→NAKO collapse diagnostic.


---
## 3. `relbeat__` — Beat-to-Beat Relative Morphology (234 features)

Every one of the 39 `bb__`/`band__` **absolute base features above** (9 broadband + 30 per-band = 39 distinct stat×band combos), turned into 6 curr-vs-neighbor comparisons each (39 × 6 = 234). Naming: `relbeat__<base_feature>__<comparison>`.

| Comparison suffix | Formula | Tags |
|---|---|---|
| `curr_over_prev` | current beat / previous beat | ratio/relative |
| `curr_over_next` | current beat / next beat | ratio/relative |
| `curr_over_neighbor_mean` | current beat / mean(previous, next) (uses whichever neighbor is available) | ratio/relative |
| `curr_minus_prev_over_prev` | (current - previous) / (|previous|+eps) | ratio/relative |
| `curr_minus_next_over_next` | (current - next) / (|next|+eps) | ratio/relative |
| `prev_over_next` | previous beat / next beat (neighbor asymmetry, independent of the target beat) | ratio/relative |

Example: `relbeat__band__4_8__curr__energy__curr_over_prev` = (4-8 Hz energy of the current beat) / (4-8 Hz energy of the previous beat). Base feature can be `bb__` (broadband, position already fixed to the relevant one internally) or `band__<band>__`. This family is only **5.6% saturated by gain** in the collapse diagnostic — the safest of the morphology-derived families.


---
## 4. `relfreq__` — Cross-Frequency Composition, Current Beat Only (60 features)

Compares the current beat's own energy/amplitude distribution **across the 5 frequency bands** (no neighbor beat involved). Computed for 4 stats (`energy`, `rms`, `abs_area`, `max_abs_amp`): 5 fraction-of-total + 10 pairwise band ratios (all C(5,2)=10 unordered band pairs) = 15 features/stat × 4 stats = 60.

**Fraction-of-total** (`relfreq__<stat>__<band>__fraction_total`): this band's stat, divided by the sum of that stat across all 5 bands.

**Pairwise ratios** (`relfreq__<stat>__<bandA>_over_<bandB>`), all 10 band pairs:

- `abs_area__0p5_4_over_16_32`
- `abs_area__0p5_4_over_32_45`
- `abs_area__0p5_4_over_4_8`
- `abs_area__0p5_4_over_8_16`
- `abs_area__16_32_over_32_45`
- `abs_area__4_8_over_16_32`
- `abs_area__4_8_over_32_45`
- `abs_area__4_8_over_8_16`
- `abs_area__8_16_over_16_32`
- `abs_area__8_16_over_32_45`
- `energy__0p5_4_over_16_32`
- `energy__0p5_4_over_32_45`
- `energy__0p5_4_over_4_8`
- `energy__0p5_4_over_8_16`
- `energy__16_32_over_32_45`
- `energy__4_8_over_16_32`
- `energy__4_8_over_32_45`
- `energy__4_8_over_8_16`
- `energy__8_16_over_16_32`
- `energy__8_16_over_32_45`
- `max_abs_amp__0p5_4_over_16_32`
- `max_abs_amp__0p5_4_over_32_45`
- `max_abs_amp__0p5_4_over_4_8`
- `max_abs_amp__0p5_4_over_8_16`
- `max_abs_amp__16_32_over_32_45`
- `max_abs_amp__4_8_over_16_32`
- `max_abs_amp__4_8_over_32_45`
- `max_abs_amp__4_8_over_8_16`
- `max_abs_amp__8_16_over_16_32`
- `max_abs_amp__8_16_over_32_45`
- `rms__0p5_4_over_16_32`
- `rms__0p5_4_over_32_45`
- `rms__0p5_4_over_4_8`
- `rms__0p5_4_over_8_16`
- `rms__16_32_over_32_45`
- `rms__4_8_over_16_32`
- `rms__4_8_over_32_45`
- `rms__4_8_over_8_16`
- `rms__8_16_over_16_32`
- `rms__8_16_over_32_45`

Note from the collapse diagnostic: `rms`-based pairwise ratios were consistently **not** saturated on NAKO, while `abs_area`/`energy`-based ratios involving the 0.5-4 Hz or 16-32 Hz bands mostly **were** — a same-unit ratio does not fully cancel the cross-device scale/spectral-shape difference.


---
## 5. `relfreqbeat__` — Cross-Frequency Composition vs. Neighbor (20 features)

Per band, the energy-fraction-of-total (broadband) of the current beat compared against the same quantity for the previous/next beat. 5 bands × 4 comparisons (`curr_over_prev_fraction`, `curr_over_next_fraction`, `curr_minus_prev_fraction`, `curr_minus_next_fraction`) = 20.

| Feature | Description |
|---|---|
| `relfreqbeat__0p5_4__curr_over_prev_fraction` | 0.5_4 Hz energy-fraction ratio: current beat / previous beat |
| `relfreqbeat__0p5_4__curr_over_next_fraction` | 0.5_4 Hz energy-fraction ratio: current beat / next beat |
| `relfreqbeat__0p5_4__curr_minus_prev_fraction` | 0.5_4 Hz energy-fraction difference: current beat - previous beat |
| `relfreqbeat__0p5_4__curr_minus_next_fraction` | 0.5_4 Hz energy-fraction difference: current beat - next beat |

(Same 4-comparison pattern repeats identically for the other 4 bands: 4-8 Hz, 8-16 Hz, 16-32 Hz, 32-45 Hz.)


---
## 6. `similarity__` — Waveform Similarity to Neighbor (24 features)

Pearson correlation and normalized RMSE between the current beat's window and its previous/next neighbor's window, computed on the broadband signal and each of the 5 sub-bands (6 sources) × 2 neighbors × 2 metrics = 24.

| Metric | Formula |
|---|---|
| `pearson_curr_<neighbor>` | Pearson correlation coefficient between current and neighbor window |
| `nrmse_curr_<neighbor>` | RMSE(current, neighbor) / max(p2p(current), p2p(neighbor)) |

Despite the p2p-normalization, `similarity__broadband__nrmse_curr_next/prev` are the **single largest saturated features** in the MIT-BIH-trained model (≈30% of total gain combined) — NAKO beats are systematically more self-similar to their neighbors (median nRMSE 0.03) than MIT-BIH beats (median 0.056), likely reflecting lower recording noise / more regular rhythm in the population cohort, not amplitude scale per se.


---
## Summary

| Family | # Features | Amplitude-scale-sensitive? | Uses frequency bands? | Uses neighbor beat? |
|---|---|---|---|---|
| `rr__` | 10 | No (timing, calibration-invariant) | No | Yes (prev/next RR) |
| `bb__` | 27 | **Yes** | No (broadband) | prev/next positions only |
| `band__` | 90 | **Yes** | **Yes** | prev/next positions only |
| `relbeat__` | 234 | No (ratio) | Mixed (bb- and band-based) | Yes |
| `relfreq__` | 60 | No (ratio) | **Yes** | No |
| `relfreqbeat__` | 20 | No (ratio/fraction) | **Yes** | Yes |
| `similarity__` | 24 | No (normalized) | Mixed (broadband + 5 bands) | Yes |
| **Total** | **465** | | | |

Suggested feature-group axes for the next ablation round (see chat discussion): (1) Full 465; (2) single-beat-only, no RR, no neighbor (99 feat., existing "Beat-only"); (3) + RR timing (109 feat., existing "Beat+RR"); (4) **NEW** — drop all `freq-band`-tagged features, keep only broadband + RR (tests whether the 5-band decomposition is needed at all); (5) **NEW** — drop all `amplitude-scale-sensitive`-tagged features, keep RR + every ratio/normalized family (tests the absolute-vs-relative hypothesis directly, decided a priori from these tags, *not* by looking at NAKO performance).
