# 1. INTRODUCTION (с. 2–3)

[с. 2]
1. INTRODUCTION
Air quality is a significant factor of public health, and road traffic is one of the leading con­
tributors to urban air pollution [1]. A trustworthy spatial estimate of the pollutant distribution
in a city requires resolving the interaction of the wind flow with the building geometry, including
street-canyon channelling and recirculation in the wakes of buildings.
Numerical approaches to turbulent scalar transport trade accuracy against computational
cost, with the two well-established families occupying opposite extremes of this trade-off. Large
Eddy Simulation (LES) resolves the energy-containing eddies responsible for most of the scalar
transport and is the reference tool for urban-canopy flows [2, 3], but reaching a quasi-stationary
regime takes wall-clock time that precludes operational analysis or a sweep over many config­
urations. At the opposite side, semi-empirical Gaussian plume models are cheap but do not
* E-mail: gerasimov.ia@phystech.edu
x–2

[с. 3]
Moscow University Physics Bulletin80(9), x (2026)
account for the building geometry at all. Machine-learning surrogates trained on high-fidelity
data can approximate the non-linear map from boundary conditions to the dispersion field at
a cost comparable to analytical models: neural networks have been used to emulate urban
pollutant dispersion for emergency forecasting [4] and, more generally, convolutional networks
predict steady flow fields orders of magnitude faster than a Computational Fluid Dynamics
(CFD) solver [5].
Machine-learning surrogates for airflow and dispersion in the built environment have devel­
oped rapidly; a comprehensive review is given by Calzolari and Liu [6]. Coupled CFD–ML
models estimate ventilation and pollutant exchange in dense urban settings [7], dedicated emu­
lators target operational dispersion forecasting for accidental releases [4], and operator-learning
methods such as the Fourier neural operator approximate the solution map of the governing
equations directly [8]. Most of these surrogates, however, predict a single near-surface plane
rather than the vertical structure of the field, fix the emission sources and vary only the inflow,
and report aggregate error without the physically grounded metrics standard in air-quality
model evaluation.
This work develops a fast surrogate for the steady-state PM2.5 field of an idealized urban
canopy at several heights and analyses which physical inputs govern its predictions. It differs
from prior machine-learning surrogates in three respects: the target is multi-level (four heights
and the vertical mean) rather than a single near-surface plane; the model is evaluated with
the standard Chang–Hanna dispersion criteria and an explicit mass-balance check, not with
𝑅2 alone; and a controlled component ablation study quantifies the roles of wind conditioning
and data augmentation. Two results are established. First, for the present setup the predicted
field is governed primarily by the emission sources and the vegetation. Second, the ablation
study establishes that data augmentation is essential to accuracy, whereas the wind-conditioning
mechanism (Feature-wise Linear Modulation, FiLM) yields no measurable improvement and
slightly worsens the mass-balance metric.
