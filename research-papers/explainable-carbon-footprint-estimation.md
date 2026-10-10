Received16November2022,accepted30November2022,dateofpublication1December2022,
dateofcurrentversion7December2022.
DigitalObjectIdentifier10.1109/ACCESS.2022.3226324
Explainable Automatic Industrial Carbon
Footprint Estimation From Bank Transaction
Classification Using Natural Language Processing
JAIMEGONZÁLEZ-GONZÁLEZ 1,SILVIAGARCÍA-MÉNDEZ 1,
FRANCISCODEARRIBA-PÉREZ 1,FRANCISCOJ.GONZÁLEZ-CASTAÑO 1,
ANDÓSCARBARBA-SEARA2
1InformationTechnologiesGroup,atlanTTic,TelecommunicationEngineeringSchool,UniversityofVigo,36310Vigo,Spain
2CoinScrapFinanceS.L.,36002Pontevedra,Spain
Correspondingauthor:SilviaGarcía-Méndez(sgarcia@gti.uvigo.es)
ThisworkwassupportedinpartbyXuntadeGalicia,Spain,underGrantED481B-2021-118andGrantED481B-2022-093;andinpartby
theSpanishNationalFundsthroughCentroParaelDesarrolloTecnológicoIndustrial(CenterforIndustrialTechnologicalDevelopment)
underProjectEXP00146826/IDI-20220298.
ABSTRACT Concernsabouttheeffectofgreenhousegaseshavemotivatedthedevelopmentofcertification
protocolstoquantifytheindustrialcarbonfootprint(cf).Theseprotocolsaremanual,work-intensive,and
expensive.Alloftheabovehaveledtoashifttowardsautomaticdata-drivenapproachestoestimatethecf,
includingMachineLearning(ml)solutions.Unfortunately,asinothersectorsofinterest,thedecision-making
processesinvolvedinthesesolutionslacktransparencyfromtheenduser’spointofview,whomustblindly
trust their outcomes compared to intelligible traditional manual approaches. In this research, manual and
automaticmethodologiesforcfestimationwerereviewed,takingintoaccounttheirtransparencylimitations.
Thisanalysisledtotheproposalofanewexplainablemlsolutionforautomaticcfcalculationsthroughbank
transactionclassification.Considerationshouldbegiventothefactthatnopreviousresearchhasconsidered
theexplainabilityofbanktransactionclassificationforthispurpose.Forclassification,differentmlmodels
have been employed based on their promising performance in similar problems in the literature, such as
SupportVectorMachine,RandomForest,andRecursiveNeuralNetworks.Theresultsobtainedwereinthe
90%rangeforaccuracy,precision,andrecallevaluationmetrics.Fromtheirdecisionpaths,theproposed
solution estimates the co emissions associated with bank transactions. The explainability methodology
2
is based on an agnostic evaluation of the influence of the input terms extracted from the descriptions of
transactionsusinglocallyinterpretablemodels.Theexplainabilitytermswereautomaticallyvalidatedusing
asimilaritymetricoverthedescriptionsofthetargetcategories.Conclusively,theexplanationperformance
is satisfactory in terms of the proximity of the explanations to the associated activity sector descriptions,
endorsingthetrustworthinessoftheprocessforahumanoperatorandendusers.
INDEX TERMS Explainableartificialintelligence,machinelearning,naturallanguageprocessing,carbon
footprint,banking.
I. INTRODUCTION signtheParisAgreement1in2015.Thisaccordexpressedthe
A. RESEARCHGAPANDMOTIVATION need for policies and regulations on ghg emissions such as
Concernsaboutclimaticchange[1],[2]relatedtotheincreas- carbondioxide(co 2 ).Theso-calledcarbonfootprint(cf)can
ingemissionofgreenhousegases(ghg)led187countriesto bedefinedastheamountofghgreleasedtotheatmosphere
1Available at https://unfccc.int/process-and-
The associate editor coordinating the review of this manuscript and
meetings/the-paris-agreement/the-paris-agreement,
approvingitforpublicationwasLiHe . November2022
ThisworkislicensedunderaCreativeCommonsAttribution-NonCommercial-NoDerivatives4.0License.
Formoreinformation,seehttps://creativecommons.org/licenses/by-nc-nd/4.0/
126326 VOLUME10,2022

J.González-Gonzálezetal.:ExplainableAutomaticIndustrialCarbonFootprintEstimation
throughoutthelifecycleofaproductorhumanactivity[3]. Regrettably, classification tasks performed by Machine
Over the years, there have been many proposals to estimate Learning (ml) models are often opaque [14], which may
thecfofdifferententities[4],includingindividuals,families, affect customer trust, especially in industrial contexts;
industries,andgeographicalbodiessuchascities[5]. hence, there is a growing interest in Explainable Artifi-
Themotivationsforthecalculationofcfarediverse,with cial Intelligence (xai). Explainability methodologies allow
compliance with environmental legislation and the certifi- for the extraction of intrinsic knowledge about the models’
| cation | of industrial | sustainability | (iso | 140642) | being two of | decisions.9 |     |     |     |
| ------ | ------------- | -------------- | ---- | ------- | ------------ | ----------- | --- | --- | --- |
the most relevant reasons. Another relevant inducement is Departingfromacategorizationmodelcombiningmlwith
self-checking to avoid environmental taxes [6] and attract NaturalLanguageProcessing(nlp)techniques,themaincon-
funding from ecologically-minded investors [7]. Moreover, tribution of this study lies in the proposal of the automatic
individuals,especiallyyoungpeople,havepressingconcerns explainabilityofcfestimationdecisions.Aspreviouslymen-
regardingtheeffectsofclimatechange[8],[9].Consequently, tioned, no authors have considered this aspect despite its
diversetrackingapplicationsallowenduserstoestimateand relevance, for example, to examine consultancy analytics.
reducetheircf[10]. The methodology extracts a set of relevant words for the
cf estimation solutions can be divided into manual and classifier,andthiswordsetisthenvalidatedwithasimilarity
automaticapproaches: metricbycomparingitwithdescriptionsofthecorresponding
activitysectors.
|     | Manual     | solutions.   | For     | individuals, | manual  |     |     |     |     |
| --- | ---------- | ------------ | ------- | ------------ | ------- | --- | --- | --- | --- |
|     | calculator | applications | require | estimates    | of con- |     |     |     |     |
sumption habits, travel, etc., as input data. These C. PAPERORGANIZATION
applicationsemploypredefinedformulae[11].For Theremainderofthispaperisorganizedasfollows.SectionII
industrialcertifications,thereexistconsultingcom-
reviewsthestateoftheartinbanktransactionclassification
|     | panies,suchasaecom3 |     | andkpmg4 |     |     |     |     |     |     |
| --- | ------------------- | --- | -------- | --- | --- | --- | --- | --- | --- |
whoseenviron- applied to cf calculation using ml models and focuses on
mentalservicesincludecfestimation. theexplainabilityfeature.SectionIIIdescribestheproposed
Automaticsolutions.SomeexamplesaretheDO,5
|     |     |     |     |     |     | architecture | for explainable | automatic industrial | cf estima- |
| --- | --- | --- | --- | --- | --- | ------------ | --------------- | -------------------- | ---------- |
Enfuce6 and Joro7 apps. Supervised approaches tion.SectionIVpresentstheexperimentaldata-setandimple-
|     | rely | on the Classification | of  | Individual | Consump- |     |     |     |     |
| --- | ---- | --------------------- | --- | ---------- | -------- | --- | --- | --- | --- |
mentationsused,alongwiththeresultsobtainedintermsof
(coicop8)
tion by Purpose by the United Nations classification and explainability. Finally, Section V summa-
or other categories of consumption habits. Bank rizestheconclusionsandproposesfutureresearch.
|     | transactions    | are useful | for        | individuals | useful [12]. |     |     |     |     |
| --- | --------------- | ---------- | ---------- | ----------- | ------------ | --- | --- | --- | --- |
|     | For industries, | little     | Enterprise | Resource    | Planning     |     |     |     |     |
II. RELATEDWORK
(erp)includescfestimation[13].
|     |     |     |     |     |     | Many previous | studies | have applied ml | in fields such as |
| --- | --- | --- | --- | --- | --- | ------------- | ------- | --------------- | ----------------- |
As far as we know, although automatic estimation of cf E-commerce[15],incidentmanagementininformationsys-
frombanktransactiondescriptionshasalreadybeenconsid- tems[16],andmedicalrecordanalysis[17].Infinance[18],
eredforendusers,itisanovelproblemintheindustry.In fact, [19],mlmodelshavebeenconsideredfordetectingfinancial
| the explainability |     | of industrial | cf estimation |     | based on the |               |                    |             |                  |
| ------------------ | --- | ------------- | ------------- | --- | ------------ | ------------- | ------------------ | ----------- | ---------------- |
|                    |     |               |               |     |              | opportunities | in social networks | [20], fraud | [21], [22], mar- |
automaticclassificationofbanktransactionshasnotyetbeen ket sentiment [23], risk [24], accounting [25], and financial
consideredinpreviousresearch,assupportedbythestate-of- transactionclassification[26].
the-artdiscussioninSectionII.
|     |     |     |     |     |     | In particular, | bank transaction | classification | is a type of |
| --- | --- | --- | --- | --- | --- | -------------- | ---------------- | -------------- | ------------ |
short-textclassificationthatwasalreadycoveredinourpre-
B. CONTRIBUTION vious work [27]. The latter topic has been applied to prob-
In this paper, we propose an explainable automatic solution lems among those in which intelligent budget management
forindustrialcfestimationbasedonasupervisedbanktrans- deservesattention[28],[29],[30].
action classification model. The training set was labeled as Nevertheless, no previous work on bank transaction clas-
coicopclasses. sification had an xai perspective (with the sole exception
|     |     |     |     |     |     | of Kotios | et al. [31], although | it did not | involve any nlp |
| --- | --- | --- | --- | --- | --- | --------- | --------------------- | ---------- | --------------- |
2Availableathttps://www.iso.org/standard/66453.html, methodology)norconsideredindustrialcfestimation.
November2022 Thebaseclassificationmethodologiesinvolvedarenumer-
3Available
|     |     | at  | https://aecom.com/services/ |     |     |     |     |     |     |
| --- | --- | --- | --------------------------- | --- | --- | --- | --- | --- | --- |
environmental-services,November2022 ous and include simple Naive Bayes classifiers [32], super-
4Available https://home.kpmg/xx/en/home/insights/ visedlearningmodelssuchasRandomForests(rf)[33],[34],
at
2020/12/environmental-social-governance-esg-and- and Support Vector Machine (svm) [35], [36], along with
sustainability.html,November2022
morecomplexapproachesbasedonDeepLearning(dl)and
| 5Available | at  | https://www.diva-portal.org/smash/get/ |     |     |     |     |     |     |     |
| ---------- | --- | -------------------------------------- | --- | --- | --- | --- | --- | --- | --- |
NeuralNetworks(nn)[37],[38].
diva2:1604075/FULLTEXT01.pdf,November2022
6Availableathttps://enfuce.com,November2022
7Availableathttps://www.joro.app,November2022
8Available at https://unstats.un.org/unsd/class/ 9Available at https://www.darpa.mil/program/
revisions/coicop_revision.asp,November2022 explainable-artificial-intelligence,November2022
| VOLUME10,2022 |     |     |     |     |     |     |     |     | 126327 |
| ------------- | --- | --- | --- | --- | --- | --- | --- | --- | ------ |

J.González-Gonzálezetal.:ExplainableAutomaticIndustrialCarbonFootprintEstimation
Thefirstsolutionsforcfestimationtypicallyfollowofficial processingpipeline,whiletheframesinbluerepresentexter-
protocols and practices10 and rely on manual calculations nal sources. Gray blocks correspond to higher-level tasks,
[11],[39].Theseprotocolsaretimeconsumingandexpensive as described in the independent subsections. This section
toapplyattheindustriallevel.Morerecentsolutionsoriented aimstoprovideaconceptualperspective.Detailedimplemen-
to end users have performed automatic cf estimation from tationsaredescribedinSectionIV.
banktransactions[12]andemployedsocialnetworking[40] In summary, the classification module labels the bank
tofosteruserengagement[41]. transactionsusedtoestimatethecf.Then,theexplainability
End users are mainly motivated by environmental aware- module automatically generates and validates the descrip-
ness and may be less concerned about the decision trans- tionsassociatedwiththeclassifierdecisions.
parencyofsolutions.Conversely,industrialusersmayobtain
important advantages from the application of automatic A. PRE-PROCESSING
| methodologies |     | based on | enterprise | data, | but solution | trans- |              |      |     |            |     |                    |      |
| ------------- | --- | -------- | ---------- | ----- | ------------ | ------ | ------------ | ---- | --- | ---------- | --- | ------------------ | ---- |
|               |     |          |            |       |              |        | The features | used | as  | input data | for | the classification | task |
parencymustbeprovided.Inthisregard,theincorporationof wereengineeredfromtextualbanktransactiondata.Forthis
aiinIndustry4.0hasboostedtheapplicationofxaistrategies
|                                                     |     |     |     |     |     |     | purpose,    | the text | was | processed | using | the following | nlp |
| --------------------------------------------------- | --- | --- | --- | --- | --- | --- | ----------- | -------- | --- | --------- | ----- | ------------- | --- |
| inrecentyears[42],[43]toshedsomelightonthedecisions |     |     |     |     |     |     | techniques: |          |     |           |       |               |     |
ofautomaticallysupervised[44]andunsupervised[45],[46]
|     |     |     |     |     |     |     | • Numbers’ |     | removal. | Bank | textual | data usually | contain |
| --- | --- | --- | --- | --- | --- | --- | ---------- | --- | -------- | ---- | ------- | ------------ | ------- |
learningmodels.Furthermore,explainabilityallowsthepre-
|     |     |     |     |     |     |     | quantitative |     | information |     | such as | the receiver’s | bank |
| --- | --- | --- | --- | --- | --- | --- | ------------ | --- | ----------- | --- | ------- | -------------- | ---- |
dictionofbehaviorofthesealgorithms[47].
account,receiptnumber,andproductcodes.Thesenum-
|     | The existence | of different |     | explainability |     | approaches is |      |               |     |            |     |                |          |
| --- | ------------- | ------------ | --- | -------------- | --- | ------------- | ---- | ------------- | --- | ---------- | --- | -------------- | -------- |
|     |               |              |     |                |     |               | bers | are typically |     | irrelevant | for | classification | purposes |
motivatedbythevarietyoflearningalgorithms:
becausetheyaretransactionspecific.
• Model-agnosticexplainability.Itconsidersmlmodels
• Terms’reconstruction.Asbankdescriptionsarerather
asblackboxesandappliesreverseengineeringtoinfer limitedinlength,relevanttermsmaybeabbreviatedor
theirbehavior.
|     |     |     |     |     |     |     | replaced | with | acronyms. |     | Thus, | these terms | need to be |
| --- | --- | --- | --- | --- | --- | --- | -------- | ---- | --------- | --- | ----- | ----------- | ---------- |
– Model induction. It consists of a counterfactual expandedintonaturallanguage.
studyoffeaturechanges[48]oracorrelationanal- Removalofsymbolsanddiacriticmarks.Allsymbols
•
ysisoffeaturesandoutputs[49],[50].
(e.g.,asterisks,hyphens,etc.),accents,diacriticmarks,
– Local explanation. It exploits local linear inter- anddiaereseswereremovedpriortotextlemmatization.
|     | pretable | models | that | match | the results | of those |        |       |     |      |          |       |           |
| --- | -------- | ------ | ---- | ----- | ----------- | -------- | ------ | ----- | --- | ---- | -------- | ----- | --------- |
|     |          |        |      |       |             |          | • Stop | words | and | code | removal. | Words | with lit- |
underanalysis[51],[52].Theselocalexplanations tle semantic load, such as determiners, prepositions,
can be enhanced using additional contextual or general-usageverbs,andalphanumericcodes(e.g.,cus-
semanticinformation[53].
tomeridentifiers),areremoved.
• Model-dependent explainability. It is based on the • Text lemmatization. Finally, the remaining terms are
inherentstructureofmlmodels. splitintotokensandconvertedintolemmas.
– Interpretablemodels.Certainlearningtechniques
areeasilyunderstandabletohumans,asinthecase B. CLASSIFICATIONMODULE
ofDecisionTree(dt)[54],[55],[56],rf[57],[58], Once the processed bank transaction descriptions contain
andsvm[59].
mostlysemanticallymeaningfulterms,theclassificationtask
|     | – Deep | explanations. | Variations |     | in dl | models allow | isperformed. |     |     |     |     |     |     |
| --- | ------ | ------------- | ---------- | --- | ----- | ------------ | ------------ | --- | --- | --- | --- | --- | --- |
thedeterminationofexplainablefeaturesbydecom-
posing the decision into the contributions of the 1) FEATUREENGINEERING
inputfeatures[60]orbyinferringthetransferfunc-
|     |     |     |     |     |     |     | Before | training | the | ml models, |     | the outcome | of the |
| --- | --- | --- | --- | --- | --- | --- | ------ | -------- | --- | ---------- | --- | ----------- | ------ |
tionbetweenlayers[61].
pre-processingmoduleisconvertedintovectors.Specifically,
Tothebestofourknowledge,thisstudyrepresentsthefirst the resulting terms of each bank transaction description are
| attempt | to  | explain industrial | cf  | estimations | from | the auto- |             |      |          |           |     |                |        |
| ------- | --- | ------------------ | --- | ----------- | ---- | --------- | ----------- | ---- | -------- | --------- | --- | -------------- | ------ |
|         |     |                    |     |             |      |           | transformed | into | wordgram | elements, |     | i.e., complete | words, |
maticclassificationofenterprisebanktransactions.Thepro- providedthatourfinalgoalisexplainability.
| posed | approach | takes | advantage | of the | different | ml models. |     |     |     |     |     |     |     |
| ----- | -------- | ----- | --------- | ------ | --------- | ---------- | --- | --- | --- | --- | --- | --- | --- |
Therefore,itfollowsamodel-agnosticexplainabilitystrategy. 2) CLASSIFICATION
Finally,anautomaticvalidationoftheexplanationqualityis
Transactionsareclassifiedusinglearningmodelsthatfulfill
provided.
|     |     |     |     |     |     |     | two requirements: |      | (i) | high classification |     | performance  | of the   |
| --- | --- | --- | --- | --- | --- | --- | ----------------- | ---- | --- | ------------------- | --- | ------------ | -------- |
|     |     |     |     |     |     |     | target labels     | used | for | cf estimation       |     | (see Section | IV), and |
III. METHODOLOGY
|     |     |     |     |     |     |     | (ii) straightforward |     | extraction |     | of self-explainable |     | features |
| --- | --- | --- | --- | --- | --- | --- | -------------------- | --- | ---------- | --- | ------------------- | --- | -------- |
Figure1illustratesthemodularschemeoftheproposedsolu-
fromthetrainedestimatorstofilltheexplainabilitytemplates.
| tion. | The frames | in white | represent | the | elements | within the |          |       |             |                   |     |          |        |
| ----- | ---------- | -------- | --------- | --- | -------- | ---------- | -------- | ----- | ----------- | ----------------- | --- | -------- | ------ |
|       |            |          |           |     |          |            | Based on | their | suitability | in explainability |     | research | in the |
literature,svm,rf,andRecursiveNeuralNetworks(rnn)were
|              | 10Available | at https://ghgprotocol.org/standards, |     |     |     |     |           |     |     |     |     |     |               |
| ------------ | ----------- | ------------------------------------- | --- | --- | --- | --- | --------- | --- | --- | --- | --- | --- | ------------- |
| November2022 |             |                                       |     |     |     |     | selected. |     |     |     |     |     |               |
| 126328       |             |                                       |     |     |     |     |           |     |     |     |     |     | VOLUME10,2022 |

J.González-Gonzálezetal.:ExplainableAutomaticIndustrialCarbonFootprintEstimation
FIGURE1. Systemarchitecture.
C. EXPLAINABILITYMODULE Additionally,thesimilaritycalculationrequiresthecollec-
The goal of the explainability methodology is to provide tionofrepresentativetermsforeachsector.Therefore,abag-
a human operator with an in-depth understanding of the of-words is generated per sector using descriptions of the
mostrepresentativeenterprises(seeSectionIV).
classificationprocessandvalidatethecorrespondingrelevant
explanationtermswithametricofproximitybetweenthese
| terms and | the descriptions | of the cf categories. | In  | principle, |     |     |     |     |     |
| --------- | ---------------- | --------------------- | --- | ---------- | --- | --- | --- | --- | --- |
2) MODEL-AGNOSTICFEATURESELECTION
the explanatory terms are those that are considered relevant Becausetheclassificationmoduleemploysdifferentmlmod-
duringtrainingbythemodel.
|     |     |     |     |     | els with | particular internal | structures, the | system follows | a   |
| --- | --- | --- | --- | --- | -------- | ------------------- | --------------- | -------------- | --- |
However,duetothecombinedeffectofpre-processingand
|     |     |     |     |     | model-agnostic | approach. | The latter method | creates a | local |
| --- | --- | --- | --- | --- | -------------- | --------- | ----------------- | --------- | ----- |
featureengineeringontheshortbanktransactiontextualdata,
surrogate[44]modeltoselecttheexplanatorytermsforeach
theexplanationsareenrichedasfollows:
banktransaction.Themodel-agnosticfeatureselectorrecur-
sivelyanalyzesthefeaturerelevancebyremovingparticular
|     |     |     |     |     | features | (the deeper the impact, | the higher | the relevance). |     |
| --- | --- | --- | --- | --- | -------- | ----------------------- | ---------- | --------------- | --- |
1) ENTERPRISETERMSELECTION
Ifanyenterprisenameispresentintheinitialbatchofexpla-
| Sometimes, | the descriptions | of transactions | include | explicit |     |     |     |     |     |
| ---------- | ---------------- | --------------- | ------- | -------- | --- | --- | --- | --- | --- |
references to particular enterprises. By identifying these nationtermsforabanktransaction,thoseexplanationterms
|             |              |                     |             |       | are expanded | using the descriptors | of the | enterprise, thanks |     |
| ----------- | ------------ | ------------------- | ----------- | ----- | ------------ | --------------------- | ------ | ------------------ | --- |
| enterprises | (see Section | IV), it is possible | to retrieve | their |              |                       |        |                    |     |
totheenterprisetermselector.
| descriptions   | from the | Internet, which  | are likely         | to be |     |     |     |     |     |
| -------------- | -------- | ---------------- | ------------------ | ----- | --- | --- | --- | --- | --- |
| representative | of their | activity sector. | These descriptions |       |     |     |     |     |     |
were pre-processed using the same method described in 3) SIMILARITY
Section III-A. The summarizer extracts all the nouns in the Giventheexpandedexplanationsets,theexplainabilitymod-
processed descriptions, and from these, the enterprise term ule computes a similarity metric between the explanation
selector takes the most representative ones, as detailed in set for each bank transaction and the bag-of-words of the
SectionIV-B4. economic sector, as selected by the classifier. Previous
| VOLUME10,2022 |     |     |     |     |     |     |     |     | 126329 |
| ------------- | --- | --- | --- | --- | --- | --- | --- | --- | ------ |

J.González-Gonzálezetal.:ExplainableAutomaticIndustrialCarbonFootprintEstimation
TABLE1. Distributionofsamplesinthedata-set.
Listing1. OriginaltemplateinSpanish.
Listing2. TemplatetranslatedtoEnglish.
authorshavealsousedcontextualandsemanticinformation • Carandtransport-flights(vuelos)(coicop7.3).Pur-
| toenhanceexplainability[53],[62]. |     |     |     |     |     |     | chaseofairlinetickets. |     |     |     |     |     |
| --------------------------------- | --- | --- | --- | --- | --- | --- | ---------------------- | --- | --- | --- | --- | --- |
• Enterpriseexpenditures-parcelandcourier(paque-
D. CARBONFOOTPRINTESTIMATION teríaymensajería)(coicop8.1).Paymentofpublicand
Once the transactions are classified, the proposed system privatepostalservices.
automaticallyobtainstheirestimatedcffromtheformulaeof • Commodities - water bill (agua) (coicop 4.4). Water
supplyreceipts.
thesectorstowhichtheyarepredictedtobelongandthebank
transactionamount,asdescribedinSectionIV-B5. • Commodities - electricity bill (electricidad) (coicop
4.5).Receiptofenergysupply.
IV. EXPERIMENTALEVALUATIONANDDISCUSSION • Commodities-gasbill(gas)(coicop4.5).Gassupply
| In this section, | we  | present | the | experimental | data-set | and | receipts. |     |     |     |     |     |
| ---------------- | --- | ------- | --- | ------------ | -------- | --- | --------- | --- | --- | --- | --- | --- |
technicalimplementations. Table 1 shows the distribution of transactions by eco-
|     |     |     |     |     |     |     | nomic sector. | Regarding | description | lengths, | for instance, |     |
| --- | --- | --- | --- | --- | --- | --- | ------------- | --------- | ----------- | -------- | ------------- | --- |
A. EXPERIMENTALDATA-SET the category commodities - electricity bill has, on average,
Thedata-setiscomposedof25,853banktransactionsissued 16 words per description, while car and transport - private
bySpanishbankscompiledbyCoinScrapFinanceSL.11Note
transporthasonly6wordsperdescription.Banktransaction
thatthisdata-setiscomparableinsizetothatinourprevious pre-processingreducestheoverallaveragedescriptionsizeto
studyonbanktransactionclassification[27]. 7words/50characters.
| It was | downsampled |     | using the | FuzzyWuzzy |     | Python |     |     |     |     |     |     |
| ------ | ----------- | --- | --------- | ---------- | --- | ------ | --- | --- | --- | --- | --- | --- |
library12tokeeponlythoseentriessufficientlyrepresentative
B. IMPLEMENTATIONS
anddistinguishable.Thosesampleswithdescriptionswitha Experimentswereperformedonacomputerwiththefollow-
similaritygreaterthan90%werediscarded.Thedownsam-
ingspecifications:
| pling process | resulted | in  | 2,619 transaction |     | archetypes, | with |     |     |     |     |     |     |
| ------------- | -------- | --- | ----------------- | --- | ----------- | ---- | --- | --- | --- | --- | --- | --- |
• OperatingSystem.Ubuntu20.04.3LTS64bits
anaveragelengthof10words/73characters.
The transactions are divided into three main categories: • Processor.IntelXeonPlatinum8375C2.9GHz
• RAM.64gbDDR4
carandtransport(automóvilyyransporte),enterpriseexpen-
Disk.500gbSSD
| ditures(gastosdeempresa),andcommodities(suministros), |     |     |     |     |     |     | •   |     |     |     |     |     |
| ----------------------------------------------------- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
andseveralsubcategories.Thus,amulti-classtransformation
Forclarity,thecorrespondingarchitectureinSectionIIIis
[63],[64]processisappliedtocombinethemaincategories indicatedforeachimplementationdescription.
| with their | respective | subcategories |     | to map | the | following |     |     |     |     |     |     |
| ---------- | ---------- | ------------- | --- | ------ | --- | --------- | --- | --- | --- | --- | --- | --- |
coicopcategories:
1) PRE-PROCESSINGMODULE(IMPLEMENTATIONOF
| • Car | and transport |     | - gas | stations | (gasolineras) |     |     |     |     |     |     |     |
| ----- | ------------- | --- | ----- | -------- | ------------- | --- | --- | --- | --- | --- | --- | --- |
SECTIONIII-A)
(coicop7.2).Paymentsingasstations.
|       |               |     |           |           |     |             | Diacritic | marks, numbers,            | identifiers, | and      | codes     | were |
| ----- | ------------- | --- | --------- | --------- | --- | ----------- | --------- | -------------------------- | ------------ | -------- | --------- | ---- |
| • Car | and transport |     | - private | transport |     | (transporte |           |                            |              |          |           |      |
|       |               |     |           |           |     |             | removed   | using regular expressions. |              | The same | technique | is   |
privado)(coicop7.3).Paymentsinprivatetransportser-
usedtoreconstructcommonacronyms,suchass.l.(Sociedad
vices.
Limitada,LimitedCompany)ore.s.(estacióndeservicio,gas
| • Car | and transport |     | - public | transport |     | (transporte |                |              |            |               |     |       |
| ----- | ------------- | --- | -------- | --------- | --- | ----------- | -------------- | ------------ | ---------- | ------------- | --- | ----- |
|       |               |     |          |           |     |             | station). Stop | word removal | (including | general-usage |     | verbs |
público)(coicop7.3).Purchaseofpublictransportation
suchas‘‘tobe’’and‘‘do’’)isbasedontheSpanishstopword
tickets(busesandtrains).
listfromtheNLTKPythonlibrary.13Fortokenizingpurposes,
|             |                                  |     |     |     |     |          | thesameNLTKPythonlibrary13 |     |     | wasusedandtheresulting |     |     |
| ----------- | -------------------------------- | --- | --- | --- | --- | -------- | -------------------------- | --- | --- | ---------------------- | --- | --- |
| 11Available | at https://coinscrapfinance.com, |     |     |     |     | November |                            |     |     |                        |     |     |
2022
| 12Available | at  | https://pypi.org/project/fuzzywuzzy, |     |     |     |     |     |     |     |     |     |     |
| ----------- | --- | ------------------------------------ | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
13Availableathttps://www.nltk.org,November2022
November2022
| 126330 |     |     |     |     |     |     |     |     |     |     | VOLUME10,2022 |     |
| ------ | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | ------------- | --- |

J.González-Gonzálezetal.:ExplainableAutomaticIndustrialCarbonFootprintEstimation
| tokens | were lemmatized |     | with | the spaCy | Python | library14 |     |     |     |     |     |     |     |     |
| ------ | --------------- | --- | ---- | --------- | ------ | --------- | --- | --- | --- | --- | --- | --- | --- | --- |
usingthees_core_news_smmodel.15
2) FEATUREENGINEERINGMODULE(IMPLEMENTATIONOF
SECTIONIII-B1)
| The selected | classification |     | models |     | require different | vec- |     |     |     |     |     |     |     |     |
| ------------ | -------------- | --- | ------ | --- | ----------------- | ---- | --- | --- | --- | --- | --- | --- | --- | --- |
| torization   | processes.     | For | the    | svc | and rf models,    | the  |     |     |     |     |     |     |     |     |
CountVectorizer16functionfromthescikit-learn
Python library was used for wordgram extraction. After Listing3. Hyperparameterselectionforsvc(bestvaluesinbold).
| the preliminary |     | tests, wordgrams |     | (one | word) and | biword- |     |     |     |     |     |     |     |     |
| --------------- | --- | ---------------- | --- | ---- | --------- | ------- | --- | --- | --- | --- | --- | --- | --- | --- |
grams(twowords)wereextracted.Thefeaturesweredown-
SelectPercentile17
| sampled | using |     |     |     | function | from the |     |     |     |     |     |     |     |     |
| ------- | ----- | --- | --- | --- | -------- | -------- | --- | --- | --- | --- | --- | --- | --- | --- |
scikit-learnPythonlibrarytokeepthosewiththehigh-
| est correlation |     | with the | target | variable. | Prior knowledge | led |     |     |     |     |     |     |     |     |
| --------------- | --- | -------- | ------ | --------- | --------------- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
ustoselectthechi-squaredscorefunction[20].
| For the | lstm | model, | the Tokenizer18 |     | function | from |     |     |     |     |     |     |     |     |
| ------- | ---- | ------ | --------------- | --- | -------- | ---- | --- | --- | --- | --- | --- | --- | --- | --- |
Listing4. Hyperparameterselectionforrf(bestvaluesinbold).
| the Keras | Python | library | was | used. | It converts | text into |     |     |     |     |     |     |     |     |
| --------- | ------ | ------- | --- | ----- | ----------- | --------- | --- | --- | --- | --- | --- | --- | --- | --- |
sequencesoftokenidentifiersembeddedinthenetwork.
|     |     |     |     |     |     |     | The | configuration |     | used | for | the lstm | model | included |
| --- | --- | --- | --- | --- | --- | --- | --- | ------------- | --- | ---- | --- | -------- | ----- | -------- |
3) CLASSIFICATIONMODULE(IMPLEMENTATIONOF the SpatialDropout24 layer (equivalent to Select-
SECTIONIII-B2) Percentile17).Thefinaldropoutpercentageappliedprior
toLSTMLayer22was20%ofthetensors.Thedroppercent-
Thefollowingmodelswereused:
LinearSupportVectorClassification(svc).Linear- ageofLSTMLayer22wasalso20%.
•
SVC19
|          | implementation |        | from | scikit-learn |              | Python |               |                                       |     |     |     |     |     |     |
| -------- | -------------- | ------ | ---- | ------------ | ------------ | ------ | ------------- | ------------------------------------- | --- | --- | --- | --- | --- | --- |
| library. |                |        |      |              |              |        | 4)            | EXPLAINABILITYMODULE(IMPLEMENTATIONOF |     |     |     |     |     |     |
| Random   |                | Forest |      | (rf).        | RandomForest |        |               |                                       |     |     |     |     |     |     |
| •        |                |        |      |              |              |        | SECTIONIII-C) |                                       |     |     |     |     |     |     |
Classifier20 implementation from the Theexplainabilitymethodologycomprisestwocomplemen-
scikit-learnPythonlibrary. tary processes: (i) the generation of explanations based on
• Long Short-Term Memory (lstm). The explainabilitytemplatesand(ii)thevalidationoftheseexpla-
Sequential21 structure and LSTMLayer22 were nations in terms of their consistency compared with human
implementedfromtheKerasPythonlibrary.
knowledgeaboutthetargetsectors.
Hyperparameter selection for the svc and rf models was The similarity metric of the validation process uses the
GridSearchCV23 bag-of-words from the target sectors and descriptors of the
| performed | using | the |     |     | function | of the |     |     |     |     |     |     |     |     |
| --------- | ----- | --- | --- | --- | -------- | ------ | --- | --- | --- | --- | --- | --- | --- | --- |
scikit-learnPythonlibrary.Listings3and4detailthe enterprisesintheexperimentaldata-setasinput.Forthefor-
hyperparameterrangesandthefinalchoices,respectively. merelement,CoinScrapFinances.l.providedacorporatelex-
icon25createdfromthedescriptionsofthetopsixenterprises
14Availableathttps://spacy.io,November2022
|     |     |     |     |     |     |     | of  | each target | sector, | with | ten representative |     | nouns | and five |
| --- | --- | --- | --- | --- | --- | --- | --- | ----------- | ------- | ---- | ------------------ | --- | ----- | -------- |
15Available
at https://spacy.io/models/es#es_core_ representative verbs each. Conversely, Spanish companies’
news_sm,November2022
|     |     |     |     |     |     |     | names26 |     |     | descriptions27 |     |     |     |     |
| --- | --- | --- | --- | --- | --- | --- | ------- | --- | --- | -------------- | --- | --- | --- | --- |
16Available https://scikit-learn.org/stable/ and their were extracted from the
at
| modules/generated/sklearn.feature_extraction.text. |     |                                     |     |     |     |     | Internet. |            |            |               |     |         |            |              |
| -------------------------------------------------- | --- | ----------------------------------- | --- | --- | --- | --- | --------- | ---------- | ---------- | ------------- | --- | ------- | ---------- | ------------ |
| CountVectorizer.html,November2022                  |     |                                     |     |     |     |     |           | enterprise |            | term selector |     |         |            |              |
|                                                    |     |                                     |     |     |     |     | The       |            |            |               |     | chooses | up         | to ten terms |
| 17Available                                        |     | at https://scikit-learn.org/stable/ |     |     |     |     |           |            |            |               |     |         |            |              |
|                                                    |     |                                     |     |     |     |     | from      | each       | summarized | description   |     | of an   | enterprise | in the       |
modules/generated/sklearn.feature_selectio.
|     |     |     |     |     |     |     | data-set. | The | summarizer |     | followed | the | same | steps as the |
| --- | --- | --- | --- | --- | --- | --- | --------- | --- | ---------- | --- | -------- | --- | ---- | ------------ |
SelectPercentile.html,November2022
18Available
at https://www.tensorflow.org/api_docs/ pre-processing module by removing stop words, common
python/tf/keras/preprocessing/text/Tokenizer,
verbs,numbers,andcodes.Thesystemcreatesalistofwords
November2022
|             |     |                                     |     |     |     |     | for | each enterprise |     | from the | resulting | list | of lemmas. | If the |
| ----------- | --- | ----------------------------------- | --- | --- | --- | --- | --- | --------------- | --- | -------- | --------- | ---- | ---------- | ------ |
| 19Available |     | at https://scikit-learn.org/stable/ |     |     |     |     |     |                 |     |          |           |      |            |        |
modules/generated/sklearn.svm.LinearSVC.html,
| November2022 |     |     |     |     |     |     | 24Available |     |     | at  | https://keras.io/api/layers/ |     |     |     |
| ------------ | --- | --- | --- | --- | --- | --- | ----------- | --- | --- | --- | ---------------------------- | --- | --- | --- |
20Available at https://scikit-learn.org/ regularization_layers/spatial_dropout1d, November
| stable/modules/generated/sklearn.ensemble. |     |     |     |     |     |     | 2022 |     |     |     |     |     |     |     |
| ------------------------------------------ | --- | --- | --- | --- | --- | --- | ---- | --- | --- | --- | --- | --- | --- | --- |
RandomForestClassifier.html,November2022 25Availableathttps://docs.google.com/spreadsheets/d/
21Available
at https://keras.io/api/models/sequential, 1Tq2l9An6DybVTHig_5O_5_KN-0VucgjSFT8wGQluahc/edit?
| November2022 |     |     |     |     |     |     | usp=sharing,November2022 |     |     |     |     |     |     |     |
| ------------ | --- | --- | --- | --- | --- | --- | ------------------------ | --- | --- | --- | --- | --- | --- | --- |
22Available at https://keras.io/api/layers/recurrent_ 26Available at https://guiaempresas.universia.es/
| layers/lstm,November2022 |     |     |     |     |     |     | localidad/MADRID,November2022 |     |     |     |     |     |     |     |
| ------------------------ | --- | --- | --- | --- | --- | --- | ----------------------------- | --- | --- | --- | --- | --- | --- | --- |
23Available at https://scikit-learn.org/stable/ 27Availableathttps://docs.google.com/spreadsheets/d/
modules/generated/sklearn.model_selection. 1SNT4avp9ki4beD6tYCH27zE6FQpsQUXTdH5vuLVF0yc/edit?
| GridSearchCV.html,November2022 |     |     |     |     |     |     | usp=sharing,November2022 |     |     |     |     |     |     |        |
| ------------------------------ | --- | --- | --- | --- | --- | --- | ------------------------ | --- | --- | --- | --- | --- | --- | ------ |
| VOLUME10,2022                  |     |     |     |     |     |     |                          |     |     |     |     |     |     | 126331 |

J.González-Gonzálezetal.:ExplainableAutomaticIndustrialCarbonFootprintEstimation
listcontainsmorethantenterms,onlythetenmostfrequent travel distance. The emission factor for the transporta-
| termsareretained. |     |     |     |     |     |     |     | tionmeansconsideredis(cid:15) |     |     |     | .   |     |     |     |
| ----------------- | --- | --- | --- | --- | --- | --- | --- | ----------------------------- | --- | --- | --- | --- | --- | --- | --- |
pt
| The model-agnostic |     |     | feature | selector | performs |     | recursive |     |     |     |     | p         |     |     |     |
| ------------------ | --- | --- | ------- | -------- | -------- | --- | --------- | --- | --- | --- | --- | --------- | --- | --- | --- |
|                    |     |     |         |          |          |     |           |     |     |     | =   | ·(cid:15) |     |     |     |
feature selection tests using the lime28 Python library given CF pt pt (3)
avp
pt
| its wide | acceptance |     | in the | literature | [44]. | As  | previously |     |     |     |     |     |     |     |     |
| -------- | ---------- | --- | ------ | ---------- | ----- | --- | ---------- | --- | --- | --- | --- | --- | --- | --- | --- |
Carandtransport-flights.Inthissector,thepriceper
| explained,thepreviousfeaturesareenrichedwiththeenter- |     |     |     |     |     |     |     | •   |     |     |     |     |     |     |     |
| ----------------------------------------------------- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
prisedescriptorsobtainedbytheenterprisetermselectorin kilometeravp mustbeaveraged,asitvariesdepending
fl
ontheairlineandplanemodel.Giventhisestimateand
casethebankdescriptioncontainsthenameofacompanyto
generatetheexplanationsets. the payment amount p, we calculate the co 2 emission
fromthecorrespondingtraveldistanceandtheemission
Forsimilaritymetricsbetweengroupsofterms,weconsid-
|                                                         |     |     |     |     |     |     |     | factorforacommercialaircraft(cid:15) |     |     |     |     | .   |     |     |
| ------------------------------------------------------- | --- | --- | --- | --- | --- | --- | --- | ------------------------------------ | --- | --- | --- | --- | --- | --- | --- |
| eredtwodifferentapproaches:(i)Jaccardsimilarityasabase- |     |     |     |     |     |     |     |                                      |     |     |     | fl  |     |     |     |
line [65], [66], and (ii) our own sophisticated metric based p
|                                                     |     |     |     |     |     |     |     |     |     |     | =   | ·(cid:15) |     |     |     |
| --------------------------------------------------- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --------- | --- | --- | --- |
|                                                     |     |     |     |     |     |     |     |     |     | CF  | fl  |           | fl  |     | (4) |
| onlexicalandsemanticproximity[67].Thecosinedistance |     |     |     |     |     |     |     |     |     |     |     | avp       |     |     |     |
fl
wasdiscardedprovidedthatthetermsinthedescriptionshad
|            |           |     |         |            |         |     |            | Enterprise |           | expenditures |     | - parcel        | and | courier. |        |
| ---------- | --------- | --- | ------- | ---------- | ------- | --- | ---------- | ---------- | --------- | ------------ | --- | --------------- | --- | -------- | ------ |
|            |           |     |         |            |         |     |            | •          |           |              |     |                 |     |          | Both   |
| no logical | ordering. |     | Using a | similarity | metric, |     | the system |            |           |              |     |                 |     |          |        |
|            |           |     |         |            |         |     |            | private    | companies |              | and | public entities |     | record   | parcel |
calculatesthesimilaritiesbetweenenrichedbanktransaction
|                                                        |            |     |        |          |         |     |          | transport | costs | per      | kilometer | avp    | on a  | yearly      | basis. |
| ------------------------------------------------------ | ---------- | --- | ------ | -------- | ------- | --- | -------- | --------- | ----- | -------- | --------- | ------ | ----- | ----------- | ------ |
| explanationsandthebag-of-wordsofthetargetsectorssothat |            |     |        |          |         |     |          |           |       |          |           |        | pc    |             |        |
|                                                        |            |     |        |          |         |     |          | From      | these | data and | the       | amount | p, it | is possible | to     |
| the highest                                            | similarity |     | can be | expected | between | an  | enriched |           |       |          |           |        |       |             |        |
estimatetheshipmentdistanceand,therefore,itscffrom
explanationofabanktransactionanditstargetsectoraccord-
|                               |     |     |     |     |     |     |     | theemissionfactor(cid:15) |     |     | .   |     |     |     |     |
| ----------------------------- | --- | --- | --- | --- | --- | --- | --- | ------------------------- | --- | --- | --- | --- | --- | --- | --- |
| ingtotheclassificationmodule. |     |     |     |     |     |     |     |                           |     |     | pc  |     |     |     |     |
p
|                                           |     |     |     |     |     |     |     |     |     |     | =   | ·(cid:15) |     |     |     |
| ----------------------------------------- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --------- | --- | --- | --- |
|                                           |     |     |     |     |     |     |     |     |     | CF  | pc  |           | pc  |     | (5) |
| 5) CARBONFOOTPRINTMODULE(IMPLEMENTATIONOF |     |     |     |     |     |     |     |     |     |     |     | avp       |     |     |     |
pc
SECTIONIV-B5)
|            |          |         |           |                 |     |         |          | • Commodities |     | - water   | bill.  | Unlike      | the rest | of the    | bank |
| ---------- | -------- | ------- | --------- | --------------- | --- | ------- | -------- | ------------- | --- | --------- | ------ | ----------- | -------- | --------- | ---- |
| The cf,    | that is, | the ghg | emissions | associated      |     | with    | a trans- |               |     |           |        |             |          |           |      |
|            |          |         |           |                 |     |         |          | transactions, |     | for water | bills, | we          | do not   | calculate | ghg  |
| action, is | directly | related | to        | the transaction |     | amount. | The      |               |     |           |        |             |          |           |      |
|            |          |         |           |                 |     |         |          | emissions     |     | but the   | total  | consumption | of       | water     | TWC, |
conversionestimatedependsonthesector:
|                                  |          |      |        |         |          |             |        | whichdependsontheaveragepriceoftheserviceavp |     |     |     |     |     |     | w   |
| -------------------------------- | -------- | ---- | ------ | ------- | -------- | ----------- | ------ | -------------------------------------------- | --- | --- | --- | --- | --- | --- | --- |
| • Carandtransport-gasstations.co |          |      |        |         |          | emissionsCF |        |                                              |     |     |     |     |     |     |     |
|                                  |          |      |        |         |          | 2           | gs     | andtheamountpaidp.                           |     |     |     |     |     |     |     |
| depend                           | on       | fuel | volume | and the | emission | factor      | of the |                                              |     |     |     |     |     |     |     |
|                                  | (cid:15) |      |        |         |          |             |        |                                              |     |     |     | p   |     |     |     |
fuel f . As bank transactions do not include the type TWC = (6)
| of fuel, | the | emission | factor | averages |     | the emissions | of  |     |     |     |     | avp w |     |     |     |
| -------- | --- | -------- | ------ | -------- | --- | ------------- | --- | --- | --- | --- | --- | ----- | --- | --- | --- |
gasoline and diesel. The volume is derived from the • Commodities-electricity/gasbill.Thedailypriceper
payment amount p and the average price per liter avp kWh kwp for the i-day of the last month is publicly
|     |     |     |     |     |     |     | f   |     | i   |     |     |     |     |     |     |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
offuelattransactiontime.
available.Theconsumptionofelectricityfromareceipt
p
= ·(cid:15) with amount p is estimated from the average price in
|     |     |     | CF gs |     | f   |     | (1) |     |     |     |     |     |     |     |     |
| --- | --- | --- | ----- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
avp the previous month. From the emission factor (cid:15) for
|     |     |     |     | f   |     |     |     |     |     |     |     |     |     |     | e   |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
electricity:
• Carandtransport-private/publictransport.Forpri-
|     |     |     |     |     |     |     |     |     |     | p   |     |     | p   |     |     |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
vatetransport,itisnecessarytofirstdistinguishbetween ·(cid:15) ·(cid:15)
|     |     |     |     |     |     |     |     |     | CF  | e = | e   | =   |     | e   | (7) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
taxi payments and other private services. We applied avp 1 (cid:80)m kwp
|                                                 |     |     |     |     |     |     |     |     |     |     | e   | i=1 | i   |     |     |
| ----------------------------------------------- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| thesekeywordsforthispurpose.Eachofthesealterna- |     |     |     |     |     |     |     |     |     |     |     | m   |     |     |     |
tiveshasitsownemissionfactor,(cid:15) and(cid:15) where m denotes the number of days in the previous
|           |     |                |     |      | t           | c ,respectively. |            |          |     |                                |     |     |     |     |     |
| --------- | --- | -------------- | --- | ---- | ----------- | ---------------- | ---------- | -------- | --- | ------------------------------ | --- | --- | --- | --- | --- |
|           |     |                |     |      |             |                  |            | month.CF |     | isdefinedsimilarlyfrom(cid:15) |     |     | .   |     |     |
| Distances |     | are calculated |     | from | the average |                  | prices per |          |     | g                              |     |     | g   |     |     |
kilometer of the region avp (for taxis) and avp (for Fromthepredictedclassoftransactionsandtheiramounts,
|         |            |     |     | t          |      |     | c          |            |          |     |       |          |           |        |     |
| ------- | ---------- | --- | --- | ---------- | ---- | --- | ---------- | ---------- | -------- | --- | ----- | -------- | --------- | ------ | --- |
|         |            |     |     |            |      |     |            | the system | presents | the | users | with the | estimated | volume | of  |
| private | companies) |     | and | the amount | paid | p.  | Prices are |            |          |     |       |          |           |        |     |
obtainedfromofficialandprivatepricinglists. ghgassociatedwitheachtransaction.Table2presentsexam-
Fortaxis: plesoftransactionsandtheircorrespondingco emissionsin
2
kilograms.Table3presentsanexampleofwaterconsumption
p
|     |     |     | CF   | =   | ·(cid:15) |     | (2) |                                     |     |     |     |     |     |     |     |
| --- | --- | --- | ---- | --- | --------- | --- | --- | ----------------------------------- | --- | --- | --- | --- | --- | --- | --- |
|     |     |     | taxi | avp | t         |     |     | estimatedfromawaterbilltransaction. |     |     |     |     |     |     |     |
t
| For | private | companies, |     | CF  | is defined | similarly | as  |     |     |     |     |     |     |     |     |
| --- | ------- | ---------- | --- | --- | ---------- | --------- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
comp
|     |       | (cid:15) |        |            |     |         |        | C. CLASSIFICATIONRESULTS |                  |     |      |        |          |     |        |
| --- | ----- | -------- | ------ | ---------- | --- | ------- | ------ | ------------------------ | ---------------- | --- | ---- | ------ | -------- | --- | ------ |
| avp | c and | c . For  | public | transport, | the | Spanish | Trans- |                          |                  |     |      |        |          |     |        |
|     |       |          |        |            |     |         |        | K-fold                   | cross-validation |     | is a | common | strategy | for | proper |
portMinistrypublishesaveragereferencesfortheprice
validationofpredictionresults[68].Inparticular,weapplied
| per | kilometer29 |     | avp . | co emissions |     | depend | on the |           |                   |     |     |                |     |      |     |
| --- | ----------- | --- | ----- | ------------ | --- | ------ | ------ | --------- | ----------------- | --- | --- | -------------- | --- | ---- | --- |
|     |             |     | pt    | 2            |     |        |        |           |                   |     |     |                |     |      |     |
|     |             |     |       |              |     |        |        | a 10-fold | cross-validation, |     |     | as implemented |     | with | the |
28Available at https://github.com/marcotcr/lime, Novem- StratifiedKFold30functionfromthescikit-learn
ber2022
29Available at https://www.mitma.gob.es/transporte- 30Available at https://scikit-learn.org/stable/
terrestre/observatorios/observatorios-y-estudios modules/generated/sklearn.feature_selection.
| (Spanish),November2022 |     |     |     |     |     |     |     | SelectPercentile.html,November2022 |     |     |     |     |     |               |     |
| ---------------------- | --- | --- | --- | --- | --- | --- | --- | ---------------------------------- | --- | --- | --- | --- | --- | ------------- | --- |
| 126332                 |     |     |     |     |     |     |     |                                    |     |     |     |     |     | VOLUME10,2022 |     |

J.González-Gonzálezetal.:ExplainableAutomaticIndustrialCarbonFootprintEstimation
TABLE2. Samplesofcfestimationresults.
TABLE3. Sampleofwaterconsumptionresults.
TABLE4. Classificationresults. TABLE5. Directlyvalidatedexplanationsfortherfclassifier.
|        |             |           |         |           |     |            | fewer terms        | per       | explanation |                 | than the | Jaccard   | distance to  |
| ------ | ----------- | --------- | ------- | --------- | --- | ---------- | ------------------ | --------- | ----------- | --------------- | -------- | --------- | ------------ |
|        |             |           |         |           |     |            | detect similarity, |           | and unlike  | the             | cosine   | distance, | it does not  |
| Python | library, to | calculate | average | accuracy, |     | precision, |                    |           |             |                 |          |           |              |
|        |             |           |         |           |     |            | rely on term       | ordering. |             | The differences |          | between   | the lists of |
recall,andtrainingtimes.Table4presentstheresultsforthe terms in the bank transaction explanation sets generated for
svc,rf,andlstmmodels.
bothmodelswereanalyzed.Forrf,eachexplanationsetcon-
| svc and | lstm achieved | over | 90 % | of accuracy. |     | svc is the |             |       |             |     |            |       |            |
| ------- | ------------- | ---- | ---- | ------------ | --- | ---------- | ----------- | ----- | ----------- | --- | ---------- | ----- | ---------- |
|         |               |      |      |              |     |            | tained 7.67 | words | on average, |     | while 8.19 | words | on average |
mosttime-efficientmodel.Regardingthetrainingtime,lstm
inthecaseofsvc.Similaritiesbetweenpairsofexplanation
| was the | most time-consuming. |     | rf  | is an intermediate |     | alter- |           |      |           |           |     |            |         |
| ------- | -------------------- | --- | --- | ------------------ | --- | ------ | --------- | ---- | --------- | --------- | --- | ---------- | ------- |
|         |                      |     |     |                    |     |        | sets were | then | computed, | resulting | in  | an overall | average |
native with slightly lower performance. Consequently, the similarityof0.79.Notethatthesimilarperformancesofboth
| best model, | considering        | the | performance-time |     | tradeoff, | was    |                      |         |       |         |                 |        |              |
| ----------- | ------------------ | --- | ---------------- | --- | --------- | ------ | -------------------- | ------- | ----- | ------- | --------------- | ------ | ------------ |
|             |                    |     |                  |     |           |        | classification       | methods |       | seem to | be related      | to the | similarity   |
| svc, but    | the classification |     | performance      | of  | the three | models |                      |         |       |         |                 |        |              |
|             |                    |     |                  |     |           |        | of their explanation |         | sets. | Thus,   | the explanation |        | potential is |
selectedwassimilar. consistentwiththeclassificationperformance.
|     |     |     |     |     |     |     | Table | 6 shows | the explanatory |     | performance |     | of both the |
| --- | --- | --- | --- | --- | --- | --- | ----- | ------- | --------------- | --- | ----------- | --- | ----------- |
D. EXPLAINABILITYPERFORMANCERESULTS models. For explanations that were neither obvious nor
Therfmodelwasusedasthebaselinebecauseofitsinferior directlyvalidated,weperformedasecondin-depthanalysisto
performance,whereassvcwasselectedasthetargetclassifier. checktheirtrustworthinessinahumanoperator.Wedivided
Table 5 shows the percentage of explanations for the rf thembymanualinspectioninto‘‘coherent’’(whenthehuman
baselinemodelthatcouldbevalidateddirectly.Anexplana- operator considered that the explanation was correct given
tionisconsideredtobedirectly‘‘validated’’whenthesector the predicted sector) and ‘‘ambiguous’’ (when the human
closesttoabanktransactionexplanationispredictedbythe operatorcouldnotdeterminefromtheexplanationitselfthe
classifier. sectorthatwaspredictedbytheclassifier).Those‘‘coherent’’
AsshowninTable5,Jaccardsimilarityresultsinalower explanations that contained the name of a company of the
percentage of directly validated explanations. Therefore, targetsectorareobviouslysatisfactoryand,assuch,theywere
intherestoftheexperiments,ourlinguisticmetric[67]was markedas‘‘obvious’’.Finally,weconsidered‘‘empty’’those
used. This metric is well-suited to our goal, as it requires explanationswhosesimilaritytoallsectorsiszero.Thismay
| VOLUME10,2022 |     |     |     |     |     |     |     |     |     |     |     |     | 126333 |
| ------------- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | ------ |

J.González-Gonzálezetal.:ExplainableAutomaticIndustrialCarbonFootprintEstimation
TABLE6. Explanationperformance.
beduetothefactthatlimefailstodetectanyrepresentative
termornoselectedexplanationtermisrepresentativeenough
(i.e.,simplealphanumericalcodes).Therefore,thelowerthe
percentageofambiguousandemptyexplanations,thehigher
thetrustworthiness.
Theexplanationperformancesweresimilar,whichresulted
fromtheuseofamodel-agnosticfeatureselectorandthesim-
ilar classification performance of both models. Satisfactory
explanations exceeded 70 %, of which approximately 60 %
could be automatically ‘‘validated’’. Regarding unsatisfac-
tory explanations (‘‘empty’’ and ‘‘ambiguous’’), only over
12 % are ‘‘empty’’ and offer no information to a human
operator.
Figure2illustratestheconfusionmatricesofthepredicted
sectors versus the most similar sector descriptions for the
direct validation. The main deviation occurred for gas sta-
tions,thecategorywith theshortestexplanations,withonly
four words on average. These are frequently closest to the
waterbillsectordescription.Othercommondeviationsexist
betweengasstationsandthegasbill,andbetweenthethree
categoriesofcommodities.
Mostofthesedeviationsdonotcorrespondtounsatisfac-
tory results from the perspective of a human operator. For
example,letusconsideranexplanationofabanktransaction
thatwaspredictedtobelongtothecommodities-electricity
billandwasclosertocarandtransport-publictransport.The
explanationsetcontainedtherelevantterms‘energia’,‘refer-
encia’,‘reciboreferencia’,‘recibo’,‘energy’,‘nxs’,‘nexus’,
‘mandato nxs’, ‘nexus energia’ and ‘referencia mandato’.
Itincludesseveralinstancesofthemeaningfultermsenergía
and energy that, in the Spanish context, are directly related
to the electricity sector from the perspective of the human
FIGURE2. Confusionmatrices,predictedsectorsversusmostsimilar
operator. sectordescriptions.
Thesystemfinallypresentsexplanationsbyfollowingthe
templateinListing2.Someexamplesare: • Enterprise expenditures - parcel and courier. The
• Carandtransport-gasstations.Theclassificationof classification of transaction 1269 into category enter-
transaction423intothecategorycarandtransport-gas priseexpenditures-parcelandcouriercanbeexplained
stationscanbeexplainedbyrelevantterms(indecreas- byrelevantterms(indecreasingorder):mail(correos),
ingorder):cedipsa,service(servicio),station(estacion), mail payment (pago correos), purchase (compra), pur-
gasstation(estacionservicio),payment(pago),cedipsa chasepayment(pagodecompra),mailleganes(correos
payment(pagocedipsa). leganes),card(tarjeta).
• Carandtransport-publictransport.Theclassifica- • Commodities-waterbill.Theclassificationoftransac-
tionoftransaction895intocategorycarandtransport tion1514intocategorycommodities-waterbillcanbe
- public transport can be explained by relevant terms explainedbyrelevantterms(indecreasingorder):water
(indecreasingorder):renfe,madrid,travelers(viajeros), (agua), water receipt (recibo agua), receipt (recibo),
renfecard(tarjetarenfe),renfetravelers(viajerosrenfe), reference order (referencia mandato), reference (refer-
purchase (compra), travelers app (viajeros app), app, encia), order (mandato), receipt reference (referencia
dev,card(tarjeta). recibo).
126334 VOLUME10,2022

J.González-Gonzálezetal.:ExplainableAutomaticIndustrialCarbonFootprintEstimation
Intheseexamples,thelistsofrelevanttermsintheexpla- V. CONCLUSION
nations are highly related to the respective sectors. These In this study, a novel explainable solution for automatic
includeelectricidad(electricity),gas(gas),agua(water),and industrial cf estimation from bank transactions is proposed,
estacion servicio (gas station). Two of the explanations are addressing the lack of transparent decision explanation
obviousbecausetheycontainthenamesofcompaniesoffer- methodologiesforthisproblem.Theexplanationisespecially
ing the services (Cedipsa and Renfe), but they also contain important to trust the outcome of automatic processes, for
other highly informative words. There are other generalist themtoreplacemoreexpensivealternatives,suchasconsul-
terms, such as recibo (receipt), compra (purchase), and tar- tancyanalytics.Indeed,eventhoughautomaticexplainability
jeta(card).Althoughtheydonotoccupythefirstpositionsin has not been tackled in this domain, the study of the state
theirrespectivelists,theyarelessrelevantthansector-specific ofthearthasalsorevealedthattherearenopreviousworks
terms. or existing commercial solutions for automatic industrial cf
estimationbasedonbanktransactions.
|     |     |     |     |     |     |     |     | The original |     | data source | includes | more | than 25,000 | bank |
| --- | --- | --- | --- | --- | --- | --- | --- | ------------ | --- | ----------- | -------- | ---- | ----------- | ---- |
E. COMPARISONWITHPRIORWORK
transactions.Itwasannotatedforclassificationusingcoicop
| The cf | estimation | has | recently | attracted | significant |     | com- |     |     |     |     |     |     |     |
| ------ | ---------- | --- | -------- | --------- | ----------- | --- | ---- | --- | --- | --- | --- | --- | --- | --- |
categories.
mercialinterest.However,therearefewautomaticsolutions
Theclassificationmethodologyforbanktransactionsfol-
| based on | bank | transaction | classification |     | in  | the literature |     |         |            |          |          |              |     |         |
| -------- | ---- | ----------- | -------------- | --- | --- | -------------- | --- | ------- | ---------- | -------- | -------- | ------------ | --- | ------- |
|          |      |             |                |     |     |                |     | lowed a | supervised | learning | strategy | by combining |     | ml with |
owingtoitsnovelty.
|     |     |     |     |     |     |     |     | nlp techniques |     | based on | our approach | in  | [27]. | The widely |
| --- | --- | --- | --- | --- | --- | --- | --- | -------------- | --- | -------- | ------------ | --- | ----- | ---------- |
Althoughafewpreviousstudieshaveappliedbanktrans-
|                       |     |     |            |     |        |                 |     | used svm, | rf, and | lstm | models | achieve satisfactory |     | perfor- |
| --------------------- | --- | --- | ---------- | --- | ------ | --------------- | --- | --------- | ------- | ---- | ------ | -------------------- | --- | ------- |
| action classification |     | to  | industrial | use | cases, | the classifica- |     |           |         |      |        |                      |     |         |
mancelevelsof90%forallmetrics,whichisconsistentwith
| tion performance |     | achieved | by  | other researchers |     | on different |     |     |     |     |     |     |     |     |
| ---------------- | --- | -------- | --- | ----------------- | --- | ------------ | --- | --- | --- | --- | --- | --- | --- | --- |
theresultsreportedbyotherauthorsintheliterature.
finance-relatedproblemsisillustrative.
Theagnosticexplanationmethodologyextractsasetofrel-
E.Folkestadetal.(2017)[28]exploiteddatafromDBpe-
dia31andWikidata32forbanktransactionclassification.They evantwordsfortheclassifier,andthisexplanationsetisthen
validatedwithasimilaritymetricbycomparingthesetwith
| reported | 83.48 | % accuracy | using | Logistic | Regression |     | (lr) |     |     |     |     |     |     |     |
| -------- | ----- | ---------- | ----- | -------- | ---------- | --- | ---- | --- | --- | --- | --- | --- | --- | --- |
thedescriptionsofcarbon-intensiveactivitysectors.Despite
(10.24%lessthanwithourapproach).Moreover,E.Vollset
thescarcityofcontentinindustrialbanktransactiondescrip-
| et al. (2017) | [29]      | augmented  |     | corporate        | data | with external |     |             |     |          |              |     |              |      |
| ------------- | --------- | ---------- | --- | ---------------- | ---- | ------------- | --- | ----------- | --- | -------- | ------------ | --- | ------------ | ---- |
|               |           |            |     |                  |      |               |     | tions, over | 70  | % of the | explanations | are | satisfactory | to a |
| semantic      | resources | to improve |     | bank transaction |      | classifica-   |     |             |     |          |              |     |              |      |
humanoperator,and60%havebeenautomaticallyvalidated
| tion. They | obtained | 92.97 | %   | accuracy | also with | lr (0.75 | %   |     |     |     |     |     |     |     |
| ---------- | -------- | ----- | --- | -------- | --------- | -------- | --- | --- | --- | --- | --- | --- | --- | --- |
fromcompanydescriptionsofthetargetsectors.Only15%
lessthanwithourapproach).
oftheexplanationswereambiguous,andthereisamarginfor
Thenlp-basedbudgetmanagementsolutionbyS.Allegue
|               |      |          |         |         |     |              |     | improvement | in  | the rest     | (which | we tag as     | ‘‘empty’’) | if side     |
| ------------- | ---- | -------- | ------- | ------- | --- | ------------ | --- | ----------- | --- | ------------ | ------ | ------------- | ---------- | ----------- |
| et al. (2021) | [30] | obtained | similar | results | to  | our approach |     |             |     |              |        |               |            |             |
|               |      |          |         |         |     |              |     | information | on  | alphanumeric | codes  | of industrial |            | activity is |
withanAdaptiveRandomForestmodel,withadifferenceof
|     |     |     |     |     |     |     |     | provided. | We consider | these | results | encouraging |     | for further |
| --- | --- | --- | --- | --- | --- | --- | --- | --------- | ----------- | ----- | ------- | ----------- | --- | ----------- |
only1%inprecision.
|         |           |     |          |     |           |            |     | study on | the automatic |     | explainability | of  | cf estimation | in  |
| ------- | --------- | --- | -------- | --- | --------- | ---------- | --- | -------- | ------------- | --- | -------------- | --- | ------------- | --- |
| The non | nlp-based | svm | solution | for | cash flow | prediction |     |          |               |     |                |     |               |     |
industrialsectors.
| for small | & medium | enterprises |     | by D. | Kotios | et al. | (2022) |     |     |     |     |     |     |     |
| --------- | -------- | ----------- | --- | ----- | ------ | ------ | ------ | --- | --- | --- | --- | --- | --- | --- |
Insummary,thehighlightsofthisstudyareasfollows:
[31]attainedaprecisionthatwasonly0.2%higherthanours,
aftertryingmanyotheralgorithms. The main contribution of this study is a novel solution
•
Given the similar performance of the existing solutions, for automatic industrial cf estimation from bank trans-
some contributions directly focus on the problem descrip- actionsbasedonsupervisedmlandnlptechniques.
tion. This is the case of the Svalna app by Andersson [12], The performance of the underlying bank transaction
•
an automatic carbon footprint estimation application based classificationmethodologyiscomparabletothatofother
on users’ transactions and environmental data from govern- researchers[30],[31].
mentalagencies.
|     |     |     |     |     |     |     |     | • Anexperimentaldata-setcomposedofmorethan25,000 |     |     |     |     |     |     |
| --- | --- | --- | --- | --- | --- | --- | --- | ------------------------------------------------ | --- | --- | --- | --- | --- | --- |
Thisapparentintrinsichighseparabilityoftheproblemis banktransactionswasused.
consistentwithourownresultswiththethreedifferentclassi- Over 70 % of the natural language explanations auto-
•
ficationmethodologies.Becausethefocusofourcontribution maticallygeneratedwithamodel-agnosticapproachare
is on classification explainability and given the small gap satisfactory for end users. Of these, 60 % have been
betweenmethodologiesinthisandotherworks,anddespite
automaticallyvalidated.Lessthan15%areambiguous.
| the advantages |     | of rf for | self-explainability |     |     | [69], we | have |           |     |             |     |             |     |            |
| -------------- | --- | --------- | ------------------- | --- | --- | -------- | ---- | --------- | --- | ----------- | --- | ----------- | --- | ---------- |
|                |     |           |                     |     |     |          |      | Regarding | the | limitations | of  | this study, | the | supervised |
appliedamodel-agnosticexplanationmethodology.
|     |     |     |     |     |     |     |     | classification | methodology |     | requires | manual | annotation | of  |
| --- | --- | --- | --- | --- | --- | --- | --- | -------------- | ----------- | --- | -------- | ------ | ---------- | --- |
banktransactionsfortrainingpurposes.Inaddition,thecat-
|     |     |     |     |     |     |     |     | egories  | for cf  | estimation | could              | change, | depending  | on the |
| --- | --- | --- | --- | --- | --- | --- | --- | -------- | ------- | ---------- | ------------------ | ------- | ---------- | ------ |
|     |     |     |     |     |     |     |     | activity | sector. | We chose   | a well-established |         | reference, | but    |
31Availableathttps://es.dbpedia.org,November2022 finerdetailsmayberequiredtoaccountforbusiness-specific
32Availableathttps://www.wikidata.org,November2022
expenses.
| VOLUME10,2022 |     |     |     |     |     |     |     |     |     |     |     |     |     | 126335 |
| ------------- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | ------ |

J.González-Gonzálezetal.:ExplainableAutomaticIndustrialCarbonFootprintEstimation
In future work, we plan to extend this research to other [15] L.Tan,M.Y.Li,andS.Kok,‘‘E-commerceproductcategorizationvia
main languages, enrich explanations with complementary machine translation,’’ ACM Trans. Manage. Inf. Syst., vol. 11, no. 3,
pp.1–14,Sep.2020.
enterprise information, and study the effect of hierarchical
[16] S.Silva,R.Pereira,andR.Ribeiro,‘‘Machinelearninginincidentcat-
methodologies on categorization by leveraging the relations egorizationautomation,’’inProc.13thIberianConf.Inf.Syst.Technol.
between target classes. We also plan to move towards a (CISTI),Jun.2018,pp.1–6.
semi-supervisedapproachbycombiningthecurrentsolution [17] G. T. Berge, O.-C. Granmo, T. O. Tveit, M. Goodwin, L. Jiao,
and B.V.Matheussen, ‘‘Using the Tsetlin machine to learn human-
witharulescheme,suchasthoseproposedbyotherauthors
interpretable rules for high-accuracy text categorization with medical
[31].Anotherpossiblelineofresearchisthecomparisonof applications,’’IEEEAccess,vol.7,pp.115134–115146,2019.
the model-agnostic approach to explainability with model- [18] J.Huang,J.Chai,andS.Cho,‘‘Deeplearninginfinanceandbanking:
Aliteraturereviewandclassification,’’FrontiersBus.Res.China,vol.14,
specificmethodologies.
no.1,p.13,Dec.2020.
[19] S.Rakshit,N.Clement,andN.R.Vajjhala,‘‘Exploratoryreviewofappli-
ACKNOWLEDGMENT cationsofmachinelearninginfinancesector,’’inAdvancesinDataScience
andManagement(LectureNotesonDataEngineeringandCommunica-
The authors would like to thank the indebted to CoinScrap
tionsTechnologies),vol.86.2022,Singapore:Springer,pp.119–126.
FinanceS.L.forprovidingthemwiththeexperimentaldata- [20] F. De Arriba-Perez, S. Garcia-Mendez, J. A. Regueiro-Janeiro, and
set. F.J.Gonzalez-Castano, ‘‘Detection of financial opportunities in micro-
bloggingdatawithastackedclassificationsystem,’’IEEEAccess,vol.8,
pp.215679–215690,2020.
REFERENCES [21] M.N.AshtianiandB.Raahemi,‘‘Intelligentfrauddetectioninfinancial
statementsusingmachinelearninganddatamining:Asystematicliterature
[1] ‘‘Thesustainabledevelopmentgoalsreport2021,’’UnitedNationsDept.
review,’’IEEEAccess,vol.10,pp.72504–72525,2022.
Econ.SocialAffairs,NewYork,NY,USA,Tech.Rep.,6,2021.
[22] C.S.KolliandU.D.Tatavarthi,‘‘Frauddetectioninbanktransactionwith
[2] V. Masson-Delmotte, P. Zhai, H.-O. Pörtner, D. Roberts, J. Skea,
wrappermodelandHarriswateroptimization-baseddeeprecurrentneural
P.R.Shukla, A. Pirani, W. Moufouma-Okia, C. Péan, R. Pidcock,
network,’’Kybernetes,vol.50,no.6,pp.1731–1750,Jul.2021.
S.Connors,J.B.R.Matthews,Y.Chen,X.Zhou,M.I.Gomis,E.Lonnoy,
T.Maycock,M.Tignor,andT.Waterfield,‘‘Globalwarmingof1.5◦C. [23] K.Mishev,A.Gjorgjevikj,I.Vodenska,L.T.Chitkushev,andD.Trajanov,
AnIPCCspecialreportontheimpactsofglobalwarmingof1.5◦Cabove ‘‘Evaluationofsentimentanalysisinfinance:Fromlexiconstotransform-
pre-industriallevelsandrelatedglobalgreenhousegasemissionpathways, ers,’’IEEEAccess,vol.8,pp.131662–131682,2020.
inthecontextofstrengtheningtheglobalresponsetothethreatofcli- [24] S.Bhatore,L.Mohan,andY.R.Reddy,‘‘Machinelearningtechniquesfor
matechange,sustainabledevelopment,andeffortstoeradicatepoverty,’’ creditriskevaluation:Asystematicliteraturereview,’’J.BankingFinancial
IntergovernmentalPanelClimateChange(IPCC),Geneva,Switzerland, Technol.,vol.4,no.1,pp.111–138,Apr.2020.
Tech.Rep.,15,2018. [25] C.Bardelli,A.Rondinelli,R.Vecchio,andS.Figini,‘‘Automaticelec-
[3] T.WiedmannandJ.Minx,‘‘Adefinitionof‘carbonfootprint,’’’inEco- tronicinvoiceclassificationusingmachinelearningmodels,’’Mach.Learn.
logicalEconomicsResearchTrends.Hauppauge,NY,USA:NovaScience Knowl.Extraction,vol.2,no.4,pp.617–629,Nov.2020.
Publishers,2008,ch.1,pp.1–11. [26] R.K.JørgensenandC.Igel,‘‘Machinelearningforfinancialtransaction
[4] D. Pandey, M. Agrawal, and J. S. Pandey, ‘‘Carbon footprint: Current classification across companies using character-level word embeddings
methodsofestimation,’’Environ.Monitor.Assessment,vol.178,nos.1–4, oftextfields,’’Intell.Syst.Accounting,FinanceManag.,vol.28,no.3,
pp.135–160,Jul.2011. pp.159–172,Jul.2021.
[5] L.Ionescu,‘‘Urbangreenhousegasaccountingfornet-zerocarboncities: [27] S. Garcia-Mendez, M. Fernandez-Gavilanes, J. Juncal-Martinez,
Sustainabledevelopment,renewableenergy,andclimatechange,’’Geopol- F.J.Gonzalez-Castano,andO.B.Seara,‘‘Identifyingbankingtransaction
itics,Hist.,Int.Relations,vol.14,no.1,pp.155–171,2022. descriptionsviasupportvectormachineshort-textclassificationbasedon
[6] N.Zhu,Y.Bu,M.Jin,andN.Mbroh,‘‘Greenfinancialbehaviorandgreen a specialized labelled corpus,’’ IEEE Access, vol. 8, pp.61642–61655,
developmentstrategyofChinesepowercompaniesinthecontextofcarbon 2020.
tax,’’J.CleanerProd.,vol.245,Feb.2020,Art.no.118908. [28] E.Folkestad,E.Vollset,M.R.Gallala,andJ.A.Gulla,‘‘Whyenriching
[7] L. Ionescu, ‘‘Transitioning to a low-carbon economy: Green financial bus.transactionswithlinkedopendatamaybeproblematicinclassification
behavior,climatechangemitigation,andenvironmentalenergysustain- tasks,’’inKnowledgeEngineeringandSemanticWeb(Communications
ability,’’Geopolitics,Hist.,Int.Relations,vol.13,no.1,pp.86–96,2021. in Computer and Information Science), vol. 786. Cham, Switzerland:
[8] T.L.Milfont,‘‘Theinterplaybetweenknowledge,perceivedefficacy,and Springer,2017,pp.347–362.
concernaboutglobalwarmingandclimatechange:Aone-yearlongitudinal [29] E.Vollset,E.Folkestad,M.R.Gallala,andJ.A.Gulla,‘‘Makinguseof
study,’’RiskAnal.,vol.32,no.6,pp.1003–1020,Jun.2012. externalcompanydatatoimprovetheclassificationofbanktransactions,’’
[9] S.Luís,C.-M.Vauclair,andM.L.Lima,‘‘Raisingawarenessofclimate inAdvancedDataMiningandApplications(LectureNotesinComputer
changecauses?Cross-nationalevidenceforthenormalizationofsocietal Science).vol.10604.Cham,Switzerland:Springer,2017,pp.767–780.
riskperceptionofclimatechange,’’Environ.Sci.Policy,vol.80,pp.74–81, [30] S.Allegue,T.Abdellatif,andH.ElAbed,‘‘SBM:Asmartbudgetman-
Feb.2018. agerinbankingusingmachinelearning,NLP,andNLU,’’Concurrency
[10] S.Hoffmann,W.Lasarov,andH.Reimers,‘‘Carbonfootprinttracking Comput.,Pract.Exper.,p.e6673,Oct.2021.
apps.Whatdrivesconsumersadoptionintention?’’Technol.Soc.,vol.69, [31] D. Kotios, G. Makridis, G. Fatouros, and D. Kyriazis, ‘‘Deep learning
May2022,Art.no.101956. enhancingbankingservices:Ahybridtransactionclassificationandcash
[11] J.Mulrow,K.Machaj,J.Deanes,andS.Derrible,‘‘Thestateofcarbon flowpredictionapproach,’’J.BigData,vol.9,no.1,pp.1–29,Oct.2022.
footprintcalculators:Anevaluationofcalculatordesignanduserinterac- [32] H.Gao,X.Zeng,andC.Yao,‘‘Applicationofimproveddistributednaive
tionfeatures,’’Sustain.Prod.Consumption,vol.18,pp.33–40,Apr.2019. Bayesianalgorithmsintextclassification,’’J.Supercomput.,vol.75,no.9,
[12] D.Andersson,‘‘Anovelapproachtocalculateindividualscarbonfoot- pp.5831–5847,Sep.2019.
prints using financial transaction data—App development and design,’’ [33] N.N.A.Sjarif,N.F.M.Azmi,S.Chuprat,H.M.Sarkan,Y.Yahya,and
J.CleanerProd.,vol.256,May2020,Art.no.120396. S.M.Sam,‘‘SMSspammessagedetectionusingtermfrequency-inverse
[13] D.ZvezdovandS.Hack,‘‘Carbonfootprintingoflargeproductportfo- documentfrequencyandrandomforestalgorithm,’’Proc.Comput.Sci.,
lios.Extendingtheuseofenterpriseresourceplanningsystemstocarbon vol.161,pp.509–515,Jan.2019.
information management,’’ J. Cleaner Prod., vol. 135, pp.1267–1275, [34] Z.TaşkinandU.Al,‘‘Acontent-basedcitationanalysisstudybasedontext
Nov.2016. categorization,’’Scientometrics,vol.114,no.1,pp.335–357,2018.
[14] P.C.Sen,M.Hajra,andM.Ghosh,‘‘Supervisedclassificationalgorithms [35] M.Goudjil,M.Koudil,M.Bedda,andN.Ghoggali,‘‘Anovelactivelearn-
inmachinelearning:Asurveyandreview,’’inEmergingTechnologyin ingmethodusingSVMfortextclassification,’’Int.J.Automat.Comput.,
ModellingandGraphics.Singapore:Springer,2020,pp.99–111. vol.15,no.3,pp.290–298,2018.
126336 VOLUME10,2022

J.González-Gonzálezetal.:ExplainableAutomaticIndustrialCarbonFootprintEstimation
[36] K.KimandS.Y.Zzang,‘‘Trigonometriccomparisonmeasure:Afeature [59] P. Ponte and R. G. Melko, ‘‘Kernel methods for interpretable machine
selection method for text categorization,’’ Data Knowl. Eng., vol. 119, learningoforderparameters,’’Phys.Rev.B,Condens.Matter,vol.96,
| pp.1–21,Jan.2019. |     |     |     |     |     |     | no20,2017,Art.no.205146. |     |     |     |     |     |     |     |
| ----------------- | --- | --- | --- | --- | --- | --- | ------------------------ | --- | --- | --- | --- | --- | --- | --- |
[37] R.Wang,Z.Li,J.Cao,T.Chen,andL.Wang,‘‘Convolutionalrecurrent [60] G.Montavon,S.Lapuschkin,A.Binder,W.Samek,andK.-R.Müller,
neuralnetworksfortextclassification,’’inProc.Int.JointConf.Neural ‘‘ExplainingnonlinearclassificationdecisionswithdeepTaylordecom-
Netw.,Jul.2019,pp.1–6. position,’’PatternRecognit.,vol.65,pp.211–222,May2017.
[38] H.A.AlmuzainiandA.M.Azmi,‘‘Impactofstemmingandwordembed- [61] S. Bach, A. Binder, G. Montavon, F. Klauschen, K.-R. Müller, and
ding on deep learning-based Arabic text categorization,’’IEEE Access, W.Samek,‘‘Onpixel-wiseexplanationsfornon-linearclassifierdecisions
vol.8,pp.127913–127928,2020. bylayer-wiserelevancepropagation,’’PLoSONE,vol.10,no.7,Jul.2015,
[39] C. Adewale, J. P. Reganold, S. Higgins, R. D. Evans, and Art.no.e0130140.
L.Carpenter-Boggs,‘‘Agriculturalcarbonfootprintisfarmspecific:Case [62] J.Rožanec,E.Trajkova,I.Novalija,P.Zajec,K.Kenda,B.Fortuna,and
study of two organic farms,’’ J. Cleaner Prod., vol. 229, pp.795–805, D.Mladenic,‘‘Enrichingartificialintelligenceexplanationswithknowl-
Aug.2019. edgefragments,’’FutureInternet,vol.14,no.5,p.134,Apr.2022.
[40] A.Biørn-Hansen,W.Barendregt,andD.Andersson,‘‘Introducingfinan- [63] R.B.Pereira,A.Plastino,B.Zadrozny,andL.H.C.Merschmann,‘‘Cat-
cialdataandgroupsinacarboncalculator:Issueswithtrustandoppor- egorizingfeatureselectionmethodsformulti-labelclassification,’’Artif.
tunitiesforsocialinteraction,’’inProc.7thInt.Conf.(ICT),Jun.2020, Intell.Rev.,vol.49,no.1,pp.57–78,2016.
pp.11–17. [64] A.N.Tarekegn,M.Giacobini,andK.Michalak,‘‘Areviewofmethods
[41] W.Barendregt,A.Biørn-Hansen,andD.Andersson,‘‘Usersexperiences for imbalanced multi-label classification,’’ Pattern Recognit., vol. 118,
withtheuseoftransactiondatatoestimateconsumption-basedemissions Oct.2021,Art.no.107965.
|     |     |     |     |     |     |     | [65] A. Jain, | A. Jain, | N. Chauhan, | V.  | Singh, and | N. Thakur, | ‘‘Information |     |
| --- | --- | --- | --- | --- | --- | --- | ------------- | -------- | ----------- | --- | ---------- | ---------- | ------------- | --- |
inacarboncalculator,’’Sustainability,vol.12,no.18,p.7777,Sep.2020.
[42] F.Emmert-Streib,O.Yli-Harja,andM.Dehmer,‘‘Explainableartificial retrieval using cosine and Jaccard similarity measures in vector space
intelligenceandmachinelearning:Arealityrootedperspective,’’WIREs model,’’Int.J.Comput.Appl.,vol.164,no.6,pp.28–30,Apr.2017.
DataMiningKnowl.Discovery,vol.10,no.6,p.e1368,Nov.2020. [66] R.SinghandS.Singh,‘‘Textsimilaritymeasuresinnewsarticlesbyvector
[43] I. Ahmed, G. Jeon, and F. Piccialli, ‘‘From artificial intelligence to spacemodelusingNLP,’’J.Inst.Eng.,Ser.B,vol.102,no.2,pp.329–338,
Apr.2021.
explainableartificialintelligenceinindustry4.0:Asurveyonwhat,how,
andwhere,’’IEEETrans.Ind.Informat.,vol.18,no.8,pp.5031–5042, [67] F. De Arriba-Pérez, S. García-Méndez, F. J. González-Castaño, and
Aug.2022. E.Costa-Montenegro,‘‘Automaticdetectionofcognitiveimpairmentin
[44] N.BurkartandM.F.Huber,‘‘Asurveyontheexplainabilityofsupervised elderlypeopleusinganentertainmentchatbotwithnaturallanguagepro-
machinelearning,’’J.Artif.Intell.Res.,vol.70,pp.245–317,Jan.2021. cessing capabilities,’’ J. Ambient Intell. Humanized Comput., pp.1–16,
Apr.2022.
[45] G.Montavon,J.Kauffmann,W.Samek,andK.-R.Müller,‘‘Explaining
thepredictionsofunsupervisedlearningmodels,’’inProc.Int.Workshop [68] T.Jiang,J.L.Gradus,andA.J.Rosellini,‘‘Supervisedmachinelearning:
ExtendingExplainableAIBeyondDeepModelsClassifiers.Vienna,Aus- Abriefprimer,’’Behav.Therapy,vol.51,no.5,pp.675–687,Sep.2020.
tria:Springer,2022,pp.117–138. [69] J. Wanner, L.-V. Herm, K. Heinrich, and C. Janiesch, ‘‘Stop ordering
[46] A. Heuillet, F. Couthouis, and N. Díaz-Rodríguez, ‘‘Explainability in machinelearningalgorithmsbytheirexplainability!Anempiricalinvesti-
gationofthetradeoffbetweenperformanceandexplainability,’’inRespon-
deepreinforcementlearning,’’Knowl.-BasedSyst.,vol.214,Feb.2021,
Art.no.106685. sible AI and Analytics for an Ethical and Inclusive Digitized Society
[47] D. Gunning and D. Aha, ‘‘DARPA’s explainable artificial intelligence (LectureNotesinComputerScience).Cham,Switzerland:Springer,2021,
| (XAI)program,’’AIMag.,vol.40,no.2,pp.44–58,Jun.2019. |     |     |     |     |     |     | pp.245–258. |     |     |     |     |     |     |     |
| ---------------------------------------------------- | --- | --- | --- | --- | --- | --- | ----------- | --- | --- | --- | --- | --- | --- | --- |
[48] S.Wachter,B.Mittelstadt,andC.Russell,‘‘Counterfactualexplanations
| without | opening the black | box: Automated | decisions |     | and the | GDPR,’’ |     |     |     |     |     |     |     |     |
| ------- | ----------------- | -------------- | --------- | --- | ------- | ------- | --- | --- | --- | --- | --- | --- | --- | --- |
HarvardJ.LawTechnol.,vol.31,no.2,pp.841–887,2018.
[49] A.Goldstein,A.Kapelner,J.Bleich,andE.Pitkin,‘‘Peekinginsidethe
blackbox:Visualizingstatisticallearningwithplotsofindividualcondi-
tionalexpectation,’’J.Comput.Graph.Statist.,vol.24,no.1,pp.44–65,
| 2015. |     |     |     |     |     |     |     |     | JAIME | GONZÁLEZ-GONZÁLEZ |     |     | received | the |
| ----- | --- | --- | --- | --- | --- | --- | --- | --- | ----- | ----------------- | --- | --- | -------- | --- |
[50] D.W.ApleyandJ.Zhu,‘‘Visualizingtheeffectsofpredictorvariablesin
|     |     |     |     |     |     |     |     |     | B.S. | degree | in telecommunication |     | technologies |     |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | ---- | ------ | -------------------- | --- | ------------ | --- |
blackboxsupervisedlearningmodels,’’J.Roy.Stat.Society,Ser.B,vol.82,
|     |     |     |     |     |     |     |     |     | engineering |     | and the M.S. | degree | in telecommu- |     |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | ----------- | --- | ------------ | ------ | ------------- | --- |
no.4,pp.1059–1086,Sep.2020.
nicationengineeringfromtheUniversityofVigo,
| [51] M. T. | Ribeiro, S. Singh, | and C. | Guestrin, ‘‘‘Why | should | I trust | you?’ |     |     |        |         |     |                     |     |       |
| ---------- | ------------------ | ------ | ---------------- | ------ | ------- | ----- | --- | --- | ------ | ------- | --- | ------------------- | --- | ----- |
|            |                    |        |                  |        |         |       |     |     | Spain, | in 2020 | and | 2022, respectively, |     | where |
Explainingthepredictionsofanyclassifier,’’inProc.ACMSIGKDDInt.
Conf.Knowl.DiscoveryDataMining,Aug.2016,pp.1135–1144. he is currently pursuing the Ph.D. degree with
[52] G. Plumb, D. Molitor, and A. Talwalkar, ‘‘Model agnostic supervised the Information Technologies Group. He is also
local explanations,’’ in Proc. Adv. Neural Inf. Process. Syst., 2018, a Researcher with the Information Technologies
| pp.2515–2524. |     |     |     |     |     |     |     |     | Group,UniversityofVigo.Hisresearchinterests |     |     |     |     |     |
| ------------- | --- | --- | --- | --- | --- | --- | --- | --- | ------------------------------------------- | --- | --- | --- | --- | --- |
[53] S.Kiefer,‘‘CaSE:Explainingtextclassificationsbyfusionoflocalsur- includethedevelopmentofmachinelearningsolu-
rogateexplanationmodelswithcontextualandsemanticknowledge,’’Inf. tions for automatic text classification and augmentative and alternative
| Fusion,vol.77,pp.184–195,Jan.2022. |                |               |          |         |              |     | communication. |     |     |     |     |     |     |     |
| ---------------------------------- | -------------- | ------------- | -------- | ------- | ------------ | --- | -------------- | --- | --- | --- | --- | --- | --- | --- |
| [54] O. Sagi                       | and L. Rokach, | ‘‘Explainable | decision | forest: | Transforming | a   |                |     |     |     |     |     |     |     |
decisionforestintoaninterpretabletree,’’Inf.Fusion,vol.61,pp.124–138,
Sep.2020.
[55] C.CousinsandM.Riondato,‘‘CaDET:Interpretableparametriccondi-
tionaldensityestimationwithdecisiontreesandforests,’’Mach.Learn.,
vol.108,nos.8–9,pp.1613–1634,Sep.2019.
| [56] Ö. Sürer, | D. W. Apley, | and E. C. | Malthouse, | ‘‘Coefficient | tree | regres- |     |     |        |               |     |          |     |           |
| -------------- | ------------ | --------- | ---------- | ------------- | ---- | ------- | --- | --- | ------ | ------------- | --- | -------- | --- | --------- |
|                |              |           |            |               |      |         |     |     | SILVIA | GARCÍA-MÉNDEZ |     | received |     | the Ph.D. |
sion:Fast,accurateandinterpretablepredictivemodeling,’’Mach.Learn.,
|     |     |     |     |     |     |     |     |     | degree | in information |     | and communication |     | tech- |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | ------ | -------------- | --- | ----------------- | --- | ----- |
pp.1–37,Nov.2021. nologies from the University of Vigo, in 2021.
| [57] M. P. | Neto and F. V. Paulovich, |     | ‘‘Explainable | matrix–visualization |     | for |     |     |     |     |     |     |     |     |
| ---------- | ------------------------- | --- | ------------- | -------------------- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
Since2015,shehasbeenworkingasaResearcher
| global | and local interpretability | of  | random forest | classification |     | ensem- |     |     |     |     |     |     |     |     |
| ------ | -------------------------- | --- | ------------- | -------------- | --- | ------ | --- | --- | --- | --- | --- | --- | --- | --- |
withtheInformationTechnologiesGroup,Univer-
bles,’’IEEETrans.Vis.Comput.Graphics,vol.27,no.2,pp.1427–1437,
|     |     |     |     |     |     |     |     |     | sity | of Vigo. | She is currently |     | collaborating | with |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | ---- | -------- | ---------------- | --- | ------------- | ---- |
Feb.2021.
foreignresearchcentersaspartofherpostdoctoral
| [58] S. Tandra | and A. Manashty, | ‘‘Probabilistic | feature | selection |     | for inter- |     |     |     |     |     |     |     |     |
| -------------- | ---------------- | --------------- | ------- | --------- | --- | ---------- | --- | --- | --- | --- | --- | --- | --- | --- |
pretablerandomforestmodel,’’inAdvancesinInformationandCommuni- stage.Herresearchinterestsincludenaturallan-
cation(AdvancesinIntelligentSystemsandComputing),vol.1364.Cham, guageprocessingtechniquesandmachinelearning
| Switzerland:Springer,2021,pp.707–718. |     |     |     |     |     |     |     |     | algorithms. |     |     |     |     |        |
| ------------------------------------- | --- | --- | --- | --- | --- | --- | --- | --- | ----------- | --- | --- | --- | --- | ------ |
| VOLUME10,2022                         |     |     |     |     |     |     |     |     |             |     |     |     |     | 126337 |

J.González-Gonzálezetal.:ExplainableAutomaticIndustrialCarbonFootprintEstimation
FRANCISCO DE ARRIBA-PÉREZ received the ÓSCARBARBA-SEARAreceivedtheB.S.degree
B.S. degree in telecommunication technologies incomputerscienceandtheM.S.degreeinsupe-
engineering, the M.S. degree in telecommunica- riorcomputerengineeringfromtheUniversityof
tion engineering, and the Ph.D. degree from the VigoandtheM.S.degreeine-commercefromthe
University of Vigo, Spain, in 2013, 2014, and PontificalUniversityofSalamanca.Heiscurrently
2019, respectively. He is currently a Researcher pursuingthePh.D.degreewiththeUniversityof
with the Information Technologies Group, Uni- Vigo.HehasworkedastheCTOortheTechnical
versityofVigo.Hisresearchinterestsincludethe Manager in several IT projects with more than
developmentofmachinelearningsolutionsfordif- 14 years of experience in the public and private
ferentdomains,suchasfinanceandhealth. sectors and in IT integrations with international
corporations, such as Mapfre, Caser, Abanca, Evo Banco, Vodafone, and
AON. He is currently the CTO of Two Initiatives in the fintech sector
involvingmachinelearningresearchfortheanalysisoffinancialandmarket-
relatedtexts.
FRANCISCOJ.GONZÁLEZ-CASTAÑOreceived
the B.S. degree from the University of Santiago
de Compostela, Spain, in 1990, and the Ph.D.
degreefromtheUniversityofVigo,Spain,in1998.
HeiscurrentlyaFullProfessorattheUniversityof
Vigo,whereheleadstheInformationTechnologies
Group.Hehasauthoredover100papersininter-
nationaljournalsinthefieldsoftelecommunica-
tionsandcomputerscienceandhasparticipatedin
severalrelevantnationalandinternationalprojects.
HeholdsthreeU.S.patents.
126338 VOLUME10,2022