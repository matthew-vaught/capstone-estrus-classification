## Relevant Research: LA–CBT Relationship Features for Estrus-Day Classification

**Paper:** Burks, J. H., & Smarr, B. L. (2026). *Dynamical model of aperiodic locomotor activity effects on mouse core body temperature removes transient perturbations from longitudinal temperature signals.* Scientific Reports.

### 1. Main Idea

This paper investigates the dynamic relationship between locomotor activity (LA) and core body temperature (CBT) in mice using minute-resolution time-series recordings.

The authors argue that CBT is influenced by two interacting physiological processes:

- **Activity-induced heating:** Increases in LA tend to raise CBT.
- **Temperature-dependent cooling:** CBT naturally decays toward a resting temperature when activity decreases.

They developed a simple, interpretable three-parameter dynamical model to describe these processes and predict CBT from LA.

Importantly, they found that **the relationship between LA and CBT changes depending on whether female mice are in estrus**, suggesting that features describing this relationship could be useful for estrus-day classification.

### 2. Mathematical Model

The authors model temperature changes using a first-order dynamical system that can be written as:

\[
\widehat{T}_{t+1}=\widehat{T}_t+a_1 LA_t-a_2(\widehat{T}_t-T_{\min})
\]

where:

- \(a_1\): Activity-induced heating coefficient, measuring how strongly LA contributes to increasing CBT.
- \(a_2\): Temperature decay coefficient, measuring how strongly CBT returns toward its resting temperature (written here as a positive cooling strength).
- \(T_{\min}\): Estimated minimum/resting CBT.

The parameters are estimated from recorded LA and CBT data.

Unlike a model that simply correlates LA with CBT, this model explicitly accounts for the fact that temperature depends on its previous state and responds dynamically to activity.

### 3. Key Findings Relevant to Estrus Detection (Figure 4)

The authors compared fitted model parameters across three conditions:

- Male mice (M)
- Female non-estrus days (NE)
- Female estrus days (E)

Their findings include:

**Activity heating coefficient (\(a_1\)):**
- Significantly lower during estrus than non-estrus (\(p<0.01\)).
- Suggests that the estimated effect of activity on temperature differs by estrous state.

**Temperature decay coefficient (\(a_2\)):**
- Significantly lower during estrus than non-estrus (\(p<0.01\)).
- Suggests that thermoregulatory cooling dynamics differ during estrus.

**Minimum temperature (\(T_{\min}\)):**
- Differed significantly between male and female mice.
- Was less clearly distinguishable between female estrus and non-estrus conditions.

**Model prediction error (RMSE):**
- Differed significantly across physiological conditions, with generally higher errors during estrus.
- Suggests that temperature dynamics during estrus may be less completely explained by activity-induced heating and baseline cooling.

When the authors plotted their three fitted parameters in a three-dimensional feature space (Figure 4E), male and female samples were separable. However, **they did not demonstrate perfect separation of female estrus versus non-estrus days**.

### 4. Residual Temperature Analysis (Figure 5)

The authors also analyzed the residuals between observed and predicted CBT:

\[
r_t=T_t-\widehat{T}_t
\]

These residuals represent temperature variation not explained by the modeled LA heating and CBT cooling effects.

They observed:

- Persistent circadian and ultradian structure in the residuals.
- Different residual patterns between estrus and non-estrus conditions.
- Elevated positive residuals during portions of the light phase on estrus days.

These findings suggest that residual temperature dynamics may contain additional information related to estrous state.

The residuals should not automatically be interpreted as purely hormonal effects, since they may also contain unmodeled physiological processes and model error.

### 5. Potential Applications to Our Classification Task

Our capstone project aims to classify individual days as **estrus or non-estrus** using minute-resolution LA and CBT recordings.

The paper suggests that we should consider features describing the *relationship between LA and CBT*, rather than relying exclusively on features extracted from each signal independently.

Potential features include:

| Feature | Interpretation |
|---|---|
| \(a_1\) | Estimated heating response to locomotor activity |
| \(a_2\) | Estimated temperature decay/cooling strength |
| \(T_{\min}\) | Estimated resting temperature |
| CBT prediction RMSE | How well activity and cooling explain observed CBT |
| Mean CBT residual | Average unexplained temperature elevation |
| Light-phase residual mean | Unexplained temperature elevation during the light phase |
| Residual variance | Variability in temperature not captured by the dynamical model |

Additional relationship features worth investigating, though not established as estrus predictors in this paper, include LA–CBT cross-correlation and the time lag between activity and temperature responses.

### 6. Important Methodological Considerations

The paper was primarily designed to model CBT dynamics and compare physiological conditions, **not to train a supervised estrus-day classifier**.

The authors fitted models using longer recordings and estrous-state-specific data. Therefore, their statistically significant parameter differences do not guarantee that these parameters can be estimated reliably or used for classification from individual 24-hour windows.

For our project, we would need to investigate:

1. Whether fitting the dynamical model independently to each 24-hour mouse-day produces stable, meaningful parameter estimates.
2. Whether the estimated parameters differ systematically between estrus and non-estrus days in our dataset.
3. Whether these relationship features improve held-out classification performance beyond conventional LA and CBT features.
4. Whether any feature extraction or model fitting introduces label leakage.

### 7. Overall Takeaway

**The paper provides evidence that the dynamic relationship between locomotor activity and core body temperature differs between estrus and non-estrus conditions.**

Its strongest implication for our project is that estrus-related information may be encoded not only in the individual LA and CBT signals, but also in the physiological relationship between them.

A promising direction would be to extract interpretable dynamical-model parameters and residual statistics as features, then evaluate whether they improve estrus-day classification when combined with traditional time-series features.

These features should be treated as hypotheses to test rather than established estrus classifiers, because the paper does not report supervised, held-out estrus-day classification accuracy.