# 3. METHOD (с. 6–9)

[с. 6]
3. METHOD
3.1. Network architecture
The surrogate is a U-Net [16] with about5.1×106 parameters (Fig. 4). The encoder is a stem
convolution to64channels followed by three max-pooling stages to128,256and512channels
x–6

[с. 7]
Moscow University Physics Bulletin80(9), x (2026)
(Mish activations). The decoder has three stages, each a transposed convolution, concatenation
of the encoder skip connection, and a modulated double convolution (convolution, GroupNorm,
wind modulation, Mish, convolution, GroupNorm, Mish) with256,128and64channels. A1×1
convolution produces the five output maps. The output is masked geometrically: at each height
the prediction is zeroed in cells where the building is taller than that level (the “Mean” map is
left unmasked); the same masking is applied in the metrics so that trivial zeros inside buildings
do not inflate the scores.
Figure 4. Architecture: a U-Net with a64–128–256–512encoder and skip connections. The global
wind vector is embedded by an MLP and injected into every decoder level through FiLM (𝛾, 𝛽).
3.2. Wind conditioning via FiLM
To test whether an explicit, strict dependence on wind improves the fit, the decoder is
conditioned on the global wind vector through Feature-wise Linear Modulation (FiLM) [17].
The wind3-vector is embedded by a two-layer MLP (3→128→512) and, at each decoder
levelℓ, a linear projection yields a per-channel scale𝛾ℓ and shift𝛽 ℓ; the feature map after the
first convolution and normalisation is modulated as
FiLM(hℓ) = (1 +𝛾 ℓ)⊙h ℓ +𝛽 ℓ.
Disabling the conditioning (“no FiLM”, used in the ablation study) forces𝛾ℓ =𝛽 ℓ = 0. Whether
this mechanism actually helps is tested in Sec. 4.3.
x–7

[с. 8]
Deep Learning in Computational Physics
3.3. Loss function
All quantities are compared in log space,ˆ𝑦= log(1 +ˆ𝐶),𝑦= log(1 +𝐶). The loss combines a
plume-weighted mean square error, a plume-weighted mean absolute error, and an unweighted
anchor term,
𝐿= MSE 𝑤 +𝜆 1 MAE𝑤 +𝜆 2 MSE, 𝜆 1 = 0.05, 𝜆2 = 1.0,
with per-pixel weights capped and normalised per scene,
𝑤= min
(︀
exp(𝛽𝑦), 𝑐max
)︀
⟨︀
min(exp(𝛽𝑦), 𝑐max)
⟩︀
scene
, 𝛽= 1, 𝑐 max = 50.
The weighted terms focus the model on the plume; the anchor term counteracts background
overestimation.
3.4. Evaluation metrics
Qualityisassessedwiththeair-qualitymetricsofChangandHanna[18], computedinphysical
space (afterexp(·)−1) with building interiors excluded. With𝐶𝑜 the LES and𝐶𝑝 the prediction
and⟨·⟩a spatial average,
FB = 2 (⟨𝐶𝑜⟩−⟨𝐶 𝑝⟩)⟨𝐶𝑜⟩+⟨𝐶 𝑝⟩ ,NMSE = ⟨(𝐶𝑜−𝐶 𝑝)2⟩⟨𝐶𝑜⟩⟨𝐶 𝑝⟩ ,
F AC2 =fraction of cells with0.5≤𝐶 𝑝/𝐶𝑜≤2.0,
together with𝑅 2 = 1−⟨(𝐶 𝑝−𝐶 𝑜)2⟩/Var(𝐶𝑜), the RMSE, the MAE, and the mass ratio
mass_ratio = ∑︀ 𝐶𝑝/ ∑︀ 𝐶𝑜, a diagnostic of the surrogate (ideal value one) rather than a con­
straint enforced during training. A model is acceptable whenF AC2≥0.5andNMSE≤1.5
with small|FB|.
3.5. Baselines and training
Two geometry-agnostic baselines are used: amean-fieldbaseline (the training-set average
field, per pixel and level) and anearest-windbaseline (the target of the training sample whose
wind vector is closest). Models are trained with AdamW (learning rate10−5, batch size256)
and a ReduceLROnPlateau schedule (factor0.5, patience5); each epoch takes about200s. Two
checkpoints are kept, one at minimum validation loss and one at maximum validation𝑅2; the
plume-weighted loss and𝑅2 anti-correlate late in training, so the reported production model is
the best-𝑅2 checkpoint, obtained by fine-tuning a converged model for a further100epochs.
x–8

[с. 9]
Moscow University Physics Bulletin80(9), x (2026)
