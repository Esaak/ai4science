# 4. RESULTS (с. 9–13)

[с. 9]
4. RESUL TS
4.1. Predictive accuracy
Table 1 reports the production model in physical space, per level and overall. Accuracy is
high (𝑅2 = 0.86,F AC2 = 0.75,NMSE = 0.44,FB = 0.07, aggregatemass_ratio = 0.93) and
satisfies the Chang–Hanna criteria; it is fairly uniform with height, best at the vertical-mean
output (𝑅2 = 0.88).
Table 1. Production surrogate, physical space, buildings excluded, over the test set. RMSE and MAE
are in𝜇g/m 3.
Level Height, m 𝑅2 RMSE MAE FB FAC2 NMSE
Z1 3 0.833 3116 1078 0.069 0.751 0.503
Z5 10 0.867 2297 810 0.077 0.750 0.390
Z8 16 0.876 2015 679 0.062 0.744 0.372
Z25 50 0.866 1768 511 0.093 0.712 0.471
Mean (output) — 0.881 1863 579 0.072 0.771 0.367
Overall — 0.862 2256 728 0.074 0.746 0.442
4.2. Baselines
Both geometry-agnostic baselines have negative𝑅2 andF AC2<0.2(mean-field𝑅 2 =−0.31,
F AC2 = 0.19; nearest-wind𝑅2 =−0.72,F AC2 = 0.15), i.e. they are worse than predicting the
mean, so the surrogate’s skill comes from resolving the source and vegetation layout, not from
the marginal statistics of the field or from the wind alone.
4.3. Ablation study
In an ablation study — disabling one component at a time to measure its contribution —
Table 2 compares, at convergence and under a matched protocol (from scratch,200epochs,
best-loss checkpoint), the full model against the same network without FiLM and without
augmentation. Two results stand out. Removing the augmentation is clearly harmful (every
x–9

[с. 10]
Deep Learning in Computational Physics
physical metric degrades:𝑅 2 0.798→0.737,mass_ratio 0.865→0.832), so the augmentation
is an essential ingredient. Removing FiLM, by contrast, does not hurt — it improves every
physical metric (higher𝑅 2, lowerFBandNMSE, and markedly better mass conservation,
mass_ratio = 0.928). In log space all three variants are nearly identical (log-𝑅2 0.896,0.900,
0.888): the differences appear only in the physical mass and bias, which the log-space loss does
not directly control. We conclude that, in this regime, wind conditioning gives no measurable
benefit and slightly worsens the mass-balance metric (mass_ratiofarther from one), whereas
augmentation is required.
We report the FiLM model as the production system because it is best checkpoint under the
best-𝑅2, fine-tuned protocol (Table 1); the ablation study is internally consistent (all variants
from scratch, best-loss) but uses a different selection protocol, so its absolute level is below
the production number and the two should not be compared directly. We can not claim the
production model would be worse without FiLM.
Table 2. Ablation at convergence (200epochs, matched protocol, physical space, over the test set).
Best value per column in bold.
Variant 𝑅2 RMSE MAE FB NMSE mass_ratio
Full (FiLM + aug) 0.798 2729 1013 0.145 0.694 0.865
Without FiLM (aug) 0.822 2561 997 0.075 0.570 0.928
Without augmentation (FiLM) 0.737 3110 1224 0.183 0.937 0.832
4.4. Governing inputs
For the problem setup considered here, the predicted field is determined chiefly by the emis­
sion input — the location and magnitude of the sources — and by the vegetation (LAI), which
redistributes and removes the scalar; the fixed building geometry and the single-speed wind
direction play a secondary role. This ordering is consistent with the ablation study of Sec. 4.3,
in which removing the explicit wind conditioning leaves accuracy essentially unchanged, and
with the dataset design, in which the source and vegetation layouts are the primary degrees
of freedom. We emphasise that it is specific to the present regime (fixed geometry, fixed wind
speed) and is not a general statement about the relative importance of these inputs.
x–10

[с. 11]
Moscow University Physics Bulletin80(9), x (2026)
4.5. Physical validity
Across three different test scenes, the predicted fields place the plume correctly but smear
its fine structure (Fig. 5), and the parity plot (Fig. 6) shows a background floor near𝐶≈0and
under-prediction of the highest concentrations — the signature of a log-space MSE objective.
Mass is well calibrated in the median (Fig. 7); a small subset of scenes (1.5%of the test set,
withmass_ratio<0.1) forms a separate cluster nearmass_ratio≈0.05andFB≈1.6, i.e. the
surrogate predicts a near-zero field where the LES contains a strong plume.
Figure 5. Three different test scenes (one per row): building footprint, LES concentration (level Z1),
surrogate prediction, and absolute error. The plume location is captured; fine structure is smeared.
Colour bars: concentration in𝜇g/m3 (shared scale for LES and prediction) and absolute error.
x–11

[с. 12]
Deep Learning in Computational Physics
Figure 6. Parity plot (log space): the prediction tracks the LES over the full range, with a background
floor at𝐶≈0and under-prediction of the largest values. Colour indicates point density (log scale).
Figure 7. Distributions of the mass ratio (median0.97) and fractional bias (median0.04). A minority
of scenes cluster near zero mass ratio (missed plume).
4.6. Computational cost
The surrogate evaluates one scene in about3.5ms on an NVIDIA Tesla V100-DGXS-32GB
GPU (∼284scenes/s). For reference, one LES run on the same GPU takes about20min for a
single-tracer configuration and about30min when16tracers are released simultaneously, the
flow solve dominating the cost. Per delivered concentration field this is≈1.2×10 3 s (single
tracer) or≈1.1×10 2 s (amortised over16tracers), so the surrogate is faster by four to five
x–12

[с. 13]
Moscow University Physics Bulletin80(9), x (2026)
orders of magnitude. As both costs are measured on the same GPU, the comparison is on
identical hardware and reflects end-to-end wall-clock time to a stationary field.
