Classifier Calibration at Scale: An Empirical Study of
Model-Agnostic Post-Hoc Methods
Valery Manokhin∗1 and Daniel Grønhaug†2
1Independent Researcher
2University of Oslo
Abstract
Westudymodel-agnosticpost-hoccalibrationmethodsintendedtoimproveprobabilistic
predictions in supervised binary classification on real i.i.d. tabular data, with particular
emphasis on conformal and Venn-based approaches that provide distribution-free validity
guarantees under exchangeability. We benchmark 21 widely used classifiers, including linear
models,SVMs,treeensembles(CatBoost,XGBoost,LightGBM),andmoderntabularneural
and foundation models, on binary tasks from the TabArena-v0.1 suite using randomized,
stratified five-fold cross-validation with a held-out test fold. Five calibrators—Isotonic
regression, Platt scaling, Beta calibration, Venn–Abers predictors, and Pearsonify—are
trained on a separate calibration split and applied to test predictions. Calibration is
evaluated using proper scoring rules (log-loss and Brier score) and diagnostic measures
(Spiegelhalter’s Z, ECE, and ECI), alongside discrimination (AUC-ROC) and standard
classification metrics.
Across tasks and architectures, Venn–Abers predictors achieve the largest average reduc-
tions in log-loss, followed closely by Beta calibration, while Platt scaling exhibits weaker
and less consistent effects. Beta calibration improves log-loss most frequently across tasks,
whereas Venn–Abers displays fewer instances of extreme degradation and slightly more
instancesofextremeimprovement. Importantly,wefindthatcommonlyusedcalibrationpro-
cedures,mostnotablyPlattscalingandisotonicregression,cansystematicallydegradeproper
scoring performance for strong modern tabular models. Overall classification performance is
often preserved, but calibration effects vary substantially across datasets and architectures,
and no method dominates uniformly. In expectation, all methods except Pearsonify slightly
increase accuracy, but the effect is marginal, with the largest expected gain about 0.008%.
Code and artifacts are available at github.com/valeman/classifier_calibration.
∗Valery.Manokhin.2015@live.rhul.ac.uk
†dfgronha@math.uio.no
6202
naJ
91
]GL.sc[
1v44991.1062:viXra

Contents
1 Introduction 4
2 Results 5
3 Conclusion 21
4 Foundation and ideas 21
4.1 Supervised k-class classification . . . . . . . . . . . . . . . . . . . . . . . . . . . 21
4.2 Architectures . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 22
4.3 Datasets . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 25
4.3.1 Synthetic . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 25
4.3.2 Real . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 27
4.4 Models . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 30
4.5 Calibration methods . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 32
4.5.1 Post-hoc calibration . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 32
4.6 Performance . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 35
4.6.1 Classification ability . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 36
4.6.2 Discriminatory ability . . . . . . . . . . . . . . . . . . . . . . . . . . . . 36
4.6.3 Calibration . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 37
4.6.4 Computational cost . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 42
4.7 Evaluation strategy . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 44
4.8 Performance evaluation . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 45
5 Experiment 48
5.1 Reproduction . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 48
5.2 Description . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 48
5.2.1 Models . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 48
5.2.2 Calibration methods . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 49
5.2.3 Datasets . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 50
2

5.2.4 Evaluation strategy . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 50
5.2.5 Performance measures . . . . . . . . . . . . . . . . . . . . . . . . . . . . 50
5.3 Evaluation of the experiment . . . . . . . . . . . . . . . . . . . . . . . . . . . . 51
5.4 Scope of inference . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 52
5.5 Future extensions . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 53
| 6 Sources    |       | 56  |
| ------------ | ----- | --- |
| A Additional | Plots | 60  |
3

1 Introduction
This paper studies model-agnostic post-hoc calibration methods for producing better-calibrated
class probability vectors in supervised binary classification on real i.i.d. tabular data. We focus
on methods applicable to popular machine learning models, including classical models (e.g.,
support vector machines), decision tree models (e.g., XGBoost, CatBoost), and neural networks
(e.g., ModernNCA). Our key objectives include:
• Identify Robust Calibration Techniques:
Identify methods that consistently yield well-calibrated outputs, serving as strong starting
points for practitioners.
• Model-Agnostic Approaches:
All methods explored are general approaches applicable across a variety of models and
datasets. We do not explore methods specific to any architecture.
• Preserve Overall Performance:
Calibration is not considered in isolation, we aim to preserve overall performance.
Calibration is the degree of which class scores reflect actual probabilities. If the score of class j is
0.8, you should expect class j to be the true class 80% of the time (Pavlovic, 2025). Calibration
is critical for reliable decision making in risk-sensitive domains (healthcare, finance, etc.) (Chen
et al., 2018; Fonseca and Lopes, 2017) and for tasks like model ensembling (Zhang et al., 2020) ,
cost-sensitive learning (Yang and Bi, 2025), and uncertainty quantification (Shen et al., 2023).
However, calibration is essential not only in risk-sensitive domains but also in various machine
learning applications, including ranking systems (Kweon et al., 2022) and online advertising
(Wei et al., 2024), where accurate probabilistic predictions are crucial for optimal performance.
To identify which calibration techniques consistently deliver well-calibrated outputs, we employ
an empirical research design. We evaluate twenty-one popular classifiers, namely Class prior,
Support vector machine, Logistic Regression, Linear Discriminant Analysis, Naïve bayes, K-
Nearest Neighbours, RandomForest, Gradient Boosting Classifier, Histogram Gradient Boosting,
ExtraTrees, Explainable Boosting Machine, Catboost, XGBoost, LightGBM, ModernNCA,
TabTransformer, TabICL, TabPFN v2, TabM, Multilayer Perceptron and Real Multilayer
Perceptron. We evaluate all methods on binary tasks from the TabArena-v0.1 dataset suite
using randomized, stratified five-fold cross-validation, where four folds are used for training
and one fold is held out for out-of-sample testing. We then apply five post-hoc calibrators
generated by holding out a calibration set from the training folds. The calibrations are Isotonic
regression, Platt scaling, Beta calibration, Venn-Abers predictors, and Pearsonify. Thereafter,
we measure changes in calibration on the held-out test fold after applying the calibrators
using Brier score, Spiegelhalter Z-statistic, Log-loss, ECE, and ECI. Afterwards we control for
changes in discriminatory ability (AUC-ROC), classification (accuracy, recall, precision and
F1 score), and computational cost (training/inference time, CPU/RAM usage). Methods that
consistently improve calibration without degrading overall performance are highlighted. Not all
4

measurements and models are presented in our results, to view specific measures on specific
models examine the artifacts in our archive. These are available on our GitHub repository.
Among the post-hoc methods studied—Isotonic regression, Platt scaling, Beta calibration,
Venn–Abers predictors, and Pearsonify—we observe substantial variation in their effects across
models and datasets. In particular, Platt scaling and isotonic regression can degrade calibration
and proper scoring performance for strong modern tabular models. By contrast, Beta calibration
and Venn–Abers predictors more consistently improve calibration relative to out-of-the-box
baselines, although no method dominates uniformly and overall classification performance is
typically preserved.
2 Results
The experiment described in section 5 produce logs which we leverage to generate the statistics
we’ll present here. These logs can be found in the archive. We’ll begin by exploring the
performance of the base models across all datasets and folds. Then we’ll examine how each
calibration method affect this performance. Lastly, we’ll comment on inter-model variance.
Figure 1: The expected ranking of each model by log-loss, across datasets and folds. No calibration.
Evaluated on an out-of-sample test set. The best rank is 1 and the worst is 21.
The foundation models and tree based models tend to outperform with regards to log-loss. MLP,
NB and KNN are the bottom performers and tend to do worse then AVG. TICL leads with an
expected rank of 2.52, which is 1.27 lower then the runner up CB. CB, TABPFN and EBM
are within a whole rank of each-other. GBC and the rest follow up with more the 2.33 higher
expected rank then EBM.
5

Figure 2: The expected ranking of each model by brier score, across datasets and folds. No calibration.
Evaluated on an out-of-sample test set. The best rank is 1 and the worst is 21.
As for brier score, the picture is similar too log-loss. But values vary. TICL leads with an
expected rank of 2.99, CB second with 3.99. CB, EBM and TABPFN are within a whole rank
of each-other before the rest follow after a gap of 2.68 in expected rank.
Figure 3: The expected ranking of each model by ECI global, across datasets and folds. No calibration.
Evaluated on an out-of-sample test set. The best rank is 1 and the worst is 21.
The highest performer is AVG with an expected rank of 3.16. This illustrates the aforementioned
issue with ECE based measures. Predicting the constant expectation or the empirical class
distribution minimizes the measure. Notably, EBM, CB, TICL and TABPFN still make up the
top ranks. However, now GBC is a closer contender.
6

Figure 4: The expected ranking of each model by brier score and log-loss, across datasets and folds.
No calibration. Evaluated on an out-of-sample test set. The best rank is 1 and the worst is 21.
A model’s log-loss and brier score rank are relatively linear with some outliers. Notably log-loss
penalizes large deviations between the true class and the assigned probability more then the
brier score. A lower brier score rank relative to log-loss rank could therefore be interpreted as
having more predictions closer to the true class, but also a higher prevalence of large deviations.
KNN for example ranks higher in log-loss then in brier score, which we interpret as a larger
prevalence of egregious mistakes (i.e. assigning a probability of 0 to the true class.).
Figure 5: The expected ranking of each model by total CPU seconds during training, across datasets
and folds. No calibration. Evaluated during training. The best rank is 1 and the worst is 21.
AVG ranks 1st with an expected rank of 1.01 and is the model which consumes the least
7

compute during training. Followed by NB, KNN and LDA with respective expected ranks of
2.39, 2.71 and 5.48. The bottom three are TABM, NCA and REMLP. TABPFN ranks 6th with
an expected rank of 7.45 1. CB and EBM rank 16th and 17th respectively with an expected
rank of 16.53 and 16.84. TICL ranks 10th with an expected rank of 9.11.
Figure 6: The expected ranking of each model by peak RAM usage during training, across datasets
and folds. No calibration. Evaluated during training. The best rank is 1 and the worst is 21.
In terms of peak RAM usage during training TICL leads with an expected rank of 1.84, while
TABM, NCA and AVG follow with 4.37, 5.12 and 5.86. The bottom performers are KNN, EBM,
RF and LGBM. While TABPFN has an expected rank of 7.53 and CB has 10.67.
Figure 7: The expected ranking of each model by total CPU seconds during inference, across datasets
and folds. No calibration. Evaluated during inference. The best rank is 1 and the worst is 21.
1Note,forTABPFNwe’veusedsettingswhichshiftcomputetoinferencesincethedocsadvisedassuchwhen
few instances of inference are expected.
8

Notably TICL and TABPFN almost always rank last with regards to CPU seconds during
inference with respective expected ranks of 20.33 and 20.67 out of 21 models. Top three are
AVG, NB and LDA with respective 1.49, 3.08 and 3.57 as expected ranking. EBM and CB rank
5th and 7th with expected rankings of 5.21 and 8.24.
Figure 8: The expected ranking of each model by peak RAM usage during inference, across datasets
and folds. No calibration. Evaluated during inference. The best rank is 1 and the worst is 21.
In terms of peak RAM usage during inference TABM, NCA and AVG lead with 3.31, 4.02 and
5.10 in expected rank. TABPFN, RF and LGBM come last. TICL has an expected ranking of
15.4, CB has 9.45 and EBM has 16.71.
Figure 9: The expected ranking of each model by total CPU seconds during training and inference,
across datasets and folds. No calibration. The best rank is 1 and the worst is 21.
9

The lowest compute consumption during training and inference is given by AVG, followed by
NB, LDA, GBC and RF. The worst are given by NCA, TABM and TTRA. TICL ranks in
the middle wrt. training but very low wrt. inference. TABPFN lies close to TICL but with
somewhat worse inference rank and better training rank 2. CB ranks lower-mid wrt. to training
but upper-middle wrt. inference. Lastly EBM provides lower-mid training cost but with good
inference cost.
Figure 10: The expected ranking of each model by total CPU seconds during training and log-loss,
across datasets and folds. No calibration. The best rank is 1 and the worst is 21.
TICL gives best log-loss but at a somewhat higher cost to training compute. in contrast,
TABPFN provides somewhat worse log-loss but you save training compute. CB and EBM
provide good log-loss but are on the worse end wrt. to training compute.
2Remember pre-trained models have consumed compute resources not reported here.
10

Figure 11: The expected ranking of each model by total CPU seconds during inference and log-loss,
across datasets and folds. No calibration. The best rank is 1 and the worst is 21.
The best balance between log-loss and inference compute is given by EBM, GBC and CB. While,
TABPFN and TICL provide better log-loss but at bottom rank inference compute costs.
(a) Training CPU time vs. cells (b) Peak training RAM vs. cells
Figure 12: Log axes. Lines are interpolated second-order polynomials.
These plots shows how a model’s peak RAM and consumed CPU seconds during training scales
with the size of the dataset. We see TABM, NCA and REMLP are indeed the highest training
compute consumers. While AVG, NB and KNN consume the least. Peak RAM usage scales
gently with size expect for NCA and TABM.
11

(a) Inference CPU time vs. cells (b) Peak inference RAM vs. cells
Figure 13: Log axes. Lines are interpolated second-order polynomials.
The plot shows how a model’s peak RAM and consumed CPU seconds during inference scales
with the size of the dataset. We see TICL and TABPFN consumes far more compute then any
other model during inference. Their peak RAM usage also scale with dataset size worse then
any other model.
Figure 14: Relative change in log-loss per calibration method across models.
12

In aggregate across all; beta, platt and venn abers are the only calibration methods, among
those explored, with an expected improvement in log-loss. Isotonic is expected to slightly
increase log-loss while pearsonify markedly increases it. Venn abers is excepted to decrease
log-loss the most with −14.17% followed by beta calibration at −13.7% then platt at −9.75%.
Beta improves log-loss most frequently at 67.1% of instances, followed by venn abers at 63.2%.
Platt appears to be much of a coin toss at 49.8%. But venn abers has less instances of extreme
degradation in log-loss, and slightly more instances of extreme improvement.
Figure 15: Relative change in brier score per calibration method across models.
With regards to brier score all but personify is expected to improve the measure. Venn abers
takes first place with −4.14% followed by beta at −3.91%, then isotonic at −3.74%. Beta
calibration improves the measure most frequently at 57.5% of instances. Venn abers comes
second with 54.2% then isotonic with 52.5%. Again venn abers has fewer instances of extreme
degradation.
13

Figure 16: Relative change in CPU seconds during training per calibration method across models.
Relative change in CPU costs during training has been heavily tainted by outliers. We’ll return
to costs later but note for now that these plots are aggregated across all models but there is
high inter-model variance. For example, AVG has the lowest training compute costs, and these
post-hoc calibration methods significantly increase these costs relative to the base case. Also
TICL and TABPFN which have massive inference costs do not lend themselves to post-hoc
calibration as this necessitates an inference step on the held-out calibration set during training.
14

Figure 17: Relative change in peak RAM during training per calibration method across models.
All methods are relatively in-line when it comes to their effect on peak RAM during training.
Theyallapproximatelydoubled themaximumRAM consumptionduringtraininginexpectation.
15

Figure 18: Relative change in CPU seconds during inference per calibration method across models.
We see that venn abers and platt increase inference compute costs significantly, while the
remaining methods are expected to decrease it. Venn abers is expected to increase inference
time CPU seconds by 139.5% and platt by 47.1%. While beta, isotonic and pearsonify are
expected to decrease the measure by respectively −0.42%, −0.931% and −2.5%.
16

Figure 19: Relative change in peak RAM during inference per calibration method across models.
All methods are relatively in-line when it comes to their effect on peak RAM during inference.
They all approximately increase the maximum RAM consumption during inference by some
percentage points in expectation.
17

Figure 20: Relative change in AUC ROC per calibration method across models.
Only beta is expected to improve AUC ROC by 0.062%. All other are expected to degrade the
measure by less then a percentage point. Notice that venn abers has less instances of extreme
degradation. But all methods degrade the measure more frequently then they improve it.
18

Figure 21: Relative change in accuracy per calibration method across models.
All methods but pearsonify is expected to improve accuracy 3. The effect is marginal, and the
highest expectation is 0.008%.
Moving on to inter-model variance, in appendix A we find the expected ranking per architecture
by log-loss. We find models which rank ahead of their calibrated counterparts such as TICL,
CB and EBM. These models seldom reap benefit from post-hoc calibration in terms of log-loss.
However, TABPFN with beta calibration rank ahead of it’s uncalibrated counterpart. Note,
when applying post-hoc calibration two things change. The base model is trained on a smaller
set since a calibration set is held out. Then the model’s inferred class score is altered by the
calibrator. There is therefore an issue of attributing performance changes between a reduced
training set and the calibrator.
3Remember, the decision boundary is kept constant at 0.5 in the base case and after a calibration method is
used.
19

(a) LDA (b) CB
Figure 22: Relative change in log-loss per calibration method for LDA and CB
To further illustrate high inter-model variance we observe the contrast the effect of calibration
on log-loss between LDA and CB. We see calibration generally improves log-loss for LDA but
degrades it for CB.
(a) TICL (b) CB
Figure 23: Relative change in CPU seconds consumed during training per calibration method for TICL
and CB
We also observe high inter-model variance in the effect on training time compute. TICL’s
20

computeconsumptionismassivelydegradedbypost-hoccalibrationduetotheinherentinference
step. While CB’s compute consumption is often improved due to savings from a smaller training
set often outweighing the added cost of calibration.
3 Conclusion
Overall, we recommend Beta calibration and Venn–Abers predictors as sensible starting points
for practitioners considering post-hoc calibration on tabular binary classification tasks. Across
models and datasets, these two methods most consistently improve calibration relative to out-
of-the-box baselines. However, post-hoc calibration is not guaranteed to improve performance,
particularly for already strong predictors such as TICL, CatBoost, and EBM, where calibration
or proper scoring performance can remain unchanged or degrade.
When improvements occur, they are typically accompanied by additional computational cost.
Beta calibration and Venn–Abers predictors generally increase compute and memory usage
during both training and inference, with the effect usually more pronounced during training.
This trade-off raises a practical question of whether available resources might be more effectively
allocated to stronger base architectures, additional data, or improved validation and feature
engineering rather than post-hoc calibration.
Finally, while calibration quality can change substantially, overall discrimination and classifica-
tion performance are often preserved, as reflected in relatively stable AUC-ROC and accuracy.
These findings highlight that the benefits of post-hoc calibration are strongly dependent on the
underlying model, dataset, and resource constraints, and should therefore be evaluated on a
case-by-case basis prior to deployment.
4 Foundation and ideas
4.1 Supervised k-class classification
A supervised k-class classification problem on tabular data is the task of finding the optimal
function f : X → Y, given a tabular dataset T = {(x ,y )}N ⊂ X ×Y. f is an element in the
i i i=1
infinite set of functions from X to Y, f ∈ F(X,Y), where f(x) = yˆ. Optimum is defined as the
extremum of a performance measure over the function space, given a dataset, often formulated
as the global minimum of a loss function over F(X,Y). (Shalev-Shwartz and Ben-David, 2014)
X is the domain set or the instance space where x ∈ X and x ∈ Rn. x is then a vector with n
dimensions. While, Y is the label set where y ∈ Y and Y = {1,2,··· ,k}. In Binary problems,
k = 2 and Y = {0,1}. (Shalev-Shwartz and Ben-David, 2014)
T is assumed under I.I.D. to have been generated by the joint probability distribution D. Each
row (x ,y ) is then viewed as an independent sample from a multivariate random variable
i i
distributed as D, which implies that D has a functional form d which is the true probability
21

| density | function. (Shaker | and Hüllermeier, |     | 2025) |     |
| ------- | ----------------- | ---------------- | --- | ----- | --- |
The I.I.D. assumption for a dataset T is not guaranteed. When we generate synthetic data by
sampling a multivariate random variable, we can enforce independence and identical distribution,
or deliberately violate it. In contrast, with real-world data we lack access to the true generative
process, so we cannot confirm those assumptions, though we can justify them. As a result, you
must always justify an I.I.D. assumption and be conscious of potential distributional shifts in
| the future. | (Gardner | et al., 2023) |     |     |     |
| ----------- | -------- | ------------- | --- | --- | --- |
f seldom maps onto Y "directly", and a common component function has the standard k-1
| dimensional | probability | simplex | as codomain: |                |     |
| ----------- | ----------- | ------- | ------------ | -------------- | --- |
|             |             |         |              | f : X → ∆k     |     |
|             |             |         |              | f(x) = yˆ      |     |
|             |             |         | yˆ =         | [p , p , ··· , | p ] |
|             |             |         |              | 1 2            | k   |
Note, in binary scenarios many methods operate on the positive class’ score , instead of the
p
1
vector since the score of the negative class is always and the class’ encoding is 0.
| yˆ           |               |     |     | p   | 1−p |
| ------------ | ------------- | --- | --- | --- | --- |
|              |               |     |     | 0   | 1   |
| (Silva Filho | et al., 2023) |     |     |     |     |
The highest class score p or another function on ∆k determines yˆ (Bayes classifier), such that:
j
∆k
|     |     |     |     | c : → Y   |     |
| --- | --- | --- | --- | --------- | --- |
|     |     |     |     | f = c ◦ f |     |
In industry applications, c ought to maximize expected value (Flores et al., 2025). yˆ is either
"directly" the learner’s output or derived from it’s outputs using a normalization function,
s : O → ∆k (e.g. softmax). O , the output space of the learner, is commonly called logit space
for neural networks, and the normalization function the normalization layer. While for SVMs
and margin classifiers it takes the name margin space or discrimnant-function space.
4.2 Architectures
We explicitly distinguish between a learner / model and an architecture. By learner
or model we mean a self-contained procedure (e.g., CatBoostClassifier) that, given training
data T, produces a function f. The learner excludes pre-/post-processing, feature selection,
hyperparameter search, sampling strategies, ensembling, etc., unless those steps are contained
withintheprocedureitself. Anarchitectureisthecompletecomposition,theend-to-endprocess
that generates f from raw input T, explicitly including learners together with pre-processing,
post-processing, tuning, ensembling, and other procedural components.
Importantly,theprocessthatyieldsfneednotbeginfromscratch,anarchitecturecanincorporate
priors or artifacts (for example, via pre-training, distillation, transfer learning, meta-learning,
continual learning, or by initializing from previously trained components) as part of the end-
22

to-end generation. Beyond continual learning, we might also envision mechanisms that enable
the effective transfer of priors and artifacts across different architectures, such that any newly
instantiated model can inherit or initialize from the accumulated "knowledge" of its predecessors.
This would allow us to capitalize on the compute already expended during prior training, in a
manner reminiscent of Isaac Newton’s famous remark: “If I have seen further, it is by standing
on the shoulders of giants.” In contrast, many models trained purely from scratch begin as
blank slates, and once they complete their task, their acquired "experience" is not natively
passed forward. To overcome this, one could imagine a distributed network of models in which
practitioners retrieve priors from a shared repository to initialize their architectures, and, upon
completing their training or generative process, contribute their own learned experience back
to this network. In doing so, the community could accumulate and transmit knowledge across
generations of architectures, gradually compounding collective progress. Parallels can be drawn
| to the work | of (Cotton, | 2022). |     |     |     |     |
| ----------- | ----------- | ------ | --- | --- | --- | --- |
An architecture is therefore compositional: it integrates all components. For a real-world
example, see Amazon’s Rate Card Transformer (Sreekar et al., 2023); conceptually one can for
| example | write: |           |                    |       |            |     |
| ------- | ------ | --------- | ------------------ | ----- | ---------- | --- |
|         |        | f = Platt | scaling ◦ CatBoost | ◦···◦ | Imputation |     |
The architecture is a higher-level abstraction than a single learner, although in some cases the
learner the entire architecture (e.g., K-NN applied to a clean numeric table). But if you
is
impute missing values before K-NN, then K-NN◦Imputation is the architecture. Thus the
learner/model becomes a component within a broader architecture, while the architecture is the
| top-level | abstraction. |     |     |     |     |     |
| --------- | ------------ | --- | --- | --- | --- | --- |
We’ve observed that components are often chosen or optimized in isolation (pre-processing,
feature engineering, model choice considered separately), that modular approach can miss
important interaction effects. Ideally the full composition f should be treated as a single,
unified function for optimization: joint optimization across stages better captures cross-stage
dependencies and can approach globally optimal solutions instead of settling for a chain of
| locally optimal | choices. |     |     |     |     |     |
| --------------- | -------- | --- | --- | --- | --- | --- |
The architectural abstraction can be extended beyond the modeling pipeline: upstream to
provenance, downstream to making, vertically/horizontally to the
| data |     |     | decision |     |     | computer |
| ---- | --- | --- | -------- | --- | --- | -------- |
platform.
• covers the data collection mechanism, storage and retrieval systems,
| Data | provenance |     |     |     |     |     |
| ---- | ---------- | --- | --- | --- | --- | --- |
and raw signal processing. A medical diagnosis architecture might therefore begin at the
| sensor | level: |            |       |               |                     |     |
| ------ | ------ | ---------- | ----- | ------------- | ------------------- | --- |
|        | K-NN   | Imputation |       | ECG Denoising | Electrode Sampling. |     |
|        | f =    | ◦          | ◦ ··· | ◦             | ◦                   |     |
• Decision making covers the consequences or actions following a classification. Essen-
tially, how they are consumed by business logic or action modules (alerts, treatment
recommendations, automated control). For example, the final decision function g could
23

| be  | written | as  |     |          |                    |         |         |     |
| --- | ------- | --- | --- | -------- | ------------------ | ------- | ------- | --- |
|     |         |     | f = | Diagnose | highest-likelihood |         | disease | ◦ f |
|     |         |     |     |          | Treat said         | disease |         |     |
|     |         |     |     | g        | =                  |         | ◦ f     |     |
• Computer platform denotes the full stack that executes an architecture, from silicon to
system software and network: compute devices (CPUs, GPUs, TPUs, FPGAs, ASICs, and
emerging photonic platforms such as Lightmatter), instruction sets and microarchitectures,
memory and storage hierarchies, NICs and fabric, OS/driver/runtime layers, utility
libraries, protocols, compilers and optimizers (e.g., XLA, LLVM), container/VM layers,
and deployment topology (single node, multi-node cluster, edge, cloud). This dimension
recognizes that architectural behavior and performance are tightly coupled to hardware
| paradigms |     | and | their software | implementations. |     | For | example: |     |
| --------- | --- | --- | -------------- | ---------------- | --- | --- | -------- | --- |
Embar-
– Parallelization efficiency is algorithm- and platform-dependent.
rassingly parallel designs (e.g., many independent ensemble members) can scale
near-linearly on distributed topologies because they require little inter-process com-
munication, while tightly coupled workloads need high-bandwidth, low-latency inter-
|     | connects |     | and communication-aware |     | partitioning. |     |     |     |
| --- | -------- | --- | ----------------------- | --- | ------------- | --- | --- | --- |
– Hardware acceleration targets specific computations and precisions. Dense
linear algebra and matrix-multiply–heavy workloads frequently achieve large (some-
times orders-of-magnitude, under favorable conditions) speedups on accelerators
(GPUs/TPUs) versus CPUs, particularly with large batch sizes, reduced precision
(BF16/FP16/INT8), optimized kernels, and compilation/fusion in the software stack
(BLAS/CUDA/XLA/etc.). Realized gains depend strongly on batch size, memory
|     | bandwidth, |     | numerical | precision, | kernel | fusion, | and the software | stack. |
| --- | ---------- | --- | --------- | ---------- | ------ | ------- | ---------------- | ------ |
– Implementationandruntimeartifactsmateriallyaffectlatencyandthrough-
put. Ahead-of-time compiled implementations (C++, Rust) or well-tuned native
libraries remove interpreter overhead and enable low-level memory/control optimiza-
tions, commonly yielding substantially lower latency than for example Python-level
implementations; the exact factor varies with workload, I/O, and parallelism charac-
teristics.
The architecture thus recursively abstracts all steps from bio-electric signal acquisition to clinical
| treatment | and | the | platform on | which | it operates. |     |     |     |
| --------- | --- | --- | ----------- | ----- | ------------ | --- | --- | --- |
Thisholistic,end-to-endviewextendsbeyondourformulationofasupervisedk-classclassification
problem on tabular data. With this perspective we instead search for optimum (e.g, extremum
24

| of value) | over | the | space of | architectures: |     |       |        |      |        |       |     |     |
| --------- | ---- | --- | -------- | -------------- | --- | ----- | ------ | ---- | ------ | ----- | --- | --- |
|           |      |     | A =      | {F(Ws,I        |     | )×P | | c(f,p) | ≤ C, | f ∈ F, | p ∈ P | }   |     |
t t+δ
Architectures
A =
|     |     |     | W = | Accumulated |     | World        | State | in space | s   | at time | t   |     |
| --- | --- | --- | --- | ----------- | --- | ------------ | ----- | -------- | --- | ------- | --- | --- |
|     |     |     |     |             | I = | Action space | at    | time     | t+δ |         |     |     |
|     |     |     |     |             |     | Computer     |       | platform |     |         |     |     |
P =
|           |     |        | c(f,p)       | ≤ C = | Operates | within     | constraints/requirements |          |     |     |     |     |
| --------- | --- | ------ | ------------ | ----- | -------- | ---------- | ------------------------ | -------- | --- | --- | --- | --- |
| Over time | you | record | observations |       | or       | experience | to                       | generate | f.  |     |     |     |
4.3 Datasets
| We require | a   | dataset | suite; |     |     |     |     |     |     |     |     |     |
| ---------- | --- | ------- | ------ | --- | --- | --- | --- | --- | --- | --- | --- | --- |
N,
|     |     |     |     |     |     | {T l | l,L | ∈   | l ≤ L} |     |     |     |     |
| --- | --- | --- | --- | --- | --- | ---------- | --- | ------ | --- | --- | --- | --- |
thatsufficientlyrepresentthediversityofdatasetsencounteredinpractice. Ideally,thiscollection
should span plausible, real-world characteristics that a practitioner is likely to observe.
Mathematically, the space of all possible datasets is infinite, as each is a member of the
d l
infinite-dimensional space of probability density functions. To make this space tractable, we
identifykeydimensionsalongwhichdatasetstypicallyvary, and construct afinite, representative
benchmark suite by selecting datasets that capture variation along these dimensions.
4.3.1 Synthetic
For synthetic datasets, we can precisely control the data-generating process, allowing us to
systematically explore a wide range of scenarios with diverse statistical properties.
| To generate |     | a synthetic | I.I.D. | dataset |     | we: |     |     |     |     |     |     |
| ----------- | --- | ----------- | ------ | ------- | --- | --- | --- | --- | --- | --- | --- | --- |
T
l
1. Draw N samples from a multivariate random variable distributed as d , which returns T
|          |     | l                |     |     |      |           |     |     |     |     | l   | l   |
| -------- | --- | ---------------- | --- | --- | ---- | --------- | --- | --- | --- | --- | --- | --- |
| 2. Apply |     | a transformation |     | G   | on T | such that | G(T | ) = | T   |     |     |     |
|          |     |                  |     |     |      | l         |     | l   | l   |     |     |     |
ToinfluencethecharacteristicsoftheresultingdatasetT ,onemustthereforevarytheunderlying
l
| density | function | d   | , the transformation |     |     | function | G,  | or both. |     |     |     |     |
| ------- | -------- | --- | -------------------- | --- | --- | -------- | --- | -------- | --- | --- | --- | --- |
l
| Key dimensions |     | along | which | d   | may | vary include: |     |     |     |     |     |     |
| -------------- | --- | ----- | ----- | --- | --- | ------------- | --- | --- | --- | --- | --- | --- |
l
1. Continuity
The distribution may be continuous (e.g., Gaussian) or discrete (e.g., categorical, Poisson).
25

2.
|     | Functional |     | Form |     |     |     |     |     |
| --- | ---------- | --- | ---- | --- | --- | --- | --- | --- |
The distribution may exhibit different structural patterns such as linear, polynomial,
exponential, trigonometric, or piecewise forms governing the relationships among variables.
3.
|     | Tail | Behavior |     |     |     |     |     |     |
| --- | ---- | -------- | --- | --- | --- | --- | --- | --- |
The density may feature heavy-tailed properties, influencing the prevalence of outliers and
|     | extreme | values. |     |     |     |     |     |     |
| --- | ------- | ------- | --- | --- | --- | --- | --- | --- |
4. Heteroskedasticity
The variance of the error term may depend on the values of the independent variables,
|     | affecting |     | the spread | of  | the data. |     |     |     |
| --- | --------- | --- | ---------- | --- | --------- | --- | --- | --- |
5. Multicollinearity
The distribution may induce strong correlations among independent variables.
6.
Endogeneity
The data-generating process may involve correlations between explanatory variables and
|     | the | error | term. |     |     |     |     |     |
| --- | --- | ----- | ----- | --- | --- | --- | --- | --- |
In practice, the density function can be constructed using multivariate parametric families
d
l
(e.g., Gaussian, Student-t), multi-modal distributions (e.g., Gaussian mixtures), copula-based
constructions that combine arbitrary marginal distributions, and nonparametric kernel-based
densities. These methods provide control over the shape and complexity of the underlying
distribution, including the ability to capture complex interactions, skewness, or tail behavior.
The transformation function G can also be varied to simulate real-world data imperfections and
| structure. |     | Key | dimensions | along | which | G may | vary include: |     |
| ---------- | --- | --- | ---------- | ----- | ----- | ----- | ------------- | --- |
1. Noise
Noise can be introduced in several forms such as missing values, corrupted entries, or
artificial interventions. Thereby degrading signal quality and simulating common data
|     | quality    | issues. |            |     |     |     |     |     |
| --- | ---------- | ------- | ---------- | --- | --- | --- | --- | --- |
|     | 2. Feature |         | Alteration |     |     |     |     |     |
Irrelevant features may be introduced, or relevant features may be removed, thereby
altering the feature set in ways that challenge a model’s ability to generalize.
3.
|     | Sporadic |     | Relationships |     |     |     |     |     |
| --- | -------- | --- | ------------- | --- | --- | --- | --- | --- |
Spurious correlations between input variables and the target can be embedded to mimic
|     | coincidental |     | or unstable |     | associations | often | encountered | in practice. |
| --- | ------------ | --- | ----------- | --- | ------------ | ----- | ----------- | ------------ |
Multivariate random variables may model the target variable as continuous. To accommodate
Y
classification models, may discretize the target via binning into ordinal classes, effectively
|              |     |     | G          |      |        |                |      | k   |
| ------------ | --- | --- | ---------- | ---- | ------ | -------------- | ---- | --- |
| transforming |     | a   | regression | task | into a | classification | one. |     |
Several prior works have focused on the design of synthetic benchmark datasets:
26

• (Orzechowski and Moore, 2021) introduced the DIverse and GENerative ML Bench-
mark (DIGEN), which consists of 40 closed-form functions mapping continuous inputs
to binary outputs. These functions were discovered through a heuristic optimization
procedure aimed at maximizing diversity in model performance. The benchmark spans
regimes that are linear, nonlinear, interaction-driven, and noise-dominated.
• (Friedman, 1989) proposed six synthetic classification scenarios. These are all multi-
variate normal distributions with varying mean vectors and covariance matrix structures.
• (Breiman, 1998) designed four synthetic classification problems, namely: waveform,
twonorm, threenorm, and ringnorm. Waveform is generated from a mixture model
involving Gaussian noise and base signals, while two-, three- and ringnorm are constructed
from multivariate normal distributions with varying means and covariances structures.
Threenorm includes a mixture of Gaussians within one class, and ringnorm involves classes
with different variances, making it effectively a mixture scenario as well.
Since our focus is on calibration, an essential requirement for synthetic data is that the true
conditional class probabilities are known. This enables precise evaluation of the extent to which
model-predicted probabilities align with the true data-generating process, thereby supporting
rigorous benchmarking of calibration performance. Notice, that the globally optimal f is the
true conditional probability function dervied from d .
l
4.3.2 Real
Unlike synthetic data, real-world datasets are not under our control with respect to their
data-generating processes. As a result, we must identify and collect datasets that span a variety
of meaningful characteristics.
Real-world tabular datasets can be differentiated along both qualitative and quantitative dimen-
sions (Anonymous):
Qualitative characteristics include:
• Domain origin: The domain from which the dataset arises such as finance, healthcare,
biology, or social sciences.
• Modality: The fundamental form in which real-world phenomena were measured and
digitally represented. Modality describes how observations from the physical world, such
as physiological signals, visual scenes, textual communications, or behavioral interactions
were captured through specific measurement processes and encoded into digital formats.
Examples include:
– Raw Sensor Data: ECG traces, camera images, microphone audio recordings
– Direct Observations: Manually entered fields (patient age, product categories, survey
responses)
27

– System Logs: Transactional records, server logs, clickstream data, audit trails
Modality fundamentally determines the data’s intrinsic characteristics including measurement
units, sampling frequency, spatial/temporal resolution, file formats, noise patterns, and typical
missingness mechanisms. These properties in turn dictate the appropriate modeling approaches.
Crucially for tabular models: Regardless of original modality, tabular models inherently operate
on numeric matrices and therefore require the original modality to be projected into a numeric
tabular representation through modality specific feature extraction/engineering:
• Sensor/Image/Audio Data: Extracting summary statistics, spectral features or pre-trained
embeddings. Such as (Dosovitskiy et al., 2020).
• Text Data: Text extracted via OCR: computing bag-of-words representations, TF-IDF
scores, contextualized embeddings or embeddings from NLP models.
• Logs/Transactions: Aggregatingcounts,calculatingtemporaldeltas,constructinguser/item
profiles
• Categorical Data: Applying encodings such as one-hot, target encoding, or learned
embeddings
Note, that there are models natively capable of operating on multiple modalities such as those
found in pytorch-widedeep (Zaurin and Mulinka, 2023). Bypassing a tabular representation
entirely may also result in higher performance (Akhauri et al., 2025).
Quantitative characteristics include:
• Class imbalance: The distribution of class labels may be skewed.
• Noise and data quality: Missing values, label noise, or inconsistencies in feature
encoding.
• Data scale and types: Datasets may vary in the number of instances, dimensionality,
and the nature of features (e.g., continuous, categorical, ordinal).
• Difficulty: Certain datasets consistently produce lower predictive performance across
models, suggesting inherent complexity or noisiness. These are often referred to as “hard”
datasets.
Distributional shifts such as temporal or domain shifts can also affect calibration, though we
omit these in this study to maintain an I.I.D. assumption throughout.
Quantitative properties can also be systematically extracted through automated tools such
as the metadata extraction framework for tabular data called pymfe (Alcobaca et al., 2020).
Notably, the characteristics listed above overlap with the design dimensions considered for
synthetic datasets.
28

A number of real-world dataset benchmarks have been developed for general-purpose bench-
marking:
• OpenML-CC18 (Bischl et al., 2021): A curated collection of 72 classification datasets
| from | varied | domains | such | as finance, |     | medicine and | manufacturing. |
| ---- | ------ | ------- | ---- | ----------- | --- | ------------ | -------------- |
• TabZilla-Hard Benchmark (McElfresh et al., 2024): A set of 36 tabular datasets
identified as consistently challenging across a range of machine learning models.
• 2022): A benchmark of 45 datasets from varied domains sourced
| (Grinsztajn |      | et      | al., |     |     |     |     |
| ----------- | ---- | ------- | ---- | --- | --- | --- | --- |
| primarily   | from | OpenML. |      |     |     |     |     |
• AutoML Benchmark (Gijsbers et al., 2023): Introduced the benchmark AMLB, a com-
prehensive suite of datasets from OpenML. The classification suite include 71 classification
| tasks | from | various | domains. |     |     |     |     |
| ----- | ---- | ------- | -------- | --- | --- | --- | --- |
Although these datasets are widely used, recent critiques, such as those presented by (Tschalzev
etal.,2025)highlightconcernsprimarilyrelatedtomethodologicalrigorandexperimentaldesign,
and some flaws in the suites themselves. Consequently, while these benchmarks remain valuable
resources, their use should be accompanied by thoughtful dataset selection and appropriate
| methodological | design. |     |     |     |     |     |     |
| -------------- | ------- | --- | --- | --- | --- | --- | --- |
Luckily, (Erickson et al., 2025) introduced "Tabarena-v0.1", an open-source and maintained
benchmark which includes a suite of 38 versioned, curated tabular classification tasks. These
were generated by filtering 1053 datasets from 13 prior benchmark studies (Including all the
aforementioned suites). The suite contains datasets from domains such as finance, chemistry,
physics, healthcare, and marketing. The filters applied to the original datasets include:
| •   | datasets: |     | No  | duplication | of  | datasets. |     |
| --- | --------- | --- | --- | ----------- | --- | --------- | --- |
Unique
| •   |     | Data: | The | datasets | must | be I.I.D. |     |
| --- | --- | ----- | --- | -------- | ---- | --------- | --- |
IID Tabular
• Tabular modality: Exclude datasets which originate from a modality/application where
| tabular | models | aren’t |     | among the | primary | architectures. |     |
| ------- | ------ | ------ | --- | --------- | ------- | -------------- | --- |
• Distribution: The dataset must originate from a real random process.
Real Random
| No synthethic |     | data. |     |     |     |     |     |
| ------------- | --- | ----- | --- | --- | --- | --- | --- |
• Predictive Machine Learning Task: Exclude datasets which do not stem from a
| predictive |     | machine | learning | task. |     |     |     |
| ---------- | --- | ------- | -------- | ----- | --- | --- | --- |
• Size Limit: Exclude datasets with less then 500 or more then 250 000 samples.
• Quality: Exclude heavily preprocessed datasets, datasets with inadequate docu-
Data
mentation on origin/pre-processing and datasets with an irreversible target leak.
• No License Issues: Exclude any dataset whose license does not allow for use in an
| academic | benchmark. |     |     |     |     |     |     |
| -------- | ---------- | --- | --- | --- | --- | --- | --- |
29

|     | •           |            |            |      |        |            | API: | Exclude | any datasets | which cannot | be automati- |
| --- | ----------- | ---------- | ---------- | ---- | ------ | ---------- | ---- | ------- | ------------ | ------------ | ------------ |
|     | Open-access |            | Structured |      |        | Data       |      |         |              |              |              |
|     | cally       | downloaded |            | from | a data | repository |      | with    | structured   | metadata.    |              |
• Tasks: Exclude datasets with tasks that pose ethical concerns
|     | Ethically |     | Unambiguous |     |     |     |     |     |     |     |     |
| --- | --------- | --- | ----------- | --- | --- | --- | --- | --- | --- | --- | --- |
4.4 Models
As formerly mentioned, our focus is on calibration methods applicable to popular machine
learningmodels. Todeterminewhichmethodsarepopularamongpractitioners,we’vesynthesized
results from surveys addressing usage among practitioners, literature reviews, and studies where
| machine |     | learning | is applied |     | to a | problem | within | a   | domain. |     |     |
| ------- | --- | -------- | ---------- | --- | ---- | ------- | ------ | --- | ------- | --- | --- |
Overall practitioners appear to use a mixture of classical-, tree based-, and neural network
models, in addition to AutoML. Regression models are sometimes extended to binary problems.
Binary models are usually extended to the multi-class setting using "one vs. all" or "one vs.
one". Models are also ensembled using bagging, boosting, routing/gating (Mixture of Experts),
| and | stacking    | (Jurek  | et     | al.,     | 2014). |       |     |     |     |     |     |
| --- | ----------- | ------- | ------ | -------- | ------ | ----- | --- | --- | --- | --- | --- |
|     | • Classical |         | models |          |        |       |     |     |     |     |     |
|     |             | Support | vector | Machines |        | (SVM) |     |     |     |     |     |
–
|     | –   | Logistic   | regression   |          | (LR)     |      |       |     |     |     |     |
| --- | --- | ---------- | ------------ | -------- | -------- | ---- | ----- | --- | --- | --- | --- |
|     | –   | Bayesian   | approaches   |          |          |      |       |     |     |     |     |
|     |     | ∗ Naive    |              | Bayes    | (NB)     |      |       |     |     |     |     |
|     |     | ∗ Bayesian |              | Networks |          | (BN) |       |     |     |     |     |
|     | –   | Linear     | discriminant |          | analysis |      | (LDA) |     |     |     |     |
|     |     | Similarity |              | search   |          |      |       |     |     |     |     |
–
|     |        | ∗ K      | Nearest | Neighbors |      | (K-NN) |     |     |     |     |     |
| --- | ------ | -------- | ------- | --------- | ---- | ------ | --- | --- | --- | --- | --- |
|     |        | ∗ Radius |         | Neighbors |      | (R-N)  |     |     |     |     |     |
|     | • Tree | models   |         |           |      |        |     |     |     |     |     |
|     |        | Random   | Forest  |           | (RF) |        |     |     |     |     |     |
–
|     | –   | CatBoost | (CB)  |        |     |     |     |     |     |     |     |
| --- | --- | -------- | ----- | ------ | --- | --- | --- | --- | --- | --- | --- |
|     | –   | XGBoost  | (XGB) |        |     |     |     |     |     |     |     |
|     |     | LightGBM |       | (LGBM) |     |     |     |     |     |     |     |
–
|     | • Artificial |               | Neural | Networks |          |          |                |     |     |     |     |
| --- | ------------ | ------------- | ------ | -------- | -------- | -------- | -------------- | --- | --- | --- | --- |
|     | –            | Convolutional |        | neural   |          | networks | (CNN)          |     |     |     |     |
|     | –            | Deep          | neural | networks |          | (DNN)    |                |     |     |     |     |
|     |              | ∗ Transformer |        |          | networks |          | (Transformers) |     |     |     |     |
30

|     | Recurrent | neural networks | (RNN) |
| --- | --------- | --------------- | ----- |
–
|     | Feedforward | neural networks | (FNN) |
| --- | ----------- | --------------- | ----- |
–
|     | ∗ Multilayer    | perceptron      | (MLP)          |
| --- | --------------- | --------------- | -------------- |
|     | ∗ Probabilistic | neural          | networks (PNN) |
|     | Graph           | neural networks | (GNN)          |
–
|     | – Topological | neural networks | (TNN) |
| --- | ------------- | --------------- | ----- |
|     | – Foundation  | models (FM)     |       |
• AutoML
AutoGluon
–
|     | – Google | cloud AutoML |     |
| --- | -------- | ------------ | --- |
– AWS Sagemaker
Note that there are many more methods which do not neatly fall into these categories such
as GANs, evolutionary approaches, fitting multivariate random variables, Non-hierarchical
clustering and so on. But we’ll not address these due to their lacking popularity, which do not
| necessarily | speak | of their potential. |     |
| ----------- | ----- | ------------------- | --- |
Kaggle’s "state of data science and machine learning" surveys provide an initial view of current
practice. In 2021 and 2022, the surveys collected approximately 25 000 responses, of which the
data from approximately 2000 respondents that report a job title of "data scientist" are used.
The 2021 survey shows that the most commonly used methods are: linear or logistic regression,
tree-based methods (RF, XGBoost,CatBoost, and LightGBM), CNNs, Bayesian approaches,
DNNs, RNNs, transformernetworks, GANsandevolutionaryapproaches(2021). Theseareoften
implemented within the frameworks: Scikit-learn, TensorFlow/Keras, pytorch/lightning/fast.ai,
or the framework specific to the model as for XGBoost and CatBoost (2022). The 2021 study
also showed an increased usage of AutoML solutions such as Google’s cloud AutoML offering
| (2021). | (Kaggle, 2021, | 2022) |     |
| ------- | -------------- | ----- | --- |
Literaturereviewsalsoshowsimilarresults. Inmarketing, Bayesianapproaches, neuralnetworks,
LDA, tree-based methods, SVM, Non-Hierarhical clustering, ensambles, and K-NN are in use
(Duarte et al., 2022). In chemistry, we’ve seen tree-based methods and neural networks such as
FNNs, CNNs, RNNs, GNNs and TNNs (Shi et al., 2023). In stellar astronomy we see neural
networks (ANNs, MLP, CNNs, RNNs, PNNs), tree based methods, SVM, K-NN and Bayesian
methods, in addition to fitting multivariate random variables (Li et al., 2025). In opinion mining
and sentiment analysis we see Naïve Bayes, Bayesian network, Maximum entropy, SVM, Neural
network, KNN, decision trees, and rules based models (Hemmatian and Sohrabi, 2019). While
in ecology we see LDA, a consensus of binomial logistic regression, multinomial regression and
SVM, tree-based methods, and Stagewise Additive Modelling using a Multi-class Exponential
| (SAMME) | loss function | (Bourel and | Segura, 2018). |
| ------- | ------------- | ----------- | -------------- |
31

Then there’s the studies which aim to catalog methods, which highlight decision trees, Bayesian
classification, Rule based classification, SVM, Association rule mining and backpropagation
(Neural Networks), K-NN, Case Based Reasoning, genetic algorithms, fuzzy logic and Rough
Set Approach (Paul and Kumar, 2020). Furthermore in "An overview of machine learning
classification techniques" they highlight NB, decision trees, LDA, Logistic regression, K-NN,
SVM, and Neural networks (Alnuaimi, Amer F.A.H. and Albaldawi, Tasnim H.K., 2024).
Lastly in "Benchmarking AutoML for regression tasks on small tabular data in materials design"
they present SVM, decision trees, BNN (Bagged NN), GBNN (Gradient Boosted NN), WBNN
(Wavelet Bagged NN), WGBNN (Wavelet Gradient Boosted NN), and a plethora of AutoML
solutions (Conrad et al., 2022).
4.5 Calibration methods
To obtain a well-calibrated function f, we’ve identified two main methods:
1. Model selection
Model selection pertains to the choice of learner, including it’s hyperparameters. We
consider the choice of loss function as a hyperparameter. Certain models have been
shown to generally achieve higher degrees of calibration out of the box. Additionally
hyperparameter optimization has been shown to improve calibration. (Boström, 2008)
2. Post-processing
Post-processing pertains to any manipulation of the learners output. Such as the normal-
ization function, which maps a learners output onto the probability simplex, or post-hoc
calibration which maps from simplex to simplex. (Silva Filho et al., 2023)
However, recall that the global optimum is best approximated when the entire architecture is
optimized as one. Therefore we won’t disregard the potential effects of pre-processing techniques
or other components, and highlight that under- and over-sampling techniques have been shown
to hurt calibration (Carriero et al., 2025). Additionally, combining calibration methods such as
hyperparameter tuning and post-hoc calibration techniques have been shown to create solutions
better then each technique in isolation (Boström, 2008). Initially, we’ll only consider post-hoc
calibration methods.
4.5.1 Post-hoc calibration
Post-hoc calibration is the procedure of estimating a function p where h is a learner such that:
p : ∆k → ∆k
f = p ◦ h
We restrict attention to model-agnostic post-hoc calibration methods while acknowledging that
32

many model-specific approaches also exist. For empirical evaluation we selected five calibrators
from the catalog in (Manokhin): Isotonic regression, Platt scaling, Beta calibration, Venn-Abers
| predictors, |     | and Pearsonify |     | (a  | recently proposed | method). |     |     |     |     |
| ----------- | --- | -------------- | --- | --- | ----------------- | -------- | --- | --- | --- | --- |
Other methods The literature contains a very large and heterogeneous set of alternatives;
the list below samples representative families to illustrate the breadth of choices (see (Manokhin)
| for | a more    | comprehensive   |           | catalog):   |          |             |          |                           |            |             |
| --- | --------- | --------------- | --------- | ----------- | -------- | ----------- | -------- | ------------------------- | ---------- | ----------- |
|     | •         |                 |           |             |          | empirical   | binning, | binning                   | averaging, | and related |
|     | Binning   | and             | histogram |             | methods: |             |          |                           |            |             |
|     | piecewise | constant        |           | estimators. |          |             |          |                           |            |             |
|     | •         |                 |           |             | Bayesian | calibration |          | maps and Gaussian-process |            | models      |
|     | Bayesian  |                 | / GP      | approaches: |          |             |          |                           |            |             |
|     | of        | the calibration |           | function.   |          |             |          |                           |            |             |
• Tree and ensemble methods: probability calibration trees, modified logistic model
trees, nested dichotomies, and ensemble combinations of scaling and binning.
• Loss / regularization based: entropy penalties, label smoothing, focal loss, and other
|     | objective | modifications |     |     | that alter probabilistic |     | outputs. |     |     |     |
| --- | --------- | ------------- | --- | --- | ------------------------ | --- | -------- | --- | --- | --- |
• Platt-style sigmoids, exponential fits, polynomials (including
|     | Parametric            |                | function |            | fits:          |           |            |             |     |                 |
| --- | --------------------- | -------------- | -------- | ---------- | -------------- | --------- | ---------- | ----------- | --- | --------------- |
|     | constrained/monotonic |                |          |            | variants), and | other     | parametric | transforms. |     |                 |
|     | •                     |                |          |            |                |           |            | Venn-Abers  | and | related confor- |
|     | Venn                  | / interval     |          | predictors | and            | conformal | variants:  |             |     |                 |
|     | mal/Venn              | constructions. |          |            |                |           |            |             |     |                 |
• Hybrid and combined strategies: mixtures or pipelines that apply scaling, binning,
|     | and | ensembling | in  | sequence. |     |     |     |     |     |     |
| --- | --- | ---------- | --- | --------- | --- | --- | --- | --- | --- | --- |
• Multiclass-specific methods: temperature (softmax) scaling, vector/matrix scaling,
|     | Dirichlet | calibration, |     | etc. |     |     |     |     |     |     |
| --- | --------- | ------------ | --- | ---- | --- | --- | --- | --- | --- | --- |
This diversity means practitioners face many valid, but different, calibration choices; our study
| focuses |         | on a small | popular | set.   |            |            |     |     |     |     |
| ------- | ------- | ---------- | ------- | ------ | ---------- | ---------- | --- | --- | --- | --- |
| Platt   | scaling | /          | Platt’s | method | / Logistic | regression |     |     |     |     |
Platt scaling fits a sigmoid (logistic) transform to a classifier’s raw scores, producing calibrated
| probabilities |     | of the | form |     |     |     |     |     |     |     |
| ------------- | --- | ------ | ---- | --- | --- | --- | --- | --- | --- | --- |
1
|     |     |     |     |     | pˆ= |     |     | ,   |     |     |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
1+exp(A·s+B)
where is the uncalibrated score and are fit on a held-out calibration set (usually by
|     | s   |     |     |     | A,B |     |     |     |     |     |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
maximum likelihood). Implementations are widely available (e.g., scikit-learn). (scikit-learn
| developers, |     | 2025b) |     |     |     |     |     |     |     |     |
| ----------- | --- | ------ | --- | --- | --- | --- | --- | --- | --- | --- |
33

Isotonic regression / ROC convex hull method
Isotonic regression is a nonparametric, monotone mapping from scores to probabilities estimated
by pool-adjacent-violators (PAV). It makes minimal functional assumptions (only monotonicity).
Variants and related techniques (e.g., ROC convex-hull based adjustments) use piecewise-
constant monotone fits to enforce consistency with empirical ROC orderings. (scikit-learn
developers, 2025a)
Beta calibration
Beta calibration is a post-hoc, parametric method for binary classifiers that generalizes Platt
scaling by fitting a Beta distribution to map scores to probabilities (Kull et al., 2017). The
implementation provides three variants for parameter estimation; in our experiments we used
the abm setting, which fits all three parameters of the Beta model.
Venn-abers predictors
Venn-Abers predictors are conformal-prediction-based post-hoc calibration methods for classifi-
cation that produces *valid probabilistic estimates* by leveraging the validity guarantees of
Venn predictors. Given a scoring classifier and a held-out calibration set, Venn-Abers fits two
isotonic regression models; one assuming the test instance belongs to class 0 and one assuming
it belongs to class 1. Yielding a pair of calibrated probabilities (p ,p ) that form a prediction
0 1
interval for the likelihood of the positive class. This interval reflects uncertainty in the calibrated
estimate and is guaranteed to contain the true probability under standard I.I.D. assumptions .
In practice, this interval is often converted to a single point estimate for decision making using
the formula
p
1
pˆ = ,
VA
1−p +p
0 1
which balances the lower and upper bounds into a single calibrated probability. Venn-Abers thus
combines distribution-free calibration guarantees with isotonic regression flexibility, providing
an alternative to standard post-hoc methods like Platt scaling or single isotonic regression. The
implementation we adopted follows the method described in (Vovk et al., 2015).
Pearsonify
Pearsonify is a lightweight, model-agnostic Python package for generating classification intervals
around predicted probabilities in binary classification tasks (xRiskLab, 2025). It combines
principles from Pearson residuals, a classical statistical measure of goodness-of-fit, with confor-
mal prediction to quantify uncertainty in probability estimates without strong distributional
assumptions. Given a base probabilistic classifier and a calibration set, Pearsonify produces
calibrated lower and upper interval bounds around predicted class probabilities that reflect
uncertainty due to limited data and model error; these intervals can then be converted into
single point estimates when required.
34

4.6 Performance
The performance of an architecture is a weighted sum or linear combination of its facets. Facets
are dimensions or aspects of performance that together determine how well it serves its intended
purpose.
Φ = a ϕ +a ϕ +···+a ϕ
1 1 2 2 r r
Whileperformanceisoftenreducedtoasinglefacet, suchasthevalueofalossfunction, accuracy
or ROC-AUC, this simplification, though convenient, can obscure important considerations.
For instance, cost is an ever-present constraint; few, if any, applications operate with unlimited
resources. Latency is another context-dependent concern, some systems require millisecond-level
responsiveness, while others can afford to run for hours. Though the relevant facets are highly
dependent on context, some are archetypical and recur across applications. These include,
among other things, predictive or classification ability, discriminatory ability, calibration, and
financial impact. Each facet should be quantitatively assessed, yet it is essential to distinguish
between the measure used and the concept it aims to capture. The full performance of an
architecture is thus best understood as a multi-dimensional construct, shaped by context and
by trade-offs between competing goals.
A critical pitfall of reducing performance assessment to a single facet is the emergence of trivial
solutions that exploit the narrow definition of success. For instance, a system can trivially
achieve zero latency and cost by estimating f as a constant function, completely bypassing
computation. Similarly, perfect calibration can be achieved by always predicting the empirical
class frequencies (ECE), independent of the input (Pavlovic, 2025). While technically optimal
under their respective measures, such solutions are useless in practice. Even improvements in
widelyvaluedmetricslikeaccuracyorROC-AUCmaycomeatunacceptablecostsinotherfacets,
such as significant increases in computational load, or inference time. These considerations
highlight the importance of assessing performance holistically, rather than optimizing for a
single dimension in isolation. While it is often necessary to prioritize specific facets, doing so
without considering others can lead to systems that are optimal in theory but impractical in
deployment.
Another important yet frequently overlooked facet is operational complexity, which captures how
well a method performs in real-world deployment scenarios from an operational point of view.
This includes considerations such as runtime stability, robustness to data distribution shifts,
susceptibility to technical debt, and ease of integration into existing systems. A method with
high operational ease is one that is fast, stable over time, interpretable, and minimally prone to
maintenance issues or performance degradation. Thus, a complete evaluation of performance
should account for a method’s fitness for production, not just its theoretical or test-set behavior.
It may also be critical to evaluate when f performs well and therefore measure performance
under predefined scenarios, or explain differences in performance between scenarios. One could
ask whether the f generalizes to out-of-distribution data? How well does it extrapolate and
interpolate? Does it perform in sparse vector space or only in dense regions? Does it require
large volumes of data to function reliably? In industry, our desire to estimate an optimal f
35

frequently arises due to the potential value generated by improving the assignment of new
unobserved instances to its class. By using instead of some alternative we stand to potentially
f
reap some value gain. Inherently, the generalization of or it’s out-of-sample performance
f
becomes paramount. More abstractly it’s the performance in production we desire an estimated
measure of, which ought to reflect itself in the evaluation strategy by for example ensuring
that the discrepancy between train and test sets represent the discrepancy between train and
| live-production      | instances. |     |     |     |
| -------------------- | ---------- | --- | --- | --- |
| 4.6.1 Classification | ability    |     |     |     |
With classification ability or predictive ability, we refer to an architecture’s ability to correctly
assign a class to an instance. To illustrate, we look towards the binary confusion matrix,
which designates an output of f aka. yˆ as a TP, FN, FP, or TN depending on the true y.
(GeeksforGeeks)
| \   | Predicted | Positive | Predicted Negative |     |
| --- | --------- | -------- | ------------------ | --- |
y yˆ
| Actual Positive | True Positive  | (TP) | False Negative | (FN) |
| --------------- | -------------- | ---- | -------------- | ---- |
| Actual Negative | False Positive | (FP) | True Negative  | (TN) |
TP + TN is therefore the count of correct predictions, FN the count of negative predictions
when the true class is positive and so on. From these counts we derive the metrics: Accuracy,
| Recall, Precision, | and F1 Score | which we define | below: |     |
| ------------------ | ------------ | --------------- | ------ | --- |
TP +TN
Accuracy =
TP +TN +FP +FN
TP
|     |     | Precision | =   |     |
| --- | --- | --------- | --- | --- |
TP +FP
TP
|     |     | Recall = |     |     |
| --- | --- | -------- | --- | --- |
TP +FN
2·Precision∗Recall
F1 Score =
Precision+Recall
To visualize overall predictive performance Murphy curves have been suggested (Dimitriadis
et al., 2023).
| 4.6.2 Discriminatory | ability |     |     |     |
| -------------------- | ------- | --- | --- | --- |
Discriminatory ability relates to "what extent the forecast values distinguish situations with
lower or higher true event probabilities". It is therefore the order of classes by score values
which is evaluted. To measure discrimination ROC-AUC has been suggested. (Dimitriadis et al.,
2023)
In the binary case, ROC-AUC is the area under the receiver operating characteristic (ROC)
curve, which plots TP against FP for all decision boundaries between 0 and 1. According to
Dimitriadis et. al. "Since the ROC curve is invariant under strictly increasing transformations of
36

the forecast values, it diagnoses discrimination ability only, while ignoring issues of calibration."
| (Dimitriadis | et al., 2023) |     |     |     |     |
| ------------ | ------------- | --- | --- | --- | --- |
4.6.3 Calibration
Calibration is a facet of performance, with varying definitions and measures. Generally, the
concept concerns itself with the degree of which class scores are actual probabilities, in a
frequenist statistical sense. A class score of 0.8 is considered calibrated if the instance belongs
to the given class 80% of the time when such a score is given. Intuitively, it is therefore the
degree of which the vector yˆ = [p , p , ··· , p ] is a probability vector. (Pavlovic, 2025)
|     |     |     | 1 2 | k   |     |
| --- | --- | --- | --- | --- | --- |
There are multiple ways of formally defining calibration, which vary by the strictness or strength
of the definition. We’ll consider three alternative definitions: instance-wise, multi-class and
class-wise calibration, and corresponding measurements. (Shaker and Hüllermeier, 2025)
RecallthatundertheI.I.D.assumption,eachrow(x ,y )ofT isviewedasanindependentsample
i i
from a random variable distributed as D. This implies the existence of marginal distributions
and the conditional probability of class j given instance x, P(Y = j | X = x). f is then
| considered | instance-wise | calibrated | when:   |         |      |
| ---------- | ------------- | ---------- | ------- | ------- | ---- |
|            |               |            | p = P(Y | = j | X | = x) |
j
|     |     |     |     | ∀ j ∈ Y |     |
| --- | --- | --- | --- | ------- | --- |
|     |     |     |     | ∀ x ∈ X |     |
In other words, f is truly instance-wise calibrated when it is the true conditional probability
function. To measure instance-wise calibration we can use the mean Brier score, Spiegelhalter Z-
statistic and mean Log-loss. Brier score and Log-loss are strictly proper scoring rules (Silva Filho
et al., 2023). These two measures are therefore uniquely minimized by the true probabilities.
The Brier score is calculated per row ), and then averaged across the rows MBS(T).
BS(yˆ ,q
|     |     |     |     | i i |     |
| --- | --- | --- | --- | --- | --- |
k
(cid:88)
|     |     |     | BS(yˆ ,q | ) = (p | −q )2 |
| --- | --- | --- | -------- | ------ | ----- |
|     |     |     | i i      | j      | j     |
j=1
N
1 (cid:88)
|     |     |     | MBS(T) = | BS(yˆ | ,q ) |
| --- | --- | --- | -------- | ----- | ---- |
i i
N
i=1
|     |     |     | f(x | ) = yˆ |     |
| --- | --- | --- | --- | ------ | --- |
i i
|     |     |     |     | q ∈ ∆k |     |
| --- | --- | --- | --- | ------ | --- |
i
|     |     |     |     | q ∈ q |     |
| --- | --- | --- | --- | ----- | --- |
j i
| When D | is known q | can be derived | as: |     |     |
| ------ | ---------- | -------------- | --- | --- | --- |
i
|     |     |     | q (j) = P(Y | = j | X   | = x )   |
| --- | --- | --- | ----------- | --------- | ------- |
|     |     |     | i           |           | i       |
|     |     |     | q = [q (1), | q (2),··· | ,q (k)] |
|     |     |     | i i         | i         | i       |
37

When is unknown is constructed based on , such that the entry corresponding to class
| D           | q          |     |     | y   |     |     |     | j   |
| ----------- | ---------- | --- | --- | --- | --- | --- | --- | --- |
|             |            | i   |     | i   |     |     |     |     |
| is 1 if and | elsewhere: |     |     |     |     |     |     |     |
| y = j       | 0          |     |     |     |     |     |     |     |
i
|     |     |     | q = [0, | 0,··· , | 1,··· , 0] |     |     |     |
| --- | --- | --- | ------- | ------- | ---------- | --- | --- | --- |
i
Furthermore, in a binary setting the Brier score can be decomposed into a calibration term
and a sharpness/resolution term, where the Spiegelhalter Z-statistic evaluates the calibration
component of the Brier Score. Many argue that the Brier score conflates calibration and
discrimination, whereas Spiegelhalter’s Z focuses purely on calibration. (Spiegelhalter, 1986;
Manokhin, 2025)
yˆ
|     |     | p i = | i [1] ,score | of  | positive class |     |     |     |
| --- | --- | ----- | ------------ | --- | -------------- | --- | --- | --- |
N
1 (cid:88)
|     |     | MBS(T) |     | =   | (y −p )2 |     |     |     |
| --- | --- | ------ | --- | --- | -------- | --- | --- | --- |
i i
N
i=1
|     |        | 1   | N        |           | 1   | N        |     |     |
| --- | ------ | --- | -------- | --------- | --- | -------- | --- | --- |
|     |        |     | (cid:88) |           |     | (cid:88) |     |     |
|     | MBS(T) | =   | (y       | −p )(1−2p | ) + | p (1−p   | )   |     |
|     |        | N   | i        | i         | i N | i        | i   |     |
|     |        |     | i=1      |           |     | i=1      |     |     |
The first term is the calibration term; the last term is the sharpness term.
To derive the Spiegelhalter Z-statistic from this decomposition and the corresponding hypothesis
test, we first assume that under the null hypothesis. Therefore, the null
|     |     | Y ∼ Bernoulli(p |     | )   |     |     |     |     |
| --- | --- | --------------- | --- | --- | --- | --- | --- | --- |
|     |     | i               |     | i   |     |     |     |     |
hypothesis is that the model is calibrated. Under this assumption, these assertions can be
proven true:
|     |     |     |     | E (Y ) = | p   |     |     |     |
| --- | --- | --- | --- | -------- | --- | --- | --- | --- |
|     |     |     |     | 0 i      | i   |     |     |     |
N
1 (cid:88)
|     |     | E 0 | (MBS(T)) | =   | p i (1−p | i ) |     |     |
| --- | --- | --- | -------- | --- | -------- | --- | --- | --- |
N
i=1
N
|     |     |            |     | 1 (cid:88) |          |     |     |     |
| --- | --- | ---------- | --- | ---------- | -------- | --- | --- | --- |
|     |     | V (MBS(T)) | =   | (1−2p      | )2p (1−p | )   |     |     |
|     |     | 0          |     |            | i i      | i   |     |     |
N2
i=1
|     |     | MBS(T) | ∼ N(E | (MBS(T)),V | (MBS(T))) |     |     |     |
| --- | --- | ------ | ----- | ---------- | --------- | --- | --- | --- |
|     |     |        |       | 0          | 0         |     |     |     |
Note that MBS(T) approaches the normal distribution in the limit due to the central limit
38

| theorem. | Furthermore: |     |     |     |     |     |     |     |     |
| -------- | ------------ | --- | --- | --- | --- | --- | --- | --- | --- |
(cid:80)N
|     |     | MBS(T)−E |     |             | 0 (MBS(T)) |     |           | (y i −p i )(1−2p | i )      |
| --- | --- | -------- | --- | ----------- | ---------- | --- | --------- | ---------------- | -------- |
|     | Z   | =        |     |             |            |     | =         | i=1              |          |
|     |     |          |     | (MBS(T))0.5 |            |     | (cid:113) |                  |          |
|     |     |          | V 0 |             |            |     |           | (cid:80)N        |          |
|     |     |          |     |             |            |     |           | (1−2p i )2p i    | (1−p i ) |
i=1
Z ∼ N(0,1)
Where Z is the Spiegelhalter Z-statistic and measures how many standard deviations the brier
score deviates from it’s expectation under perfect calibration. Low |Z| indicates high calibration,
while high |Z| indicates low calibration. By choosing a level of significance we can also perform
| a hypothesis | test | of the | null | hypothesis. |     |     |     |     |     |
| ------------ | ---- | ------ | ---- | ----------- | --- | --- | --- | --- | --- |
An alternative measure is the log-loss (LL) (a.k.a. binary cross-entropy or negative log-
likelihood):
|     |     |     | p   | is the | score | assigned |     | to the true class |     |
| --- | --- | --- | --- | ------ | ----- | -------- | --- | ----------------- | --- |
yi
|     |     |     |     |     | LL(yˆ | ,y i ) | = −log(p | yi ) |     |
| --- | --- | --- | --- | --- | ----- | ------ | -------- | ---- | --- |
i
N
|     |     |     |     |        |     |     | 1 (cid:88) |            |     |
| --- | --- | --- | --- | ------ | --- | --- | ---------- | ---------- | --- |
|     |     |     |     | MLL(T) |     | =   |            | LL(yˆ ,y ) |     |
|     |     |     |     |        |     |     |            | i i        |     |
N
i=1
Log loss heavily penalizes under-confidence in the correct class, since lim −log(x) = ∞. In
x→0
contrast, the Brier score penalizes errors quadratically and does not diverge in the interval [0,1],
| making | it less sensitive |     | to large | deviations. |     |     |     |     |     |
| ------ | ----------------- | --- | -------- | ----------- | --- | --- | --- | --- | --- |
Alternative definitions of calibration do not condition on the instances x but on the class scores
p , this is known as probability-wise calibration. First, we define the space of yˆ and p as:
j j
|     |     |     |     | Yˆ  | = { | yˆ | f(x) | =   | yˆ, x ∈ X} |     |
| --- | --- | --- | --- | --- | --- | --------- | --- | ---------- | --- |
Yˆ}
|           |            |     |                | P   | = {        | p | p | = yˆ[j], | yˆ ∈ |     |
| --------- | ---------- | --- | -------------- | --- | ---------- | ----- | -------- | ---- | --- |
|           |            |     |                | j   |            | j     | j        |      |     |
| f is then | considered | to  | be multi-class |     | calibrated |       | when:    |      |     |
Yˆ
|     |     |     |     |     | p = | P(Y | = j | | = yˆ) |     |
| --- | --- | --- | --- | --- | --- | --- | ----- | ----- | --- |
j
|     |     |     |     |     |     | ∀   | j ∈ Y |     |     |
| --- | --- | --- | --- | --- | --- | --- | ----- | --- | --- |
Yˆ
|         |               |     |     |            |            | ∀   | yˆ ∈    |           |     |
| ------- | ------------- | --- | --- | ---------- | ---------- | --- | ------- | --------- | --- |
| While f | is considered | to  | be  | class-wise | calibrated |     | when:   |           |     |
|         |               |     |     |            | p j =      | P(Y | = j | P | j = p j ) |     |
|         |               |     |     |            |            | ∀   | j ∈ Y   |           |     |
|         |               |     |     |            |            | ∀ p | ∈ P     |           |     |
|         |               |     |     |            |            |     | j       | j         |     |
39

Therefore, multi-class and class-wise calibration both condition on class scores. But multi-class
conditions on the entire vector of scores while class-wise conditions on score j. In binary
problems, multi-class and class-wise calibration can be collapsed into one.
To measure multi-class and class-wise calibration we use specific variants of the expected
calibration error (ECE). Many variants of ECE exists, below we’ll provide an abstract definition
of ECE which encompass multi-class and class-wise definitions (Famiglini et al., 2023).
The ECE is calculated per class over a dataset T. ECE for a dataset T is then aggregated
across the classes. The general procedure of calculating ECE is similar across probability-wise
calibration defintions. Given a dataset T with N rows calculate f(x ) = yˆ ,∀ i ∈ {1,2,...,N}
|     |     |     |     |     |     | i   | i   |
| --- | --- | --- | --- | --- | --- | --- | --- |
where is the class score of class for instance i. Then group the rows based on
|     | p   | ∈ yˆ |     | j   |     |     | (x ,y ) |
| --- | --- | ---- | --- | --- | --- | --- | ------- |
|     | i,j | i    |     |     |     |     | i i     |
when measuring multi-class calibration or when measuring class-wise calibration, using a
| yˆ  |     |     |     | p   |     |     |     |
| --- | --- | --- | --- | --- | --- | --- | --- |
| i   |     |     |     | i,j |     |     |     |
fuzzy match:
|     | • Fuzzy | match |     |     |     |     |     |
| --- | ------- | ----- | --- | --- | --- | --- | --- |
Placerowswithsimilaryˆ orp inthesamegroup. Oftenachievedbybinning/partitioning
|     |     |     | i i,j |     |     |     |     |
| --- | --- | --- | ----- | --- | --- | --- | --- |
the probability simplex ∆k or the interval [0,1]. Many binning procedures have been
suggested in the literature such as M equal width binning, the Monotonic Sweep Method
with equal mass (MSM), and the pool-adjacent-violators algorithm (CORP).
We’ll call each such group a bin B and the collection of bins for B. The number of rows in a
| bin | is |B|, | such that: |     |     |     |     |     |
| --- | ------- | ---------- | --- | --- | --- | --- | --- |
(cid:88)
|     |     |     |     | |B| | = N |     |     |
| --- | --- | --- | --- | --- | --- | --- | --- |
B∈B
| Within | each | bin we calculate | the observed | frequency | of class | label j |     |
| ------ | ---- | ---------------- | ------------ | --------- | -------- | ------- | --- |
1 (cid:88)
|     |     |     | p¯  | =   | 1(y = j) |     |     |
| --- | --- | --- | --- | --- | -------- | --- | --- |
|     |     |     |     | j,B | i        |     |     |
|B|
i∈B
| and | the average | class | score as |     |     |     |     |
| --- | ----------- | ----- | -------- | --- | --- | --- | --- |
1
(cid:88)
|     |     |     |     | p˜ =    | p   |     |     |
| --- | --- | --- | --- | ------- | --- | --- | --- |
|     |     |     |     | j,B |B| | i,j |     |     |
i∈B
(cid:80)
where the sum is understood as "for each row in B". The ECE of class j over dataset T
i∈B
| is  | then finally | calculated | as: |     |     |     |     |
| --- | ------------ | ---------- | --- | --- | --- | --- | --- |
(cid:88) |B|
|     |     |     | ECE | (T) = | |p¯ −p˜ | |   |     |
| --- | --- | --- | --- | ----- | ------- | --- | --- |
|     |     |     |     | j     | j,B     | j,B |     |
N
B∈B
| While | the | ECE of dataset | T is then | finally calculated | as: |     |     |
| ----- | --- | -------------- | --------- | ------------------ | --- | --- | --- |
k
(cid:88)
|     |     |     | ECE(T) | =   | ECE j (T) |     |     |
| --- | --- | --- | ------ | --- | --------- | --- | --- |
j=1
ECE(T) as defined above is called static calibration error or frequency based ECE.
40

Many authors critique the ECE for being uninterpretable, inconsistent, and noncomprehensive.
ECE, is known to be severely affected by the binning scheme. It has also been shown that the
ECE is a biased estimator of the true calibration error and the error is strongly dependent on
the choice of the number of bins. To address this, the Estimated Calibration Indices (ECI) was
| made as | a modification |     | of the | ECE. |     |
| ------- | -------------- | --- | ------ | ---- | --- |
ECI defines a suite of five indices, namely the local calibration index, ECI , an over-confidence,
l
ECI , and under-confidence, ECI calibration index, and two global calibration indices,
| over |     |     |     |     | under |
| ---- | --- | --- | --- | --- | ----- |
ECI and ECI . ECI allows you to measure calibration error in specific regions of
| global |     | balance |     | l   |     |
| ------ | --- | ------- | --- | --- | --- |
the probability space. ECI and ECI measures the global tendency toward over- and
|     |     |     |     | over | under |
| --- | --- | --- | --- | ---- | ----- |
under-confidence. While, ECI measures the overall calibration level in absolute terms and
global
ECI in terms of overall tendency toward over- or under-confidence.
balance
To calculate the binary indices we start with binning the rows of into a collection of bins
T
by partitioning the interval and grouping by the class score of the positive class. Per
[0,1]
bin, calculate the observed frequency and the average class score as described above.
p¯ p˜
1,B 1,B
These pairs of values per bin, now constitute a point in the first quadrant of the euclidean plane
). If this point lies close to the main diagonal (as in a reliability diagram) the
| P = (p˜ | , p¯    |     |     |     |     |
| ------- | ------- | --- | --- | --- | --- |
| B       | 1,B 1,B |     |     |     |     |
lower the calibration error. Therefore, the point’s distance from the line becomes a measure of
miscalibration. This distance is found by projecting the point onto the line and calculating the
| euclidean | norm | between | these | points. |                    |
| --------- | ---- | ------- | ----- | ------- | ------------------ |
|           |      |         |       |         | ⟨·,·⟩ Dot product  |
|           |      |         |       |         | |·| Euclidean norm |
2
1
b = √ (1,1)
2
|     |     |     |     |     | P∗ = ⟨b,P ⟩b |
| --- | --- | --- | --- | --- | ------------ |
B B
|P∗
|     |     |     |     |     | d = −P | |
| --- | --- | --- | --- | --- | -------- |
|     |     |     |     |     | B B B 2  |
The distance d is then normalized by dividing it with the maximum distance from the main
B
diagonal given the same average class score dmax. The point with the maximum distance is
B
| Pmax = | (p˜ , | p¯max), | where: |     |     |
| ------ | ----- | ------- | ------ | --- | --- |
| B      | 1,B   | 1,B     |        |     |     |
(cid:40)
1, if p˜ ≤ 0.5
p¯max 1,B
=
1,B else
0,
| ECI for | bin B | can now | be  | calculated | as: |
| ------- | ----- | ------- | --- | ---------- | --- |
l
d
ECIB B
= 1−
l dmax
B
The other indices are then calculated based on . Firstly, we collect all the bins where
ECI B
l
the scores are under- and over-confident into separate collections. The overconfident set
B−
are the bins where: and the underconfident set B+ contains such that
p˜ > p¯ p˜ ≤ p¯
|     |     |     | 1,B | 1,B | 1,B 1,B |
| --- | --- | --- | --- | --- | ------- |
41

|     | The | remaining | indices | are then | calculated | as: |
| --- | --- | --------- | ------- | -------- | ---------- | --- |
B = B−∪B+
(cid:80)
|B| ECIB
|     |     |     |     |       | B∈B+         | N l  |
| --- | --- | --- | --- | ----- | ------------ | ---- |
|     |     |     | ECI | =     |              |      |
|     |     |     |     | under | (cid:80)     | |B|  |
|     |     |     |     |       | B∈B+         | N    |
|     |     |     |     |       | (cid:80) |B| | ECIB |
B∈B−
|     |     |     | ECI | =    |          | N l |
| --- | --- | --- | --- | ---- | -------- | --- |
|     |     |     |     | over | (cid:80) | |B| |
B∈B− N
|     |     |     | ECI     | =   | ECI −ECI     |       |
| --- | --- | --- | ------- | --- | ------------ | ----- |
|     |     |     | balance |     | over         | under |
|     |     |     |         |     | (cid:80) |B| | ECIB  |
|     |     |     | ECI     | =   | B∈B          | N l   |
global
(cid:80) |B|
B∈B N
ECI is extended to multiple classes using a "one vs. all" scheme and averaging the results per
class.
The ECI has been shown to exhibit a lower bias then ECE, on average. The ECI metric
also generally over estimates the true calibration error. ECE and ECI are not proper scoring
rules and inconsistent. They can be optimized by always predicting the empirical frequencies,
leading to misleading calibration measurements in heavily skewed class problems if the model
| consistently | assigns | a high | score to | the frequent | class. |     |
| ------------ | ------- | ------ | -------- | ------------ | ------ | --- |
Note there are several other definitions and measures in the literature on calibration, such as
confidence calibration, an alternative definition of calibration, or the Hosmer-Lemeshow test, an
| alternative | evaluation | of calibration. |     |     |     |     |
| ----------- | ---------- | --------------- | --- | --- | --- | --- |
To visualize calibration reliability curves have been suggested (Dimitriadis et al., 2023).
| 4.6.4 | Computational |     | cost |     |     |     |
| ----- | ------------- | --- | ---- | --- | --- | --- |
Computationalcostrelatestotheamountofcomputationalresourceseacharchitectureconsumes,
both during training and inference. It is a proxy for the cost accrued when the model is created
and subsequently used, but also independently interesting to assess productivity, "performance
| complexity" | and bottlenecks. |     |     |     |     |     |
| ----------- | ---------------- | --- | --- | --- | --- | --- |
Our measures of computational cost are inspired by how companies such as AWS price cloud
products such as EC2 instances. Where you pay an hourly rate dependent on the instance
type, which designates the amount of computational resources available to the virtual machine.
| (Amazon    | Web Services  | (AWS), | 2025)    |          |     |     |
| ---------- | ------------- | ------ | -------- | -------- | --- | --- |
| To measure | computational |        | cost, we | measure: |     |     |
| • Training | time          |        |          |          |     |     |
42

| Wall time   | spent training     | the entire | architecture   |
| ----------- | ------------------ | ---------- | -------------- |
| • Inference | time               |            |                |
| Wall time   | spent on inference |            |                |
| • CPU usage |                    |            |                |
| CPU time    | spent during       | training   | and inference  |
| • RAM       | usage              |            |                |
| Peak RAM    | usage during       | training   | and inference. |
We measure peak RAM usage since you’d have to provision for the maximum memory footprint
to avoid out-of-memory failures. We also record wall-clock and CPU time as proxy measures of
training and inference cost. We do not report disk or network usage, not because our methods
never utilize them, but because none of them require them during model execution (some
architectures could swap to disk to reduce RAM usage, but we have spare RAM).
Downloading and storing model artifacts does incur network bandwidth and disk-space overhead,
but these costs are typically an order of magnitude lower than memory and compute expenses.
That said, specialized use cases, such as on-device hosting in mobile or embedded environments
could shift the bottleneck toward storage or bandwidth, and merit further investigation.
With regards to costs one ought to remember that the implementation is highly relevant,
inefficient implementations of an architecture may degrade it’s performance at no fault of
the underlying mathematics. Wall time could be high due to lacking parallelization, RAM
usage could be high due to inefficient data structures, CPU usage could be high due to thread
| contention and | so on. |     |     |
| -------------- | ------ | --- | --- |
Cost must be quantified in any rigorous benchmark study. It’s an ever present constraint directly
related to any value generated by modeling tabular problems. Just as optimal financial decision
making maximizes net present value, architecture choice ought to follow suit. Increasing cost
is only justified by marginal value gains, preferably allocated to minimize opportunity costs.
Without it, industry practitioners risk becoming cost centers, and academic benchmarkers
| cannot credibly | claim one | architecture’s | relative superiority. |
| --------------- | --------- | -------------- | --------------------- |
As classical algorithms are judged by how their run time scales with problem size (time
complexity), architectures should be judged by how their performance scales with available
computational resources ("performance complexity"). Formally, if denotes our resource
R
budget, methods whose performance scales as will asymptotically outperform those
θ(logR)
scaling as θ(R), regardless of any constant-factor speedups. Implementing such an evaluation is
often hampered by implementations that lack native support for specifying resource budgets
(e.g., "max 5 CPU cores, 20 GB RAM, 20 minutes"), by algorithms whose resource usage grows
discretely rather than continuously, and difficulties in comparing productivity across datasets T.
Relative out-performance in non-cost measures can simply be due to vastly greater resource
consumptionorsuperiorprogrammaticimplementation. Benchmarkstudiesshouldatleastreport
43

resource usage alongside other measures. For instance, contrasting out-of-the-box K-nearest
neighbors with CatBoost is misleading without noting that K-NN typically trains in a fraction of
the time, freeing cycles for feature selection or hyperparameter search. Furthermore, if TabPFN
outperforms CatBoost, that advantage must be contextualized by TabPFN’s extensive pre-
training. By explicitly measuring and reporting resource usage; CPU/GPU time, memory/cache
footprint, or even energy consumption, studies can establish fair “cost-performance” tiers
that reflect real-world trade-offs and drive the field toward architectures with provably better
"performance complexity", rather than ever-greater brute-force computation.
4.7 Evaluation strategy
The evaluation/validation strategy defines how T is sampled and split to assess an architecture’s
performance. Specifically, it determines how training and test sets are sampled from T.
The most basic of methods is to train and test the architecture on all of T. However, we’re
seldom interested in the performance of an architecture on in-sample instances, but rather on
out-of-sample instances, which emulates production environments where architectures encounter
new instances drawn from the underlying data distribution. Furthermore, the tendency of
generating an overfit f arise, which further defeats the purpose of generalization.
Therefore a common procedure is to partition T into a training and test set (holdout validation).
f is generated by training an architecture on the training test, any hyperparameter tuning
or post-hoc calibration is performed using a calibration set drawn from the training set and
performance is assessed on the test set. However, since the split is inherently random as is the
performance assessment prone to random variance. The process could therefore be repeated
using multiple splits, which give rise to r×k-fold cross validation, k designating the number
of folds and r the number of repetitions with different random seeds. This method could be
further modified by generating each fold through randomized, stratified sampling, grouping by
feature values and so on.
Prior literature introduce many validation, resampling or over-/under-sampling procedures. In
"The importance of choosing a proper validation strategy in predictive models. A tutorial with
real examples" the authors emphasize the importance of splitting the data between a training
and test set (generalizability), different cross-validation strategies (predictability), jackknifing
and bootstrapping (stability) and permutation test (significance) when generating and assessing
a reliable model which are models that exhibit (Lopez et al., 2023):
• Stability: The model does not change significantly after removing several samples.
• Significance: The response of the model is not due to random chance or overfitting.
• Predictability: The model is able to predict correctly (i.e., with high figures of merit).
• Generalizability: The model can be used to predict new samples.
44

The authors believe that a validation strategy should be chosen such that the model that is
stable and allows us to predict new samples with high reliability is chosen. "The best model is
not the model that best fits the calibration data, or delivers the best results in cross-validation
or, more generally spoken, resampling. "
The cross-validation strategies presented are: Leave-one-out cross-validation, Venetian blinds
cross-validation, Cross-validation across data structure and Random subsets. While the method
to split between train and test are the Kennard-Stone algorithm, Random test-set validation,
and Validation across dataset structure. Note that: "Random test-set validation is unsuitable
for imbalanced targets. This must be done with special care, always keeping the proportion of
the classes in both training and testing data sets" which is to stratify the random samples by
target value.
The authors also recommend alternatives like bootstrapping, permutation tests and jackknifing
asthestrategiestofollowapartfromcross-validation, whenclassimbalanceistoolargeandthere
are few instances. Other alternatives include over-/under- sampling however these techniques
have been shown to negatively affect calibration.
Recent work critiquing the methodology of prior benchmark studies also recommend using
k-fold cross-validation such as (Tschalzev et al., 2025) where the authors argue that 5-fold
cross-validation (5CV) consistently improves performance over holdout validation. But this
argumentationdirectlycontradictswith(Lopezetal.,2023)whichcritiquestherapidapplication
of validation methods without properly evaluating whether the utilized method is appropriate.
One example is the tendency to use leave-one-out cross-validation since it is the validation
strategy which returns the highest performance measures, without considering the data structure
and the reliability of the model. Though the authors don’t divulge on the reasoning for why
this proclaimed practice is inappropriate anymore than stating it’s an issue.
Prior benchmark studies such as (Erickson et al., 2025) have chosen a dynamic approach where
a dataset-specific repetition strategy is used and the strategy is as follows: (I) for datasets with
less than 2500 samples, use 10 times repeated 3-fold outer cross-validation; (II) for all other
datasets, we use 3 repeats.
4.8 Performance evaluation
After you’ve ran an experiment you will possess a large collection of performance measurements
across datasets, folds × repeats, and architectures. Now we’ll define how we’ll process this
information to perform the analysis we need to illuminate our research objectives.
We aim to identify calibration methods which consistently yield well-calibrated outputs. Seeing
as we explore post-hoc calibration methods, we need to assess whether these methods improved
or degraded performance. Inherently, the performance evaluation becomes relative.
45

First, let:
|     |     |     | M   | = {SVM,LR,···} |     |     |     | The | space | of models       |     |     |
| --- | --- | --- | --- | -------------- | --- | --- | --- | --- | ----- | --------------- | --- | --- |
|     |     |     |     |                |     |     |     | The | space | of calibrators. |     |     |
C = {None,Platt,Isotonic,···}
|     |     |     |     | None | being | no  | post-hoc |     | calibration   |       |     |     |
| --- | --- | --- | --- | ---- | ----- | --- | -------- | --- | ------------- | ----- | --- | --- |
|     |     |     |     | A =  | M×C   | The | space    | of  | architectures |       |     |     |
|     |     |     |     |      |       |     |          | The | dataset       | suite |     |     |
S = {jm1,MIC,···}
|     |     |     |     | F = | {1,2,··· | ,5}  | The | folds×repeats |     |     |     |     |
| --- | --- | --- | --- | --- | -------- | ---- | --- | ------------- | --- | --- | --- | --- |
|     |     |     |     |     | a        | ∈ A, | s ∈ | S, f          | ∈ F |     |     |     |
We define a discrete random variable Xp per architecture (a) and performance measure (p).
a
|     |     |     |     |     |     | Ω =   | S ×F,    | ω ∈ | Ω     |     |     |     |
| --- | --- | --- | --- | --- | --- | ----- | -------- | --- | ----- | --- | --- | --- |
|     |     |     |     |     | Xp  | : Ω → | {1,2,··· |     | ,|A|} |     |     |     |
a
where Xp(ω) is the ordinal rank of in ascending order relative to all architectures in when
|           | a   |        |          |     | a   |     |     |     |     |     |     | A   |
| --------- | --- | ------ | -------- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| evaluated | on  | (s,f), | computed |     | as: |     |     |     |     |     |     |     |
ω =
|     |     |     |         |     |      | (cid:88) |     | vp    |     |          |     |     |
| --- | --- | --- | ------- | --- | ---- | -------- | --- | ----- | --- | -------- | --- | --- |
|     |     |     | Xp(s,f) |     | = 1+ |          | 1(  | (s,f) | ≺   | vp(s,f)) |     |     |
|     |     |     |         | a   |      |          |     | a′    |     | p a      |     |     |
a′∈A\{a}
where vp(s,f) is the value of for on and the preference relation defined as:
|     | a   |     |     | p   | a   | (s,f) |     |     |     |     | ≺ p |     |
| --- | --- | --- | --- | --- | --- | ----- | --- | --- | --- | --- | --- | --- |
(cid:40)
|     |     |     |     |     |     | v < | v , | if lower  | is better |        |     |     |
| --- | --- | --- | --- | --- | --- | --- | --- | --------- | --------- | ------ | --- | --- |
|     |     |     |     |     |     | 1   | 2   |           |           |        |     |     |
|     |     |     |     | v ≺ | v = |     |     |           |           |        |     |     |
|     |     |     |     | 1 p | 2   |     |     |           |           |        |     |     |
|     |     |     |     |     |     | v > | v , | if higher | is        | better |     |     |
|     |     |     |     |     |     | 1   | 2   |           |           |        |     |     |
The expected rank of a across folds and datasets is given by the law of total expectation (Devore
et al., 2021):
|     |     |     |     | E[Xp] | =   | E[E[E[ | Xp  | | S, | F ] | | S ]] |     |     |
| --- | --- | --- | --- | ----- | --- | ------ | --- | ---- | ----- | ---- | --- | --- |
|     |     |     |     |       | a   |        |     | a    |       |      |     |     |
where S : Ω → S is the dataset random variable and F : Ω → F is the fold. The expectations
| are | empirically | estimated |        | as: |      |       |      |       |            |         |     |     |
| --- | ----------- | --------- | ------ | --- | ---- | ----- | ---- | ----- | ---------- | ------- | --- | --- |
|     |             |           |        | Eˆ[ | Xp   |       |      |       | Xp(s,f)    |         |     |     |
|     |             |           |        |     | |    | S =   | s, F | = f ] | =          |         |     |     |
|     |             |           |        |     | a    |       |      |       | a          |         |     |     |
|     |             |           |        |     |      |       |      |       | 1 (cid:88) |         |     |     |
|     |             |           | Eˆ[Eˆ[ | Xp  | | S, | F ] | | S =  | s ] = |            | Xp(s,f) |     |     |
|     |             |           |        |     | a    |       |      |       |            | a       |     |     |
|F|
f∈F
|     |     |     |     |        |     |     | 1   | (cid:88)(cid:88) |         |     |     |     |
| --- | --- | --- | --- | ------ | --- | --- | --- | ---------------- | ------- | --- | --- | --- |
|     |     |     |     | Eˆ[Xp] |     | =   |     |                  | Xp(s,f) |     |     |     |
|     |     |     |     |        | a   |     |     |                  | a       |     |     |     |
|S|·|F|
s∈Sf∈F
46

Eˆ[Xp] is a Monte Carlo estimator of the expected rank under the ranking distribution. This
a
estimator assumes a uniform prior over datasets and folds. If the datasets are not sampled
I.I.D. from the population of datasets (is representative of the population), the estimator may
be biased. Additionally, increasing the number of cross-validation repeats per dataset reduces
estimator variance. We compute Eˆ[Xp] for each architecture and select performance measures
a
to assess who has the highest expected performance by and call it the expected performance
p
rank of across folds and datasets. The figure is understood as the expected ranking of if you
a a
| randomly chose | a   | fold and | dataset |     | in the suite. |     |     |     |
| -------------- | --- | -------- | ------- | --- | ------------- | --- | --- | --- |
To isolate the effect of post-hoc calibration methods (PHCMS) we define change measures that
measure performance deltas relative to the uncalibrated learner. For learner m ∈ M, PHCM
| c ∈ C \{None} | =   | PHCMS |     | , and | ω = (s,f) |     |        |     |
| ------------- | --- | ----- | --- | ----- | --------- | --- | ------ | --- |
|               |     |       |     |       | Marginal  |     | change |     |
:
|     |     |     | ∆p  | (m,c,ω) | =   | vp  | (ω)−vp | (ω) |
| --- | --- | --- | --- | ------- | --- | --- | ------ | --- |
marg
|     |     |     |     |     |          | (m,c)  | (m,None) |     |
| --- | --- | --- | --- | --- | -------- | ------ | -------- | --- |
|     |     |     |     |     | Relative | change | :        |     |
∆p
|     |     |     |         |     | sign(cid:0) |      | (cid:1) | (m,c,ω) |
| --- | --- | --- | ------- | --- | ----------- | ---- | ------- | ------- |
|     |     | ∆p  | (m,c,ω) |     | =           | ∆p   | ·| marg | |·100   |
|     |     |     | rel     |     |             | marg | vp      |         |
(ω)
(m,None)
Y∆p
We define another discrete random variable per PHCM (c) and performance delta measure
c
(∆p).
|     |     |     |     |     | Θ = M×S | ×F, | θ ∈ Θ |     |
| --- | --- | --- | --- | --- | ------- | --- | ----- | --- |
Y∆p
|     |     |     |     | :   | Θ → {1,2,··· |     | ,|C \{None}|} |     |
| --- | --- | --- | --- | --- | ------------ | --- | ------------- | --- |
c
where Y∆p(θ) is the ordinal rank of c in ascending order relative to all PHCMS when evaluated
c
| on θ = (m,s,f), |     | computed | as: |     |          |     |            |            |
| --------------- | --- | -------- | --- | --- | -------- | --- | ---------- | ---------- |
|                 | Y∆p |          |     |     | (cid:88) |     | ∆p(m,c′,ω) | ∆p(m,c,ω)) |
|                 |     | (m,ω)    | =   | 1+  |          | 1(  |            | ≺          |
|                 |     | c        |     |     |          |     |            | p          |
c′∈C\{None,c}
The expected rank of c across models, datasets and folds is given by the law of total expectation:
|       |     | E[Y∆p  | ]     | = E[E[E[E[ | Y∆p       | |   | M, S, F ] | | M, S ]| M]] |
| ----- | --- | ------ | ----- | ---------- | --------- | --- | --------- | ------------- |
|       |     |        | c     |            |           | c   |           |               |
| where |     | is the | model | random     | variable. |     |           |               |
| M : Θ | → M |        |       |            |           |     |           |               |
47

| The expectations |     | are | empirically |     | estimated | as: |        |                 |     |     |
| ---------------- | --- | --- | ----------- | --- | --------- | --- | ------ | --------------- | --- | --- |
|                  |     |     | Eˆ[ Y∆p     | |   | M = m,    | S = | s, F = | f ] = Y∆p (m,ω) |     |     |
|                  |     |     |             | c   |           |     |        | c               |     |     |
1
|     |     | Eˆ[Eˆ[ | Y∆p |       |       |     |        | (cid:88) Y∆p |       |     |
| --- | --- | ------ | --- | ----- | ----- | --- | ------ | ------------ | ----- | --- |
|     |     |        | |   | M, S, | F ] | | M = | m, S = | s ] =        | (m,ω) |     |
|     |     |        | c   |       |       |     |        | |F|          | c     |     |
f∈F
|     |           |     |      |     |          |      |        | 1 (cid:88)(cid:88) |     |       |
| --- | --------- | --- | ---- | --- | -------- | ---- | ------ | ------------------ | --- | ----- |
|     | Eˆ[Eˆ[Eˆ[ | Y∆p |      |     |          |      |        |                    | Y∆p |       |
|     |           |     | | M, | S,  | F ] | M, | S ]| | M = m] | =                  |     | (m,ω) |
|     |           |     | c    |     |          |      |        | |S|·|F|            |     | c     |
s∈Sf∈F
|     |     |     |        |     | 1           |     | (cid:88) | (cid:88)(cid:88) |     |     |
| --- | --- | --- | ------ | --- | ----------- | --- | -------- | ---------------- | --- | --- |
|     |     |     | Eˆ[Y∆p |     |             |     |          | Y∆p              |     |     |
|     |     |     |        | ] = |             |     |          | (m,ω)            |     |     |
|     |     |     |        | c   | |M|·|S|·|F| |     |          | c                |     |     |
m∈Ms∈Sf∈F
Eˆ[Y∆p]
is also a Monte Carlo estimator and the same considerations apply, additionally the
c
estimator may be biased if the set of models is un-representative. The figure is understood as
the expected ranking of a PHCM if you randomly chose a model, dataset and fold.
We also want to know the impact each post-hoc calibration method has and therefore produce
the distributions of ∆p(m,c,ω) aggregated across folds and datasets per model and post-hoc
| calibrator. | Additionally |     | we  | aggregate | across | models. |     |     |     |     |
| ----------- | ------------ | --- | --- | --------- | ------ | ------- | --- | --- | --- | --- |
5 Experiment
5.1 Reproduction
To reproduce or review the specifics of our experiment’s implementation go to our GitHub
repository and follow the instructions in the README.md file and run the project on a host
machine running Linux (RHEL) with Intel Xeon E5-2690 CPUs, 32 cores and 512 GB RAM if
| you want | to imitate |     | our machine. |     |     |     |     |     |     |     |
| -------- | ---------- | --- | ------------ | --- | --- | --- | --- | --- | --- | --- |
5.2 Description
To determine which calibration methods consistently perform, we’ll measure the out-of-box
performance of each model on a diverse dataset suite, then we’ll apply each calibration method
on each model to measure the change in performance. Afterwards, we’ll assess whether any
calibration methods consistently out-perform across models and datasets.
5.2.1 Models
| We’ll restrict | ourselves |        | to Binary    |       | problems, | and   | include | the models; |     |     |
| -------------- | --------- | ------ | ------------ | ----- | --------- | ----- | ------- | ----------- | --- | --- |
| • Empirical    |           | class  | distribution |       | / Class   | prior | (AVG)   |             |     |     |
| • Support      |           | vector | machine      | (SVM) |           |       |         |             |     |     |
48

• Linear Discriminant Analysis (LDA)
• Naïve bayes (NB)
• Logistic Regression (LR)
• K-Nearest Neighbours (KNN)
• RandomForest (RF)
• Gradient Boosting Classifier (GBC)
• Histogram Gradient Boosting (HGB)
• ExtraTrees (EXT)
• Explainable Boosting Machine (EBM)
• Catboost (CB)
• XGBoost (XGB)
• LightGBM (LGBM)
• ModernNCA (NCA)
• TabTransformer (TTRA)
• TabICL (TICL)
• TabPFN v2 (TABPFN)
• TabM (TABM)
• Multilayer Perceptron (MLP)
• Real Multilayer Perceptron (REMLP)
Prioritizing implementations from Scikit-learn, TensforFlow/Keras, pytorch/lightning/fast.ai, or
the model specific framework.
5.2.2 Calibration methods
The calibration methods considered are the post-hoc calibration methods:
• Isotonic regression (isotonic)
• Platt scaling (platt)
• Beta calibration (beta)
• Venn-abers predictors (venn abers)
• Pearsonify. (pearsonify)
49

5.2.3 Datasets
To evaluate these methods we’ll apply them to the dataset suite Tabarena-v0.1, which contains
30 binary classification problems. We minimally pre-processes the datasets by encoding all
categoricals to unique integers, missing values are encoded to their own group. Non-categoricals
are coerced to real numbers, missing values and invalid parsing are set to 0. There is no model
specific pre-processing.
| 5.2.4 | Evaluation | strategy |     |     |
| ----- | ---------- | -------- | --- | --- |
We’ll use the evaluation strategy; 1×5-fold cross validation. Four folds are collectively the
training set while the remaining held-out fold is the test set. There are no repetitions. Each
architecture is therefore generated and evaluated 5 times per dataset. The folds are generated
using randomized stratified sampling without replacement. The strata is the target class. When
a calibration set is required by an architecture, it will be sampled from the training folds using
randomized stratified sampling without replacement, the strata still being the target class.
| 5.2.5            | Performance | measures |                    |     |
| ---------------- | ----------- | -------- | ------------------ | --- |
| To assess        | performance | on each  | run we’ll measure: |     |
| • Classification |             | ability  |                    |     |
Accuracy
–
| • Discriminatory |     | ability |     |     |
| ---------------- | --- | ------- | --- | --- |
AUC-ROC
–
• Calibration
|     | – Brier score |     |     |     |
| --- | ------------- | --- | --- | --- |
Log-loss
–
|                 | – ECI global | (MSM)       |              |           |
| --------------- | ------------ | ----------- | ------------ | --------- |
| • Computational |              | Cost        |              |           |
|                 | Total CPU    | time during | training and | inference |
–
|     | – Peak RAM | usage during | training | and inference |
| --- | ---------- | ------------ | -------- | ------------- |
ECE and ECI bins are generated using the Monotonic Sweep Method with equal mass (MSM).
ECE is calculated using the frequency based definition. Calibration, discrimination and classifi-
cation is measured on the held-out test set. Class predictions are derived from the scores using
the highest score, which is a Bayes classifier when the learner is instance-wise calibrated (Cohen
| and Goldszmidt, | 2004). |     |     |     |
| --------------- | ------ | --- | --- | --- |
50

5.3 Evaluation of the experiment
In light of our research objectives, the experiment design imply certain strength and weakness
in the choices we’ve made with regards to the dataset suite, evaluation strategy, space of
architectures evaluated and performance measurements.
The space of methods or space of architectures evaluated encompass binary, popular machine
learning models and select post-hoc calibration techniques. This provides the grounds to assess
which binary calibration methods tend to out-perform among models explored. But does not
provide the ground to claim state of the art. Since, the set of post-hoc calibration techniques is
limited. We’re also missing components in architectures known to improve performance, such as
hyperparameter optimization and model specific pre-processing.
The Tabarena-v0.1 suite is an actively maintained, distillation of a broad collection of dataset
suites. It being maintained, allows us to easily rerun the experiment in the future as the dataset
develops. It’s also curated in such a way that makes it an ideal match for our research objective.
The datasets are required to be I.I.D. and arise from real random distributions. They’re
also required to reflect classification and regression problems you likely would have applied
supervised-tabular machine learning to solve. The only questionable aspects of the curation is
the size limit, ethical exclusions and lacking evaluation of diversity and representativeness.
Very small and very large datasets are excluded, since the authors argue that these dataset
require specialized methods to handle optimally. I’d rather these datasets be included in the
suite, such that the architecture’s ability to handle large and small datasets be evaluated. The
authors could’ve made no such exclusion or created multiple suites.
Ethically ambiguous tasks are also excluded, when they could’ve been flagged or obscured.
Ultimately, these datasets are tables with numbers which we use to benchmark the performance
of architectures. These interventions into the suite may weaken it’s representativeness and also
any subsequent benchmarking.
Lastly, we found no real consideration made to the qualitative and quantitative diversity of the
resultingsuiteorit’srepresentativeness. Thesuiteshouldrepresentthespaceofpossibledatasets,
but whether the suite does so has not been evaluated. Intuitively, representativeness seems
likely due to the high number of benchmark studies being distilled, but it is mere conjecture.
The evaluation is missing which weakens any generalization of results beyond the suite. Since
there is no quantitative or qualitative assessment of the diversity of datasets, there is no cause
to claim the explored methods perform in general or on those with the present nature.
Stratified randomized 1×5-fold cross validation allows us to repeat the experiment multiple
times, aggregating performance measures across runs to asses expectation. Our results should
therefore be less prone to random variance. Stratification also ensures each class is present in
each set according to their empirical frequency. However, we would’ve liked if our folds were
generated in such a way as to guarantee additional properties. Such as the test sets containing
interpolative and extrapolative out of sample instances. Furthermore, instances in dense and
sparse vector space. We also see that the chosen evaluation strategy may not be optimal for
51

small and heavily imbalanced datasets.
Our battery of performance metrics is diverse and measures multiple facets of performance. The
same facets are evaluated in multiple ways to capture methodological differences and to ensure
our results are comparable with previous studies. The battery lacks a principled foundation,
establishing which performance facets are essential and which measurements are optimal. There
may also be facets of performance relevant to your domain or application which we’ve failed to
consider.
We contend that performance measures should be strictly proper scoring rules (e.g., log-loss,
Brier score). A core objective when estimating f is to recover the true conditional probability
function. Crucially, the true f uniquely minimizes log-loss and brier score. Thus, lower values
on these measurements provide evidence of approaching ground-truth probabilities. A property
absent for ECE and ECI which are also prone to aforementioned errors.
Computationalresourcesaremeasuredusingcgroupv2,whichprovideskernelaggregatedresource
usage attributable to a group of processes. We’re therefore confident our measurements are all
encompassing and accurate. We expect some overhead to be included in the RAM and CPU
measurements.
5.4 Scope of inference
Due to the nature of our experiment, as evaluated above, the conclusions we may justifiably
infer from it’s results are limited. Specifically, no claim to have found state-of-the-art may
be made, we’ve inherently explored optimum over a space of architectures and datasets, and
can only evaluate expectation in performance within this space. We may generalize these
performance expectations to other datasets and models, since these sets are diverse. But the
missing evaluation of Tabarena-v0.1’s diversity weaken any generalization across datasets. We
do not know whether the suite is representative for datasets in general.
We therefore believe this experiment provides the grounds to illuminate which post-hoc calibra-
tion methods among those explored tend to perform across binary classification datasets and
models, but cannot claim to have found the best methods. The experiment is also missing any
statistical tests to ensure the results are statistically significant.
52

| 5.5 Future | extensions |     |     |     |
| ---------- | ---------- | --- | --- | --- |
In a future iteration of this study we’d like modify the experiment to include:
•
Evaluate the diversity and representativeness of the dataset suite
Include an investigation into how one ought to evaluate the diversity of a dataset suite,
and subsequently evaluate the representativeness of Tabarena-v0.1. Should be done to
| strengthen | the generalization | of  | results across | datasets. |
| ---------- | ------------------ | --- | -------------- | --------- |
•
| Expand | the performance | assessment |     |     |
| ------ | --------------- | ---------- | --- | --- |
We should examine performance facets more comprehensively, including developing princi-
pled approaches for selecting appropriate metrics within each facet rather than relying on
ad-hoc choices.
Results should be validated using appropriate statistical methods to establish significance
and reliability. Potential approaches include the DeGroot and Fienberg calibration test for
rigorous calibration assessment, and Friedman and Nemenyi tests to evaluate performance
| differences | across diverse | datasets. |     |     |
| ----------- | -------------- | --------- | --- | --- |
Our assessment of computational cost should be more comprehensive. RAM utilization
through training and inference should be measured, not only the peak. L1, L2 and L3
| cache usage | could also | be measured | along | with energy consumption. |
| ----------- | ---------- | ----------- | ----- | ------------------------ |
Several technical enhancements would improve measurement accuracy. Process isolation
using separate cgroups during model training and inference would reduce measurement
overhead and improve resource usage measurement. Dictionary-based storage should be
replaced with a n-dimensional tensors for more efficient performance measurement storage
and analysis. A Streamlit application could enable user-specific analysis and exploration
of results.
Beyond aggregate performance metrics, the evaluation should investigate when methods
perform well. This conditional analysis would examine performance under different con-
ditions such as dataset characteristics (size, dimensionality, class balance), data quality
issues (missing values, noise, outliers), domain-specific constraints (latency requirements,
interpretability needs), resource limitations (computational budgets), and instance charac-
| teristics | (sparse/dense | space, extrapolative/interpolative). |     |     |
| --------- | ------------- | ------------------------------------ | --- | --- |
•
| Refine | evaluation | strategy |     |     |
| ------ | ---------- | -------- | --- | --- |
Though the chosen evaluation strategy has many strengths, maybe other strategies are
more efficient for large, small or imbalanced datasets. The held-out sets should also
somehow guarantee the presence of out-of-sample interpolative and extrapolative instances
as well as instances in dense and sparse vector space. The Kennard-Stone algorithm
could be used to generate these sets. Partly, such that one may evaluate how well each
| architecture | handles       | such cases. |     |     |
| ------------ | ------------- | ----------- | --- | --- |
| • Define     | computational | budgets     |     |     |
Fair comparison of architectures requires establishing explicit computational budgets to
53

ensure performance evaluations occur within comparable resource constraints. These
budgets should encompass both operational specifications (such as maximum inference
time) and resource limitations (including CPU/GPU time, memory usage, and wall-clock
time).
A practical approach involves defining composite resource budgets that specify maximum
computational resource usage over a fixed time period (e.g., maximum 2 CPU cores and 20
GB RAM for 30 minutes of training time). Implementation should utilize process isolation
by spawning child processes during both training and inference phases, enabling precise
budget monitoring and enforcement. This approach provides the capability to terminate
architectures that exceed their allocated resources.
Furthermore, when using a fixed-budget framework with pre-trained architectures (e.g.,
foundation models), two precautions are essential. First, because one off pre-training
confers an advantage over from scratch models, you must specify which development stages
count toward the budget and should ideally allow all architectures equivalent pre-training
access. Without this parity, any performance gains may reflect budget differences rather
than architectural merits. Though, one could question the degree to which practitioners
consider costs they do not incur.
• Find state of the art
The study could be modified to provide the ground to make state of the art claims.
To do so all of the above must be done, additionally we must; remove model agnostic
pre-processing, use GPUs and expand the space of explored architectures.
The space of proposed and possible architectures has become massive especially, when
you consider all possible combinations or compositions. To truly generate the empirical
foundation necessary to support state-of-the-art claims today is therefore a considerably
larger undertaking then many authors seem to realize.
To expand the space of explored architectures we could include more learners and calibra-
tion methods, especially model specific methods. When doing so one must ensure that
each model is applied optimally such that any performance evaluation reflect it’s outmost
potential on the given dataset by for example applying relevant pre-processing, hyper-
parameter tuning, and ensembling. The explored architectures should also encompass
those shown to out-perform previously and those claimed to be state of the art.
• Include a synthetic dataset suite
Should create and benchmark on a synthetic dataset suite. By doing so we can calculate
the true conditional probabilities and therefore the true calibration error. We can also
guarantee the diversity of the dataset suite, and evaluate how methods perform in a broad
range of scenarios.
• Extend to multiclass
Should expand the study to also include multi-class problems and methods.
• Extend to non I.I.D. data
The study could be expanded to include non I.I.D. data such as time series. Because,
54

in real systems, distributions often drift over time. This is especially true in domains
regarding complex adaptive systems like economics and biology, where the structure
of the underlying system evolves dynamically. In such settings, the I.I.D. assumption
frequently breaks down. Considering non I.I.D. scenarios, whether through methods from
continual/incremental learning, complete re-training or explicit modeling of distribution
| drift can greatly | improve | the relevance | of the results. |
| ----------------- | ------- | ------------- | --------------- |
•
| Provide theoretical | explanations |     |     |
| ------------------- | ------------ | --- | --- |
Ourstudyisempiricalinnatureandprovidesnotheoreticalexplanationforit’sobservations.
| Could include | such considerations | in the | future. |
| ------------- | ------------------- | ------ | ------- |
55

6 Sources
References
Yash Akhauri, Bryan Lewandowski, Cheng-Hsi Lin, Adrian N. Reyes, Grant C. Forbes, Arissa
Wongpanich, Bangding Yang, Mohamed S. Abdelfattah, Sagi Perel, and Xingyou Song.
Performance Prediction for Large Systems via Text-to-Text Regression, 2025. URL https:
//arxiv.org/abs/2506.21718.
Edesio Alcobaca, Felipe Siqueira, Adriano Rivolli, Luis P. F. Garcia, Jefferson T. Oliva, and
AndrÃ© C. P. L. F. de Carvalho. MFE: Towards reproducible meta-feature extraction.
Journal of Machine Learning Research, 21(111):1–5, 2020. URL http://jmlr.org/papers/
v21/19-348.html.
Alnuaimi, Amer F.A.H. and Albaldawi, Tasnim H.K. An overview of machine learning classifi-
cation techniques. BIO Web Conf., 97:00133, 2024. doi: 10.1051/bioconf/20249700133. URL
https://doi.org/10.1051/bioconf/20249700133.
Amazon Web Services (AWS). Amazon EC2 On-Demand Pricing, 2025. URL https://aws.
amazon.com/ec2/pricing/on-demand/.
Anonymous. A Comprehensive Guide to Dataset Selection for Classifier Calibration Benchmark-
ing.
BerndBischl,GiuseppeCasalicchio,MatthiasFeurer,PieterGijsbers,FrankHutter,MichelLang,
Rafael G. Mantovani, Jan N. van Rijn, and Joaquin Vanschoren. OpenML Benchmarking
Suites, 2021. URL https://arxiv.org/abs/1708.03731.
Henrik Boström. Calibrating Random Forests. In 2008 Seventh International Conference on
Machine Learning and Applications, pages 121–126, 2008. doi: 10.1109/ICMLA.2008.107.
M. Bourel and A. M. Segura. Multiclass classification methods in ecology. Ecological Indicators,
85:1012–1021, 2018. ISSN 1470-160X. doi: https://doi.org/10.1016/j.ecolind.2017.11.031.
URL https://www.sciencedirect.com/science/article/pii/S1470160X17307434.
Leo Breiman. Arcing classifier (with discussion and a rejoinder by the author). The Annals of
Statistics, 26(3):801 – 849, 1998. doi: 10.1214/aos/1024691079. URL https://doi.org/10.
1214/aos/1024691079.
Alex Carriero, Kim Luijken, Anne de Hond, Karel G. M. Moons, Ben van Calster, and Maarten
van Smeden. The Harms of Class Imbalance Corrections for Machine Learning Based
Prediction Models: A Simulation Study. Statistics in Medicine, 44(3-4):e10320, 2025. doi:
https://doi.org/10.1002/sim.10320. URL https://onlinelibrary.wiley.com/doi/abs/10.
1002/sim.10320.
Weijie Chen, Berkman Sahiner, Frank Samuelson, Aria Pezeshk, and Nicholas Petrick. Cal-
ibration of medical diagnostic classifier scores to the probability of disease. Statistical
56

Methods in Medical Research, 27(5):1394–1409, 2018. doi: 10.1177/0962280216661371. URL
https://doi.org/10.1177/0962280216661371.
Ira Cohen and Moises Goldszmidt. Properties and Benefits of Calibrated Classifiers. In 8th
EuropeanConferenceonPrinciplesandPracticeofKnowledgeDiscoveryinDatabases(PKDD),
volume 3202, August 2004. ISBN 978-3-540-23108-0. doi: 10.1007/978-3-540-30116-5_14.
Felix Conrad, Mauritz Mälzer, Michael Schwarzenberger, Hajo Wiemer, and Steffen Ihlenfeldt.
BenchmarkingAutoMLforregressiontasksonsmalltabulardatainmaterialsdesign. Scientific
Reports, 12(1):19350, November 2022. ISSN 2045-2322. doi: 10.1038/s41598-022-23327-1.
URL https://doi.org/10.1038/s41598-022-23327-1.
P. Cotton. Microprediction: Building an Open AI Network. MIT Press, 2022. ISBN
9780262047326. URL https://books.google.no/books?id=RDlcEAAAQBAJ.
Jay L. Devore, Kenneth N. Berk, and Matthew A. Carlton. Modern Mathematical Statistics with
Applications. Springer Texts in Statistics. Springer, Cham, Switzerland, 3 edition, 2021. ISBN
978-3-030-55155-1 (hardcover), 978-3-030-55156-8 (eBook). doi: 10.1007/978-3-030-55156-8.
URL https://link.springer.com/book/10.1007/978-3-030-55156-8.
Timo Dimitriadis, Tilmann Gneiting, Alexander I. Jordan, and Peter Vogel. Evaluating
Probabilistic Classifiers: The Triptych, 2023. URL https://arxiv.org/abs/2301.10803.
Alexey Dosovitskiy, Lucas Beyer, Alexander Kolesnikov, Dirk Weissenborn, Xiaohua Zhai,
Thomas Unterthiner, Mostafa Dehghani, Matthias Minderer, Georg Heigold, Sylvain Gelly,
Jakob Uszkoreit, and Neil Houlsby. Vision Transformer (ViT), 2020. URL https://github.
com/google-research/vision_transformer.
Vannessa Duarte, Sergio Zuniga-Jara, and Sergio Contreras. Machine Learning and Marketing:
A Literature Review. SSRN Electronic Journal, January 2022. doi: 10.2139/ssrn.4006436.
URL https://ssrn.com/abstract=4006436.
Nick Erickson, Lennart Purucker, Andrej Tschalzev, David Holzmüller, Prateek Mutalik Desai,
David Salinas, and Frank Hutter. TabArena: A Living Benchmark for Machine Learning on
Tabular Data, 2025. URL https://arxiv.org/abs/2506.16791.
Lorenzo Famiglini, Andrea Campagner, and Federico Cabitza. Towards a Rigorous Calibration
Assessment Framework: Advancements in Metrics, Methods, and Use. September 2023. ISBN
9781643684369. doi: 10.3233/FAIA230327.
Gerardo Flores, Abigail Schiff, Alyssa H. Smith, Julia A. Fukuyama, and Ashia C. Wilson. A
Consequentialist Critique of Binary Classification Evaluation Practices, 2025. URL https:
//arxiv.org/abs/2504.04528.
PedroG.FonsecaandHugoD.Lopes. CalibrationofMachineLearningClassifiersforProbability
of Default Modelling, 2017. URL https://arxiv.org/abs/1710.08901.
57

Jerome H. Friedman. Regularized Discriminant Analysis. Journal of the American Statistical
Association, 84(405):165–175, 1989. doi: 10.1080/01621459.1989.10478752. URL https:
//www.tandfonline.com/doi/abs/10.1080/01621459.1989.10478752.
Josh Gardner, Zoran Popovic, and Ludwig Schmidt. Benchmarking Distribution
Shift in Tabular Data with TableShift. In A. Oh, T. Naumann, A. Glober-
son, K. Saenko, M. Hardt, and S. Levine, editors, Advances in Neural In-
formation Processing Systems, volume 36, pages 53385–53432. Curran Associates,
Inc., 2023. URL https://proceedings.neurips.cc/paper_files/paper/2023/file/
a76a757ed479a1e6a5f8134bea492f83-Paper-Datasets_and_Benchmarks.pdf.
GeeksforGeeks. Confusion Matrix in Machine Learning. URL https://www.geeksforgeeks.
org/confusion-matrix-machine-learning/.
Pieter Gijsbers, Marcos L. P. Bueno, Stefan Coors, Erin LeDell, Sébastien Poirier, Janek
Thomas, Bernd Bischl, and Joaquin Vanschoren. AMLB: an AutoML Benchmark, 2023. URL
https://arxiv.org/abs/2207.12560.
Léo Grinsztajn, Edouard Oyallon, and Gaël Varoquaux. Why do tree-based models still
outperformdeeplearningontabulardata?, 2022. URLhttps://arxiv.org/abs/2207.08815.
Fatemeh Hemmatian and Mohammad Karim Sohrabi. A survey on classification techniques
for opinion mining and sentiment analysis. Artificial Intelligence Review, 52:1495–1545,
2019. doi: 10.1007/s10462-017-9599-6. URL https://link.springer.com/article/10.
1007/s10462-017-9599-6.
Anna Jurek, Yaxin Bi, Shengli Wu, and Chris Nugent. A survey of commonly used ensemble-
based classification techniques. The Knowledge Engineering Review, 29(5):551–581, 2014. doi:
10.1017/S0269888913000155.
Kaggle. Kaggle Machine Learning & Data Science Survey (2021). 2021. URL https://www.
kaggle.com/kaggle-survey-2021.
Kaggle. Kaggle Machine Learning & Data Science Survey (2022). 2022. URL https://www.
kaggle.com/kaggle-survey-2022.
Meelis Kull, Telmo de Menezes e Silva Filho, and Peter Flach. Beta calibration: A well-founded
andeasilyimplementedimprovementonlogisticcalibrationforbinaryclassifiers. InProceedings
of the 20th International Conference on Artificial Intelligence and Statistics (AISTATS),
volume 54 of Proceedings of Machine Learning Research, pages 623–631, 2017. URL https:
//betacal.github.io/. Extended version also published in Electronic Journal of Statistics.
Wonbin Kweon, SeongKu Kang, and Hwanjo Yu. Obtaining Calibrated Probabilities with
Personalized Ranking Models, 2022. URL https://arxiv.org/abs/2112.07428.
Guangping Li, Zujia Lu, Junzhi Wang, and Zhao Wang. Machine Learning in Stellar Astronomy:
Progress up to 2024, 2025. URL https://arxiv.org/abs/2502.15300.
58

Eneko Lopez, Jaione Etxebarria-Elezgarai, Jose Manuel Amigo, and Andreas Seifert. The
importance of choosing a proper validation strategy in predictive models. A tutorial with real
examples. Analytica Chimica Acta, 1275:341532, 2023. ISSN 0003-2670. doi: https://doi.org/
10.1016/j.aca.2023.341532. URL https://www.sciencedirect.com/science/article/pii/
S0003267023007535.
Valeriy Manokhin. Spiegelhalter z-score for binary classifica-
tion. Medium, June 2025. URL https://valeman.medium.com/
spiegelhalter-z-score-for-binary-classification-25566e43ae0d.
Valery Manokhin. Machine learning for probabilistic prediction. URL https://doi.org/10.
5281/zenodo.6727505.
Duncan McElfresh, Sujay Khandagale, Jonathan Valverde, Vishak Prasad C, Benjamin Feuer,
Chinmay Hegde, Ganesh Ramakrishnan, Micah Goldblum, and Colin White. When Do Neural
Nets Outperform Boosted Trees on Tabular Data?, 2024. URL https://arxiv.org/abs/
2305.02997.
Patryk Orzechowski and Jason H. Moore. Generative and reproducible benchmarks for compre-
hensive evaluation of machine learning classifiers, 2021. URL https://arxiv.org/abs/2107.
06475.
Yash Paul and Neerendra Kumar. A Comparative Study of Famous Classification Techniques
and Data Mining Tools. In Pradeep Kumar Singh, Arpan Kumar Kar, Yashwant Singh,
Maheshkumar H. Kolekar, and Sudeep Tanwar, editors, Proceedings of ICRIC 2019, pages
627–644, Cham, 2020. Springer International Publishing. ISBN 978-3-030-29407-6.
Maja Pavlovic. Understanding Model Calibration – A gentle introduction and visual exploration
of calibration and the expected calibration error (ECE), 2025. URL https://arxiv.org/
abs/2501.19047.
scikit-learn developers. sklearn.isotonic.IsotonicRegression — scikit-learn api docu-
mentation. https://scikit-learn.org/stable/modules/generated/sklearn.isotonic.
IsotonicRegression.html, 2025a.
scikit-learn developers. sklearn.linear_model.LogisticRegression — scikit-learn api documen-
tation. https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.
LogisticRegression.html, 2025b.
Mohammad Hossein Shaker and Eyke Hüllermeier. Random Forest Calibration, 2025. URL
https://arxiv.org/abs/2501.16756.
Shai Shalev-Shwartz and Shai Ben-David. Understanding Machine Learning: From Theory to
Algorithms. Cambridge University Press, 2014.
Maohao Shen, Yuheng Bu, Prasanna Sattigeri, Soumya Ghosh, Subhro Das, and Gregory
Wornell. Post-hoc Uncertainty Learning Using a Dirichlet Meta-Model. Proceedings of the
AAAI Conference on Artificial Intelligence, 37(8):9772–9781, June 2023. doi: 10.1609/aaai.
v37i8.26167. URL https://ojs.aaai.org/index.php/AAAI/article/view/26167.
59

Yun-Fei Shi, Zheng-Xin Yang, Sicong Ma, Pei-Lin Kang, Cheng Shang, P. Hu, and Zhi-
Pan Liu. Machine Learning for Chemistry: Basics and Applications. Engineering, 27:
70–83, 2023. ISSN 2095-8099. doi: https://doi.org/10.1016/j.eng.2023.04.013. URL https:
//www.sciencedirect.com/science/article/pii/S2095809923002813.
Telmo Silva Filho, Hao Song, Miquel Perello-Nieto, Raul Santos-Rodriguez, Meelis Kull, and
Peter Flach. Classifier calibration: a survey on how to assess and improve predicted class
probabilities. Machine Learning, 112(9):3211–3260, May 2023. ISSN 1573-0565. doi: 10.1007/
s10994-023-06336-7. URL http://dx.doi.org/10.1007/s10994-023-06336-7.
David J. Spiegelhalter. Probabilistic prediction in patient management and clinical trials.
Statistics in Medicine, 5(5):421–433, October 1986. doi: 10.1002/sim.4780050506. URL
https://pubmed.ncbi.nlm.nih.gov/3786996/.
P. Aditya Sreekar, Sahil Verma, Varun Madhavan, and Abhishek Persad. Unveiling the Power
of Self-Attention for Shipping Cost Prediction: The Rate Card Transformer, 2023. URL
https://arxiv.org/abs/2311.11694.
AndrejTschalzev, LennartPurucker, StefanLüdtke, FrankHutter, ChristianBartelt, andHeiner
Stuckenschmidt. Unreflected Use of Tabular Data Repositories Can Undermine Research
Quality, 2025. URL https://arxiv.org/abs/2503.09159.
Vladimir Vovk, Ivan Petej, and Valentina Fedorova. Large-scale probabilistic predictors with
and without guarantees of validity, 2015. URL https://arxiv.org/abs/1511.00213.
Penghui Wei, Weimin Zhang, Ruijie Hou, Jinquan Liu, Shaoguo Liu, Liang Wang, and Bo Zheng.
Posterior Probability Matters: Doubly-Adaptive Calibration for Neural Predictions in Online
Advertising, 2024. URL https://arxiv.org/abs/2205.07295.
xRiskLab. Pearsonify: Lightweight Python package for generating classification intervals
in binary classification tasks using Pearson residuals and conformal prediction. https:
//github.com/xRiskLab/pearsonify, 2025. GitHub repository.
Mochen Yang and Xuan Bi. Cost-Aware Calibration of Classifiers. INFORMS Journal on Data
Science, 4(2):101–113, 2025. doi: 10.1287/ijds.2024.0038. URL https://doi.org/10.1287/
ijds.2024.0038.
JavierRodriguezZaurinandPavolMulinka. pytorch-widedeep: Aflexiblepackageformultimodal
deep learning. Journal of Open Source Software, 8(86):5027, June 2023. doi: 10.21105/joss.
05027. URL https://joss.theoj.org/papers/10.21105/joss.05027.
JizeZhang,BhavyaKailkhura,andT.Yong-JinHan.Mix-n-Match: EnsembleandCompositional
Methods for Uncertainty Calibration in Deep Learning, 2020. URL https://arxiv.org/
abs/2003.07329.
A Additional Plots
60