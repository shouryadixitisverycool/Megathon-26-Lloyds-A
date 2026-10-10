|     | Leakage |     | and      | the | Reproducibility | Crisis           | in  | ML-based |     | Science |     |     |
| --- | ------- | --- | -------- | --- | --------------- | ---------------- | --- | -------- | --- | ------- | --- | --- |
|     |         |     |          |     | SayashKapoor1   | ArvindNarayanan1 |     |          |     |         |     |     |
|     |         |     | Abstract |     |                 | 1.Overview       |     |          |     |         |     |     |
Therehasbeenamarkedshifttowardstheparadigmofpre-
|     |        |         |          |      |         | dictive | modeling | across | quantitative | science | fields. | This |
| --- | ------ | ------- | -------- | ---- | ------- | ------- | -------- | ------ | ------------ | ------- | ------- | ---- |
| The | use of | machine | learning | (ML) | methods |         |          |        |              |         |         |      |
for prediction and forecasting has become shifthasbeenfacilitatedbythewidespreaduseofmachine
|                                          |     |     |     |     |      | learning | (ML) | methods. | However, | pitfalls | in using | ML  |
| ---------------------------------------- | --- | --- | --- | --- | ---- | -------- | ---- | -------- | -------- | -------- | -------- | --- |
| widespreadacrossthequantitativesciences. |     |     |     |     | How- |          |      |          |          |          |          |     |
ever,therearemanyknownmethodologicalpit- methodshaveledtoexaggeratedclaimsabouttheirperfor-
2202 luJ 41  ]GL.sc[  1v84070.7022:viXra
mance. Sucherrorscanleadtoafeedbackloopofoverop-
| falls, | including | data | leakage, | in ML-based | sci- |        |       |              |     |                       |     |     |
| ------ | --------- | ---- | -------- | ----------- | ---- | ------ | ----- | ------------ | --- | --------------------- | --- | --- |
|        |           |      |          |             |      | timism | about | the paradigm | of  | prediction—especially |     | as  |
ence. Inthispaper,wesystematicallyinvestigate
reproducibilityissuesinML-basedscience. We non-replicablepublicationstendtobecitedmoreoftenthan
|      |           |         |     |        |              | replicableones(Serra-Garcia&Gneezy,2021). |     |     |     |     | Itisthere- |     |
| ---- | --------- | ------- | --- | ------ | ------------ | ----------------------------------------- | --- | --- | --- | --- | ---------- | --- |
| show | that data | leakage | is  | indeed | a widespread |                                           |     |     |     |     |            |     |
problemandhasledtoseverereproducibilityfail- foreimportanttoexaminethereproducibilityoffindingsin
ures. Specifically,throughasurveyofliterature communitiesadoptingMLmethods.
inresearchcommunitiesthatadoptedMLmeth-
|      |         |           |       |        |           | Scope. | We focus | on reproducibility |     | issues | in ML-based |     |
| ---- | ------- | --------- | ----- | ------ | --------- | ------ | -------- | ------------------ | --- | ------ | ----------- | --- |
| ods, | we find | 17 fields | where | errors | have been |        |          |                    |     |        |             |     |
science,whichinvolvesmakingascientificclaimusingthe
found, collectively affecting 329 papers and in performanceoftheMLmodelasevidence. Thereisamuch
somecasesleadingtowildlyoveroptimisticcon-
betterknownreproducibilitycrisisinresearchthatusestra-
clusions. Basedonoursurvey,wepresentafine-
|     |     |     |     |     |     | ditional | statistical | methods | (Open | Science | Collaboration, |     |
| --- | --- | --- | --- | --- | --- | -------- | ----------- | ------- | ----- | ------- | -------------- | --- |
grainedtaxonomyof8typesofleakagethatrange
|     |     |     |     |     |     | 2015). | We also | situate our | work | in contrast | to other | ML  |
| --- | --- | --- | --- | --- | --- | ------ | ------- | ----------- | ---- | ----------- | -------- | --- |
fromtextbookerrorstoopenresearchproblems.
domains,suchasmethodsresearch(creatingandimproving
widely-applicableMLmethods),ethicsresearch(studying
We argue for fundamental methodological theethicalimplicationsofMLmethods), engineeringap-
changes to ML-based science so that cases of plications(buildingorimprovingaproductorservice),and
leakagecanbecaughtbeforepublication. Tothat modelingcontests(improvingpredictiveperformanceona
end,weproposemodelinfosheetsforreporting fixeddatasetcreatedbyanindependentthirdparty). Investi-
scientificclaimsbasedonMLmodelsthatwould gatingthevalidityofclaimsinalloftheseareasisimportant,
addressalltypesofleakageidentifiedinoursur- andthereisongoingworktoaddressreproducibilityissues
vey. Toinvestigatetheimpactofreproducibility inthesedomains(Hullmanetal.,2022;Pineauetal.,2020;
ErikGundersen,2021;Bell&Kampman,2021).
errorsandtheefficacyofmodelinfosheets,we
undertakeareproducibilitystudyinafieldwhere
Wedefinearesearchfindingasreproducibleifthecodeand
| complex | ML  | models | are | believed | to vastly out- |           |           |             |     |               |     |          |
| ------- | --- | ------ | --- | -------- | -------------- | --------- | --------- | ----------- | --- | ------------- | --- | -------- |
|         |     |        |     |          |                | data used | to obtain | the finding |     | are available | and | the data |
performolderstatisticalmodelssuchasLogistic
iscorrectlyanalyzed(Hofmanetal.,2021a;Leek&Peng,
| Regression |     | (LR): | civil war | prediction. | We find |                         |     |     |                              |     |     |     |
| ---------- | --- | ----- | --------- | ----------- | ------- | ----------------------- | --- | --- | ---------------------------- | --- | --- | --- |
|            |     |       |           |             |         | 2015;Pineauetal.,2020). |     |     | Thisisabroaderdefinitionthan |     |     |     |
thatallpapersclaimingthesuperiorperformance
computationalreproducibility—whentheresultsinapaper
ofcomplexMLmodelscomparedtoLRmodels
canbereplicatedusingtheexactcodeanddatasetprovided
| fail to | reproduce | due | to data | leakage, | and com- |     |     |     |     |     |     |     |
| ------- | --------- | --- | ------- | -------- | -------- | --- | --- | --- | --- | --- | --- | --- |
bytheauthors(seeAppendixA).
plexMLmodelsdon’tperformsubstantivelybet-
terthandecades-oldLRmodels. Whilenoneof Leakage. Dataleakagehaslongbeenrecognizedasalead-
these errors could have been caught by reading ingcauseoferrorsinMLapplications(Nisbetetal.,2009).
the papers, model info sheets would enable the Informativeworkonleakage,Kaufmanetal.(2012)provide
detectionofleakageineachcase. anoverviewofdifferenttypesoferrorsandgiveseveralrec-
|     |     |     |     |     |     | ommendationsformitigatingtheseerrors. |     |        |           |                  | Sincethispaper |       |
| --- | --- | --- | --- | --- | --- | ------------------------------------- | --- | ------ | --------- | ---------------- | -------------- | ----- |
|     |     |     |     |     |     | was published,                        |     | the ML | community | has investigated |                | leak- |
ageinseveralengineeringapplicationsandmodelingcom-
1Department
|     | of  | Computer | Science | and | Center for Informa- |     |     |     |     |     |     |     |
| --- | --- | -------- | ------- | --- | ------------------- | --- | --- | --- | --- | --- | --- | --- |
petitions(Fraser,2016;Ghanietal.,2020;Becker,2018;
tionTechnologyPolicy,PrincetonUniversity.Correspondenceto:
|     |     |     |     |     |     | Brownlee,2016;Collins-Thompson). |     |     |     | However,leakageoc- |     |     |
| --- | --- | --- | --- | --- | --- | -------------------------------- | --- | --- | --- | ------------------ | --- | --- |
SayashKapoor<sayashk@princeton.edu>.
curringinML-basedsciencehasnotbeencomprehensively

LeakageandtheReproducibilityCrisisinML-basedScience KapoorandNarayanan
t
|                    |                          |     |     |       |         |         |         | e s     |         |       | t       |        |     |
| ------------------ | ------------------------ | --- | --- | ----- | ------- | ------- | ------- | ------- | ------- | ----- | ------- | ------ | --- |
|                    |                          |     |     |       |         | s       | s t     | -t      |         |       | e s     | s      |     |
|                    |                          |     |     |       |         | l l     | t e     | n       |         |       | - t     | u e    |     |
|                    |                          |     |     |       | d f     | a       | n -     | a i     | s       | e     | n       | s      |     |
|                    |                          |     |     | w     | e i t   |         | i       | r       | r e     | g a   | i       | i s    |     |
|                    |                          |     |     | e     | p       |         | r a n   | t       | u       | a r   | y       |        |     |
|                    |                          |     |     | i     | h       |         | t o     |         | a t a   | k w t | a s i t |        | ?   |
|                    |                          |     |     | e v   | w i t   | n       |         |         | e e     |       | i b i l | s      | e d |
|                    |                          |     |     | r     | t       | o       | e l.    | s       | f l     | b /   | b i     | s e    | us  |
|                    |                          |     |     | er s  | r s s e | c .     | s       | t e t e | a l     | . g   | u c     | e s u  |     |
|                    |                          |     |     | e     | t       | o       | e a     | a       | o r n   | d i n | d s u   | s      | et  |
|                    |                          |     | a   | p a p | e s     | p r u   | r i c   | m       | p i     | p l   | o i s   | e i as |     |
|                    |                          |     | p   | p     | t       | - t     | p l     | t i m   | n -     | m     | p r y   | c a t  |     |
|                    |                          |     | f   | f     | o r e   | e a     | u       | g i e   | o       | a r e | i t     | o i d  |     |
|                    |                          |     | o   | o     | N P     | F       | D       | e T     | N       | S .   | a l     | h d    |     |
|                    |                          |     | er  | er ]  | ]       | ]       | ] I l l | ]       | ] ]     | ut    | u c     | r      |     |
|                    |                          |     | b b | . 1   | . 2     | . 3 . 4 | ]       | . 1     | . 2 . 3 | p     | q ri c  | d a    |     |
|                    |                          |     | m m | 1     | 1       | 1 1     | 2       | 3       | 3 3     | m t   | a t     | n      |     |
|                    |                          | u   | u   | L     | L L     | L       | L       | L L     | L       | o a   | M e     | t a    |     |
| Field              | Paper                    | N   | N   | [     | [ [     | [       | [       | [ [     | [       | C D   | S       |        |     |
| Medicine           | Bouwmeesteretal.(2012)   | 71  | 27  | ◦     |         |         |         |         |         | ◦     |         |        |     |
| Neuroimaging       | Whelan&Garavan(2014)     | –   | 14  | ◦     | ◦       |         |         |         |         |       |         |        |     |
| AutismDiagnostics  | Boneetal.(2015)          | –   | 3   |       |         | ◦       |         |         | ◦       | ◦     | ◦ ◦     |        |     |
| Bioinformatics     | Blagus&Lusa(2015)        | –   | 6   | ◦     |         |         |         |         |         |       |         |        |     |
| NutritionResearch  | Ivanescuetal.(2016)      | –   | 4   | ◦     |         |         |         |         |         | ◦     | ◦       |        |     |
| SoftwareEng.       | Tuetal.(2018)            | 58  | 11  |       |         |         | ◦       |         |         | ◦ ◦   | ◦       |        |     |
| Toxicology         | Alvesetal.(2019)         | –   | 1   |       |         | ◦       |         |         |         | ◦ ◦   |         |        |     |
|                    |                          |     |     |       |         |         |         | ◦       |         | ◦     | ◦       |        |     |
| SatelliteImaging   | Nalepaetal.(2019)        | 17  | 17  |       |         |         |         |         |         |       |         |        |     |
| Tractography       | Poulinetal.(2019)        | 4   | 2   | ◦     |         |         |         |         |         | ◦ ◦   | ◦ ◦     |        |     |
| ClinicalEpidem.    | Christodoulouetal.(2019) | 71  | 48  |       | ◦       |         |         |         |         | ◦     |         |        |     |
| Brain-computerInt. | Nakanishietal.(2020)     | –   | 1   | ◦     |         |         |         |         |         |       | ◦       |        |     |
| Histopathology     | Oneretal.(2020)          | –   | 1   |       |         |         |         | ◦       |         |       |         |        |     |
| Neuropsychiatry    | Poldracketal.(2020)      | 100 | 53  | ◦ ◦   |         |         |         |         |         | ◦     | ◦       |        |     |
|                    |                          |     |     |       | ◦       |         |         | ◦       | ◦       | ◦ ◦   | ◦       |        |     |
| Medicine           | Vandewieleetal.(2021)    | 24  | 21  |       |         |         |         |         |         |       |         |        |     |
| Radiology          | Robertsetal.(2021)       | 62  | 62  | ◦     |         | ◦       |         |         | ◦       | ◦     | ◦       |        |     |
| ITOperations       | Lyuetal.(2021)           | 9   | 3   |       |         |         | ◦       |         |         |       | ◦       |        |     |
| Medicine           | Filhoetal.(2021)         | –   | 1   |       |         |         | ◦       |         |         |       |         |        |     |
| Neuropsychiatry    | Shimetal.(2021)          | –   | 1   |       | ◦       |         |         |         |         | ◦     |         |        |     |
| Genomics           | Barnettetal.(2022)       | 41  | 23  |       | ◦       |         |         |         |         | ◦     |         |        |     |
|                    |                          |     |     | ◦ ◦   | ◦       |         | ◦       | ◦       | ◦       | ◦     | ◦       |        |     |
| ComputerSecurity   | Arpetal.(2022)           | 30  | 30  |       |         |         |         |         |         |       |         |        |     |
Table1.Surveyof20papersthatidentifypitfallsintheadoptionofMLmethodsacross17fields,collectivelyaffecting329papers.In
eachfield,papersadoptingMLmethodssufferfromdataleakage.Thecolumnheadingsfortypesofdataleakage,showninbold,are
basedonourtaxonomyofdataleakage.Wealsohighlightotherissuesthatarereportedinthepapers,includingissueswithcomputational
reproducibility(theavailabilityofcode,data,andcomputingenvironmenttoreproducetheexactresultsreportedinthepaper),data
quality(forexample,smallsizeorlargeamountsofmissingdata),metricchoice(usingincorrectmetricsforthetaskathand,forexample,
usingaccuracyformeasuringmodelperformanceinthepresenceofheavyclassimbalance),andstandarddatasetuse,whereissuesare
founddespitetheuseofstandarddatasetsinafield.
investigated. As a result, mitigations for data leakage in problems(Section2.4).
scientificapplicationsofMLremainunderstudied.
|     |     |     |     | 2)Modelinfosheetstodetectandpreventleakage. |     |     |     |     |     |     |     | Cur- |     |
| --- | --- | --- | --- | ------------------------------------------- | --- | --- | --- | --- | --- | --- | --- | ---- | --- |
Inthispaper,wesystematicallyinvestigatereproducibility rentstandardsforreportingmodelperformanceinML-based
issuesinML-basedscienceduetodataleakage. Wemake scienceoftenfallshortinaddressingissuesduetoleakage.
threemaincontributions: Specifically,checklistsandmodelcardsareonewaytopro-
videstandardbestpracticesforreportingdetailsaboutML
1)Asurveyandtaxonomyofreproducibilityissuesdue
models(Monganetal.,2020;Collinsetal.,2015;Mitchell
toleakage.Weprovideevidenceforagrowingreproducibil-
|                             |                         |     |     | etal.,2019).         |     | However,currenteffortsdonotaddressissues |          |     |                         |     |     |     |     |
| --------------------------- | ----------------------- | --- | --- | -------------------- | --- | ---------------------------------------- | -------- | --- | ----------------------- | --- | --- | --- | --- |
| itycrisisinML-basedscience. | Throughasurveyoflitera- |     |     |                      |     |                                          |          |     |                         |     |     |     |     |
|                             |                         |     |     | arisingduetoleakage. |     |                                          | Further, |     | mostchecklistscurrently |     |     |     |     |
tureinresearchcommunitiesthatadoptedMLmethods,we
inusearenotdevelopedforML-basedscienceingeneral,
find20papersacross17fieldswhereerrorshavebeenfound,
|                                         |                            |     |     | but rather | for     | specific | scientific |     | or research    |     | communities  |     |     |
| --------------------------------------- | -------------------------- | --- | --- | ---------- | ------- | -------- | ---------- | --- | -------------- | --- | ------------ | --- | --- |
| collectivelyaffecting329papers(Table1). | Eachofthese                |     |     |            |         |          |            |     |                |     |              |     |     |
|                                         |                            |     |     | (Pineau    | et al., | 2020;    | Mongan     |     | et al., 2020). |     | As a result, |     |     |
| fieldssuffersfromleakage.               | Wehighlightthatdataleakage |     |     |            |         |          |            |     |                |     |              |     |     |
bestpracticesformodelreportinginML-basedscienceare
mitigationstrategiesdevelopedforotherMLapplications
underspecified.
suchasmodelingcontestsandengineeringapplicationsof-
ten do not translate to ML-based science. Based on our Inthispaper,weintroducemodelinfosheetstodetectand
survey, wepresentafine-grainedtaxonomyof8typesof preventleakageinML-basedscience(Section3). Theyare
leakage that range from textbook errors to open research inspiredbythemodelcardsinMitchelletal.(2019). Filling

LeakageandtheReproducibilityCrisisinML-basedScience KapoorandNarayanan
|     | 1.0 |     |     | Logistic Regression 1 |     | Logistic Regression |     |     |     |     |     |
| --- | --- | --- | --- | --------------------- | --- | ------------------- | --- | --- | --- | --- | --- |
|     |     |     |     | Logistic Regression 2 |     | Random Forests 1    |     |     |     |     |     |
|     |     |     |     | Logistic Regression 3 |     | Random Forests 2    |     |     |     |     |     |
Random Forests
0.9
0.8
0.7
|     |     |     |     |     |     |     |     |     | AdaBoost              |     | AdaBoost            |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --------------------- | --- | ------------------- |
|     |     |     |     |     |     |     |     |     | GBT                   |     | Extratrees          |
|     | 0.6 |     |     |     |     |     |     |     | Logistic Regression 1 |     | Lasso               |
|     |     |     |     |     |     |     |     |     | Logistic Regression 2 |     | Logistic Regression |
|     |     |     |     |     |     |     |     |     | Logistic Regression 3 |     | Random Forest       |
|     |     |     |     |     |     |     |     |     | Random Forests        |     | SVM                 |
0.5
Reported results Corrected results Reported results Corrected results Reported results Corrected results Reported results Corrected results
|     |     | (AUC) |     | (AUC) | (AUC) | (AUC) |     | (AUC) | (AUC) | (Accuracy) | (Accuracy) |
| --- | --- | ----- | --- | ----- | ----- | ----- | --- | ----- | ----- | ---------- | ---------- |
Paper  Muchlinski et al.  Colaresi and Mahmood  Wang  Kaufman et al.
Claim  Random Forests model  Random Forests models drastically  Adaboost and Gradient Boosted  Adaboost outperforms other models
|     |     | drastically outperforms Logistic  |     | outperform Logistic regression  |     |     | Trees (GBT) drastically outperform  |     |     |     |     |
| --- | --- | --------------------------------- | --- | ------------------------------- | --- | --- | ----------------------------------- | --- | --- | --- | --- |
|     |     | regression models                 |     | model                           |     |     | other models                        |     |     |     |     |
Error  [L1.2] Pre-proc. on train-test    [L1.2] Pre-proc. on train-test  [L1.2] Pre-proc. on train-test.  [L2] Illegitimate features (Data
(Incorrect imputation)  (Incorrect reuse of an imputed  (Incorrect reuse of an imputed dataset)  leakage due to proxy variables)
|     |     |     |     | dataset)  |     |     | [L3.1] Temporal leakage (k-fold cross  |     |     | [L3.1] Temporal leakage (k-fold       |     |
| --- | --- | --- | --- | --------- | --- | --- | -------------------------------------- | --- | --- | ------------------------------------- | --- |
|     |     |     |     |           |     |     | validation with temporal data)         |     |     | cross validation with temporal data)  |     |
Impact  Random Forests perform no  Random Forests perform no better  Difference in AUC between Adaboost  Adaboost no longer outperforms

better than Logistic Regression  than Logistic Regression  and Logistic Regression drops from  Logistic Regression.
|     |     |     |     |     |     |     | 0.14 to 0.01  |     |     | None of the models outperform a  |     |
| --- | --- | --- | --- | --- | --- | --- | ------------- | --- | --- | -------------------------------- | --- |
baseline model that predicts the
outcome of the previous year
Discussion  Impact of the incorrect  Re-use the dataset provided by  Re-use the dataset provided by  Use several proxy variables for
imputation is severe since 95%  Muchlinski et al., which uses an  Muchlinski et al., which uses an  the outcome as predictors (e.g.,
of the out-of-sample dataset is  incorrect imputation method   incorrect imputation method   colwars, cowwars, sdwars, all
missing and is filled in using the    proxies for civil war), leading to
|     |     | incorrect imputation method  |     |     |     |     |     |     |     | near perfect accuracy  |     |
| --- | --- | ---------------------------- | --- | --- | --- | --- | --- | --- | --- | ---------------------- | --- |

F  igure1.Acomparisonofreportedandcorrectedresultsincivilwarpredictionpaperspublishedintoppoliticalsciencejournals.The
mainfindingsofeachofthesepapersareinvalidduetovariousformsofdataleakage:Muchlinskietal.(2016)imputethetrainingand
testdatatogether,Colaresi&Mahmood(2017)andWang(2019)incorrectlyreuseanimputeddataset,andKaufmanetal.(2019)use
proxiesforthetargetvariablewhichcausesdataleakage.Theuseofmodelinfosheets(Section3)woulddetectleakageineverypaper.
Whenwecorrecttheseerrors,complexMLmodels(suchasAdaboostandRandomForests)donotperformsubstantivelybetterthan
decades-oldLogisticRegressionmodelsforcivilwarpredictionineachcase.Eachcolumninthetableoutlinestheimpactofleakageon
theresultsofapaper.Thefigureaboveeachcolumnshowsthedifferenceinperformancethatresultsfromfixingleakageissues.
out a model info sheet requires the researcher to provide toppoliticalsciencejournals. Further,whentheerrorsare
preciseargumentstojustifythatmodelsusedtowardsmak- corrected, ML models don’t perform substantively better
ingscientificclaimsdonotsufferfromleakage. Modelinfo thandecades-oldLogisticRegressionmodels,callinginto
sheetsaddressalltypesofleakageidentifiedinoursurvey. questiontheshiftfromexplanatorymodelingtopredictive
Weadvocateformodelinfosheetstobeincludedwithevery modeling in this field. While none of these errors could
papermakingascientificclaimusinganMLmodel. havebeencaughtbyreadingthepapers,modelinfosheets
enablethedetectionofleakageineachcase.
| 3)  | Empirical | case study | of  | leakage | in civil war | predic- |     |     |     |     |     |
| --- | --------- | ---------- | --- | ------- | ------------ | ------- | --- | --- | --- | --- | --- |
tion. Foranin-depthlookattheimpactofreproducibility
2.Evidenceofareproducibilitycrisis
errorsandtheefficacyofmodelinfosheets,weundertakea
reproducibilitystudyincivilwarprediction,asubfieldof
ManyscientificfieldshaveadoptedMLmethodsandthe
politicalsciencewhereMLmodelsarebelievedtovastly
paradigmofpredictivemodeling(Athey&Imbens,2019;
outperformolderstatisticalmodelssuchasLogisticRegres-
Schrider&Kern,2018;Vallettaetal.,2017;Iniestaetal.,
| sion. | We  | perform a | systematic | review | to find papers | on  |     |     |     |     |     |
| ----- | --- | --------- | ---------- | ------ | -------------- | --- | --- | --- | --- | --- | --- |
2016;Tonidandeletal.,2018;Yarkoni&Westfall,2017).
civilwarpredictionandfindthatallpapersinourreview
|     |     |     |     |     |     |     | We  | find at least | three main | uses of ML | models in scien- |
| --- | --- | --- | --- | --- | --- | --- | --- | ------------- | ---------- | ---------- | ---------------- |
claimingthesuperiorperformanceofMLmodelscompared
|     |     |     |     |     |     |     | tificliterature. |     | First,modelswhicharebetteratprediction |     |     |
| --- | --- | --- | --- | --- | --- | --- | ---------------- | --- | -------------------------------------- | --- | --- |
toLogisticRegressionmodelsfailtoreproduceduetodata
arethoughttoenableanimprovedunderstandingofscien-
| leakage(Figure1)1. |     | Eachofthesepaperswaspublishedin |     |     |     |     |                                    |     |     |                   |     |
| ------------------ | --- | ------------------------------- | --- | --- | --- | --- | ---------------------------------- | --- | --- | ----------------- | --- |
|                    |     |                                 |     |     |     |     | tificphenomena(Hofmanetal.,2021b). |     |     | Second,especially |     |
1Anoteonterminology.Weuse“MLmodels”asashorthand whenusedinmedicalfields,modelswithhigherpredictive
formodelsotherthanLogisticRegression,specifically,Random
terminologyweuseiscommoninfieldsthatdistinguishMLfrom
| Forests,Gradient-BoostedTrees,andAdaboost. |     |     |     |     | Tobeclear,all |     |     |     |     |     |     |
| ------------------------------------------ | --- | --- | --- | --- | ------------- | --- | --- | --- | --- | --- | --- |
statisticalmethodsthatinvokeanassumptionaboutthetruedata
ofthesemodelsincludingLogisticRegressioninvolvelearning
generatingprocess,suchasLogisticRegression(Christodoulou
| from | data | in the predictive | modeling | approach. | However, | the |     |     |     |     |     |
| ---- | ---- | ----------------- | -------- | --------- | -------- | --- | --- | --- | --- | --- | --- |
etal.,2019).

LeakageandtheReproducibilityCrisisinML-basedScience KapoorandNarayanan
accuracycanaidinresearchanddevelopmentofbetterdi- ingsettingsorpredictivemodelingcompetitions(Kaufman
agnostictools(McDermottetal.,2021). Finally,ML-based etal.,2012). However,thetaxonomyofdataleakageout-
methodshavealsobeenusedtoinvestigatetheinherentpre- lined in this body of work does not address all kinds of
dictabilityofphenomena, especiallyforpredictingsocial leakage that we identify in our survey. In particular, we
outcomes(Salganiketal.,2020). Theincreasedadoption findthatleakagecanresultfromadifferencebetweenthe
of ML methods in science motivates our investigation of distributionofthetestsetandthedistributionofscientific
reproducibilityissuesinML-basedscience. interest(Section2.4). Robustnesstodistributionshiftisan
|     |     |     |     |     |     | area of | ongoing research | in  | ML methods, |     | and is as | such |
| --- | --- | --- | --- | --- | --- | ------- | ---------------- | --- | ----------- | --- | --------- | ---- |
2.1.Dataleakagecausesirreproducibleresults anopenproblem(Geirhosetal.,2020). Additionally,prior
workprimarilyfocusesonmitigatingleakageinmodeling
Dataleakageisaspuriousrelationshipbetweentheindepen-
|     |     |     |     |     |     | competitionsandengineeringapplications. |     |     |     |     | Bothofthese |     |
| --- | --- | --- | --- | --- | --- | --------------------------------------- | --- | --- | --- | --- | ----------- | --- |
dentvariablesandthetargetvariablethatarisesasanartifact
settingsareverydifferentfromscientificresearch,andmiti-
ofthedatacollection,sampling,orpre-processingstrategy.
gationsfordataleakageinmodelingcompetitionsaswellas
Sincethespuriousrelationshipwon’tbepresentinthedis-
engineeringapplicationsofMLoftendonottranslateinto
tributionaboutwhichscientificclaimsaremade, leakage strategiesformitigatingdataleakageinML-basedscience.
usuallyleadstoinflatedestimatesofmodelperformance.
|     |     |     |     |     |     | Leakageinmodelingcompetitions. |     |     |     | Inpredictivemodel- |     |     |
| --- | --- | --- | --- | --- | --- | ------------------------------ | --- | --- | --- | ------------------ | --- | --- |
Researchersinmanycommunitieshavealreadydocumented
ingcompetitions,datasetcreationandmodelevaluationis
| reproducibility | failures   | in ML-based          | science | within   | their |                          |       |                            |          |     |           |     |
| --------------- | ---------- | -------------------- | ------- | -------- | ----- | ------------------------ | ----- | -------------------------- | -------- | --- | --------- | --- |
|                 |            |                      |         |          |       | left to impartial        | third | parties                    | who have | the | expertise | and |
| fields. Here    | we conduct | a cross-disciplinary |         | analysis | by    |                          |       |                            |          |     |           |     |
|                 |            |                      |         |          |       | incentivestoavoiderrors. |       | Withinthisframework,noneof |          |     |           |     |
building on these individual reviews. This enables us to theparticipantshaveaccesstotheheld-outevaluationset
highlightthescaleandscopeofthecrisis,identifycommon
|     |     |     |     |     |     | beforethecompetitionends. |     | Incontrast,inmostML-based |     |     |     |     |
| --- | --- | --- | --- | --- | --- | ------------------------- | --- | ------------------------- | --- | --- | --- | --- |
patterns,andmakeprogresstowardasolution.
sciencetheresearcherhasaccesstotheentiredatasetwhile
When searching for past literature that documents repro- creatingtheMLmodels. Leakageoftenoccursduetothe
ducibilityfailuresinML-basedscience,wefoundthatdif- researcher having access to the entire dataset during the
modelingprocess.
ferentfieldsoftenusedifferenttermstodescribepitfallsand
errors. Thismakesitdifficulttoconductasystematicsearch
|     |     |     |     |     |     | Leakage | in engineering | applications. |     | One | of the | most |
| --- | --- | --- | --- | --- | --- | ------- | -------------- | ------------- | --- | --- | ------ | ---- |
to find papers with errors. Therefore, we do not present common recommendations for detecting and mitigating
ourresultsasasystematicmeta-reviewofleakagefroma
|     |     |     |     |     |     | leakage | is to deploy | the ML | model | at a limited | scale | in  |
| --- | --- | --- | --- | --- | --- | ------- | ------------ | ------ | ----- | ------------ | ----- | --- |
coherentsampleofpapers,butratherasalowerboundof
|                                         |           |                |     |               |     | production.  | Thisadviceisonlyapplicabletoengineering |          |     |         |             |      |
| --------------------------------------- | --------- | -------------- | --- | ------------- | --- | ------------ | --------------------------------------- | -------- | --- | ------- | ----------- | ---- |
| reproducibilityissuesinML-basedscience. |           |                |     | Additionally, |     |              |                                         |          |     |         |             |      |
|                                         |           |                |     |               |     | applications | of ML, where                            | the      | end | goal is | not to gain | in-  |
| most reviews                            | only look | at the content | of  | the papers,   | and |              |                                         |          |     |         |             |      |
|                                         |           |                |     |               |     | sights about | a particular                            | process, | but | rather  | to serve    | as a |
not the code and data provided with the papers to check componentinaproduct.Often,aroughideaofmodelperfor-
| forerrors. | Thisleadstounder-countingthenumberofaf- |     |     |     |     |     |     |     |     |     |     |     |
| ---------- | --------------------------------------- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
manceisenoughtodecidewhetheramodelisgoodenough
fectedpapers,sincethecodemighthaveerrorsthatarenot
|     |     |     |     |     |     | tobedeployedinaproduct. |     | Contrarily,ML-basedscience |     |     |     |     |
| --- | --- | --- | --- | --- | --- | ----------------------- | --- | -------------------------- | --- | --- | --- | --- |
apparentfromreadingthepapers.
involvesmakingascientificclaimusingtheperformanceof
Ourfindingspresentaworryingtrendforthereproducibility theMLmodelasevidence. Inaddition,engineeringapplica-
tionsofMLoftenoperateinarapidlychangingcontextand
| ofML-basedscience. |     | Wefind20papersfrom17fieldsthat |     |     |     |     |     |     |     |     |     |     |
| ------------------ | --- | ------------------------------ | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
outlineerrorsinML-basedscienceintheirfield,collectively haveaccesstolargedatasets,sosmalldifferencesinperfor-
affecting329papers. Aprominentfindingthatemergesis mancesareoftennotasimportant,whereasscientificclaims
aresensitivetosmallperformancedifferencesbetweenML
| thatdataleakageisapitfallineverysinglecase.   |     |     |     | Theresults    |         |         |     |     |     |     |     |     |
| --------------------------------------------- | --- | --- | --- | ------------- | ------- | ------- | --- | --- | --- | --- | --- | --- |
| fromoursurveyarepresentedinTable1.            |     |     |     | Columnsinbold |         | models. |     |     |     |     |     |     |
| representdifferenttypesofleakage(Section2.4). |     |     |     |               | Thelast |         |     |     |     |     |     |     |
fourcolumnsrepresentothercommontrendsinthepapers 2.3.Whydowecallitareproducibilitycrisis?
| westudy(Section2.5).       |     | Forsystematicreviews,wereport |     |     |     |                                       |               |         |              |        |            |        |
| -------------------------- | --- | ----------------------------- | --- | --- | --- | ------------------------------------- | ------------- | ------- | ------------ | ------ | ---------- | ------ |
|                            |     |                               |     |     |     | We say                                | that ML-based | science | is suffering |        | from a     | repro- |
| thenumberofpapersreviewed. |     | Eachpaperinoursurvey          |     |     |     |                                       |               |         |              |        |            |        |
|                            |     |                               |     |     |     | ducibilitycrisisfortworelatedreasons: |               |         |              | First, | ourresults |        |
highlightsissueswithleakage,with6papershighlighting
showthatreproducibilityfailuresinML-basedscienceare
thepresenceofmultipletypesofleakageintheirfield.
|     |     |     |     |     |     | systemic. | In nearly every | scientific |     | field that | has | carried |
| --- | --- | --- | --- | --- | --- | --------- | --------------- | ---------- | --- | ---------- | --- | ------- |
outasystematicstudyofreproducibilityissues,papersare
2.2.DataleakagemitigationsforotherML
|     |     |     |     |     |     | plaguedbycommonpitfalls. |     |     | Inmanysystematicreviews, |     |     |     |
| --- | --- | --- | --- | --- | --- | ------------------------ | --- | --- | ------------------------ | --- | --- | --- |
applicationsdonotapplytoscientificresearch
amajorityofthepapersreviewedsufferfromthesepitfalls.
|               |          |             |         |         |     | Thus, we | find that similar | problems |     | are likely | to arise | in  |
| ------------- | -------- | ----------- | ------- | ------- | --- | -------- | ----------------- | -------- | --- | ---------- | -------- | --- |
| Most previous | research | and writing | on data | leakage | has |          |                   |          |     |            |          |     |
focusedonmitigatingdataleakageprimarilyforengineer- manyfieldsthatareadoptingMLmethods. Second,despite

LeakageandtheReproducibilityCrisisinML-basedScience KapoorandNarayanan
theurgencyofaddressingreproducibilityfailures,thereare isusedforthepurposesoftrainingandevaluatinganML
no systemic solutions that have been deployed for these model,thesamedatacouldexistinthetrainingaswellas
| failures. | Scientificcommunitiesarediscoveringthesame |     |     |     | testset. |     |     |     |     |     |     |
| --------- | ------------------------------------------ | --- | --- | --- | -------- | --- | --- | --- | --- | --- | --- |
failuremodesacrossdisciplines,buthaveyettoconverge
|     |     |     |     |     | [L2]Modelusesfeaturesthatarenotlegitimate. |     |     |     |     |     | Ifthe |
| --- | --- | --- | --- | --- | ------------------------------------------ | --- | --- | --- | --- | --- | ----- |
onbestpracticesforavoidingreproducibilityfailures.
modelhasaccesstofeaturesthatshouldnotbelegitimately
Callingattentiontoandaddressingthesewidespreadfail- availableforuseinthemodelingexercise,thiscouldresultin
uresisvitaltomaintainingpublicconfidenceinML-based leakage. Oneinstancewhenthiscanhappenisifafeatureis
science. Atthesametime,theuseofMLmethodsisstill aproxyfortheoutcomevariable(Kaufmanetal.,2012).For
initsinfancyinmanyscientificfields. Addressingrepro- example,Filhoetal.(2021)findthatarecentstudyincluded
ducibilityfailurespre-emptivelyinsuchfieldscancorrecta theuseofanti-hypertensivedrugsasafeatureforpredicting
lotofscientificresearchthatwouldotherwisebeflawed. hypertension. Suchafeaturecouldleadtoleakagebecause
themodelwouldnothaveaccesstothisinformationwhen
2.4.Towardsasolution: Ataxonomyofdataleakage predictingthehealthoutcomeforanewpatient. Further,if
thefactthatapatientusesanti-hypertensivedrugsisalready
| We now           | provide our taxonomy             |     | of data leakage | errors in |          |            |       |                |     |              |     |
| ---------------- | -------------------------------- | --- | --------------- | --------- | -------- | ---------- | ----- | -------------- | --- | ------------ | --- |
|                  |                                  |     |                 |           | known at | prediction | time, | the prediction | of  | hypertension |     |
| ML-basedscience. | Suchataxonomycanenableabetterun- |     |                 |           |          |            |       |                |     |              |     |
becomesatrivialtask.
derstandingofwhyleakageoccursandinformpotentialso-
|     |     |     |     |     | The judgement |     | of whether | the use | of a given | feature | is  |
| --- | --- | --- | --- | --- | ------------- | --- | ---------- | ------- | ---------- | ------- | --- |
lutions. Ourtaxonomyiscomprehensiveandaddressesdata
leakagearisingduringthedatacollection,pre-processing, legitimateforamodelingtaskrequiresdomainknowledge
|                             |     |     |                          |     | andcanbehighlyproblemspecific. |     |     |     | Asaresult,wedonot |     |     |
| --------------------------- | --- | --- | ------------------------ | --- | ------------------------------ | --- | --- | --- | ----------------- | --- | --- |
| modelingandevaluationsteps. |     |     | Inparticular,ourtaxonomy |     |                                |     |     |     |                   |     |     |
addresses all cases of data leakage that we found in our providesub-categoriesforthissortofleakage. Instead,we
survey(Table1). suggestthatresearchersdecidewhichfeaturesaresuitable
foramodelingtaskandjustifytheirchoiceusingdomain
| [L1] Lack | of clean | separation | of training | and test |     |     |     |     |     |     |     |
| --------- | -------- | ---------- | ----------- | -------- | --- | --- | --- | --- | --- | --- | --- |
expertise.
| dataset. | If the training | dataset | is not separated | from the |           |        |           |          |              |     |         |
| -------- | --------------- | ------- | ---------------- | -------- | --------- | ------ | --------- | -------- | ------------ | --- | ------- |
|          |                 |         |                  |          | [L3] Test | set is | not drawn | from the | distribution |     | of sci- |
testdatasetduringallpre-processing,modelingandevalu-
ationsteps,themodelhasaccesstoinformationinthetest entificinterest. Thedistributionofdataonwhichtheper-
|            |                 |               |       |           | formance | of an | ML model | is evaluated | differs | from | the |
| ---------- | --------------- | ------------- | ----- | --------- | -------- | ----- | -------- | ------------ | ------- | ---- | --- |
| set before | its performance | is evaluated. | Since | the model |          |       |          |              |         |      |     |
hasaccesstoinformationfromthetestsetattrainingtime, distribution of data about which the scientific claims are
themodellearnsrelationshipsbetweenthepredictorsand made. Theperformanceofthemodelonthetestsetdoes
notcorrespondtoitsperformanceondatadrawnfromthe
theoutcomethatwouldnotbeavailableinadditionaldata
drawnfromthedistributionofinterest. Theperformanceof distributionofscientificinterest.
themodelonthisdatathereforedoesnotreflecthowwell [L3.1]Temporalleakage. WhenanMLmodelisusedto
themodelwouldperformonanewtestsetdrawnfromthe
|     |     |     |     |     | make predictions |     | about | a future outcome |     | of interest, | the |
| --- | --- | --- | --- | --- | ---------------- | --- | ----- | ---------------- | --- | ------------ | --- |
samedistributionofdata.
testsetshouldnotcontainanydatafromadatebeforethe
[L1.1]Notestset. Usingthesamedatasetfortrainingas training set. If the test set contains data from before the
wellastestingthemodelisatext-bookexampleofoverfit- trainingset,themodelisbuiltusingdata“fromthefuture”
|     |     |     |     |     | that it should | not | have access | to during | training, |     | and can |
| --- | --- | --- | --- | --- | -------------- | --- | ----------- | --------- | --------- | --- | ------- |
ting,whichleadstooveroptimisicperformanceestimates
| (Kuhn&Johnson,2013).                      |     |     |     |             | causeleakage.          |     |     |               |     |               |     |
| ----------------------------------------- | --- | --- | --- | ----------- | ---------------------- | --- | --- | ------------- | --- | ------------- | --- |
|                                           |     |     |     |             | [L3.2] Nonindependence |     |     | between train | and | test samples. |     |
| [L1.2]Pre-processingontrainingandtestset. |     |     |     | Usingtheen- |                        |     |     |               |     |               |     |
tiredatasetforanypre-processingstepssuchasimputation Nonindependencebetweentrainandtestsamplesconstitutes
orover/undersampling. Forinstance,usingoversampling leakage,unlessthescientificclaimisaboutadistribution
|     |     |     |     |     | thathasthesamedependencestructure. |     |     |     | Intheextreme(but |     |     |
| --- | --- | --- | --- | --- | ---------------------------------- | --- | --- | --- | ---------------- | --- | --- |
beforesplittingthedataintotrainingandtestsetsleadsto
animperfectseparationbetweenthetrainingandtestsets unfortunatelycommon)case,trainandtestsamplescome
|     |     |     |     |     | from the | same people | or  | units. For | example, | Oner | et al. |
| --- | --- | --- | --- | --- | -------- | ----------- | --- | ---------- | -------- | ---- | ------ |
sincedatageneratedusingoversamplingfromthetraining
setwillalsobepresentinthetestset. (2020)findthatarecentstudyonhistopathologyusesdiffer-
entobservationsofthesamepatientinthetrainingandtest
[L1.3]Featureselectionontrainingandtestset. Feature sets. Inthiscase,thescientificclaimisbeingmadeabout
selectionontheentiredatasetresultsinusinginformation
theabilitytopredictgenemutationsinnewpatients;how-
aboutwhichfeatureperformswellonthetestsettomake
ever,itisevaluatedondatafromoldpatients(i.e.,datafrom
adecisionaboutwhichfeaturesshouldbeincludedinthe
patientsinthetrainingset),leadingtoamismatchbetween
model.
|                             |     |     |                          |     | thetestsetdistributionandthescientificclaim. |        |         |                      |     | Thetrain- |          |
| --------------------------- | --- | --- | ------------------------ | --- | -------------------------------------------- | ------ | ------- | -------------------- | --- | --------- | -------- |
|                             |     |     |                          |     | test split                                   | should | account | for the dependencies |     | in        | the data |
| [L1.4]Duplicatesindatasets. |     |     | Ifadatasetwithduplicates |     |                                              |        |         |                      |     |           |          |

LeakageandtheReproducibilityCrisisinML-basedScience KapoorandNarayanan
toensurecorrectperformanceevaluation. Methodssuchas 2.5.Otherissuesidentifiedinoursurvey(Table1)
‘blockcrossvalidation’canpartitionthedatasetstrategically
|     |     |     |     | Computationalreproducibilityissues. |     |     | Computationalre- |     |
| --- | --- | --- | --- | ----------------------------------- | --- | --- | ---------------- | --- |
sothattheperformanceevaluationdoesnotsufferfromdata
|     |     |     |     | producibility | of a finding | refers | to sharing | the complete |
| --- | --- | --- | --- | ------------- | ------------ | ------ | ---------- | ------------ |
leakageandoveroptimism(Robertsetal.,2017;Valavietal.,
|     |     |     |     | code and | data needed | to reproduce | the findings | reported |
| --- | --- | --- | --- | -------- | ----------- | ------------ | ------------ | -------- |
2021). Handlingnonindependencebetweenthetrainingand
|     |     |     |     | inapaperexactly. | Thisisimportanttoenableexternalre- |     |     |     |
| --- | --- | --- | --- | ---------------- | ---------------------------------- | --- | --- | --- |
testsetsingeneral—i.e.,withoutanyassumptionsaboutin-
searcherstoreproduceresultsandverifytheircorrectness.
dependenceinthedata—isahardproblem,sincewemight
Fivepapersinoursurveyoutlinedthelackofcomputational
notknowtheunderlyingdependencystructureofthetaskin
reproducibilityintheirfield.
manycases(Malik,2020).
Dataqualityissues.Accesstogoodqualitydataisessential
| [L3.3] Sampling | bias in test distribution. | Sampling | bias |     |     |     |     |     |
| --------------- | -------------------------- | -------- | ---- | --- | --- | --- | --- | --- |
forcreatingMLmodels(Paulladaetal.,2020;Scheuerman
| inthechoiceoftestdatasetcanleadtodataleakage. |                          |             | One       |                                    |             |             |                   |                   |
| --------------------------------------------- | ------------------------ | ----------- | --------- | ---------------------------------- | ----------- | ----------- | ----------------- | ----------------- |
|                                               |                          |             |           | et al., 2021).                     | Issues with | the quality | of                | the dataset could |
| example of                                    | sampling bias is spatial | bias, which | refers to |                                    |             |             |                   |                   |
|                                               |                          |             |           | affecttheresultsofML-basedscience. |             |             | 10papersinoursur- |                   |
choosingthetestdatafromageographiclocationbutmak-
veyhighlighteddataqualityissuessuchasnotaddressing
| ing claims | about model performance | in other | geographic |     |     |     |     |     |
| ---------- | ----------------------- | -------- | ---------- | --- | --- | --- | --- | --- |
missingvaluesinthedata,thesmallsizeofdatasetscom-
| locationsaswell. | Anotherexampleisselectionbias,which |     |     |     |     |     |     |     |
| ---------------- | ----------------------------------- | --- | --- | --- | --- | --- | --- | --- |
paredtothenumberofpredictors,andtheoutcomevariable
entailschoosinganon-representativesubsetofthedataset
beingapoorproxyforthephenomenonbeingstudied.
| forevaluation. | Forexample,Boneetal.(2015)highlight |     |     |     |     |     |     |     |
| -------------- | ----------------------------------- | --- | --- | --- | --- | --- | --- | --- |
thatinastudyonpredictingautismusingMLmodels,ex- Metricchoiceissues. Amismatchbetweenthemetricused
cludingthedatacorrespondingtoborderlinecasesofautism toevaluateperformanceandthescientificproblemofinter-
leadstoleakagesincethetestsetisnolongerrepresentative
|     |     |     |     | estleadstoissueswithperformanceclaims. |     |     |     | Forexample, |
| --- | --- | --- | --- | -------------------------------------- | --- | --- | --- | ----------- |
ofthegeneralpopulationaboutwhichclaimsaremade. In usingaccuracyastheevaluationmetricwithaheavilyim-
addition,borderlinecasesofautismareoftenthemosttricky balanceddatasetleadstooveroptimisticresults,sincethe
todiagnose,soexcludingthemtheevaluationsetislikely modelcangetahighaccuracyscorebyalwayspredicting
toleadtooveroptimisticresults. Casesofleakagedueto themajorityclass. Fourpapersinoursurveyhighlighted
| samplingbiascanoftenbesubtle. |     | Forexample,Zechetal. |     |     |     |     |     |     |
| ----------------------------- | --- | -------------------- | --- | --- | --- | --- | --- | --- |
metricchoiceissues.
(2018)findthatmodelsforpneumoniapredictiontrainedon
|     |     |     |     | Use of standard | datasets. | Reproducibility |     | issues arose |
| --- | --- | --- | --- | --------------- | --------- | --------------- | --- | ------------ |
imagesfromonehospitaldonotgeneralizetoimagesfrom
despitetheuseofstandard,widely-useddatasets,oftenbe-
anotherhospitalduetosubtledifferencesinhowimagesare
causeofthelackofstandardmodelingandevaluationproce-
generatedineachhospital.
duressuchasfixingthetrain-testsplitandevaluationmetric
A model may have leakage when the distribution about forthedataset. Sevenpapersinoursurveyhighlightedthat
whichthescientificclaimismadedoesnotmatchthedistri- issuesarosedespitetheuseofstandarddatasets.
| butionfromwhichtheevaluationsetisdrawn. |     |     | MLmodels |     |     |     |     |     |
| --------------------------------------- | --- | --- | -------- | --- | --- | --- | --- | --- |
mayalsosufferfromarelated,butdistinctlimitation: the 3.Modelinfosheetsfordetectingand
lackofgeneralizationwhenwetrytoapplyaresultabout
preventingleakage
| one population | to another similar | but distinct | population. |     |     |     |     |     |
| -------------- | ------------------ | ------------ | ----------- | --- | --- | --- | --- | --- |
Several issues with the generalization of ML models op- Our taxonomy of data leakage highlights several failure
eratingunderadistributionshifthavebeenhighlightedin
|     |     |     |     | modeswhichareprevalentinML-basedscience. |     |     |     | Todetect |
| --- | --- | --- | --- | ---------------------------------------- | --- | --- | --- | -------- |
MLmethodsresearch,suchasfragilitytowardsadversarial casesof leakage, we provideatemplate foramodelinfo
examples(Szegedyetal.,2014),imagedistortionandtex-
sheettoaccompanyscientificclaimsusingpredictivemod-
| ture(Geirhosetal.,2018), | andoverinterpretation(Carter |     |     |     |     |     |     |     |
| ------------------------ | ---------------------------- | --- | --- | --- | --- | --- | --- | --- |
eling2. Thetemplateconsistsofpreciseargumentsneeded
etal.,2021). Robustnesstodistributionshiftisanongoing tojustifytheabsenceofleakage. Modelinfosheetswould
| areaofworkinMLmethodsresearch. |     | Evenslightshifts |     |     |     |     |     |     |
| ------------------------------ | --- | ---------------- | --- | --- | --- | --- | --- | --- |
addresseverytypeofleakageidentifiedinoursurvey.
inthetargetdistributioncancauseperformanceestimates
| tochangedrastically(Rechtetal.,2019). |     | Despiteongoing |     |     |     |     |     |     |
| ------------------------------------- | --- | -------------- | --- | --- | --- | --- | --- | --- |
3.1.Priorworkonmodelcardsandreporting
worktocreateMLmethodsthatarerobusttodistribution
standards
shift,bestpracticestodealwithdistributionshiftcurrently
includetestingtheMLmodelsonthedatafromthedistribu- Ourproposalisinspiredbypriorworkonmodelcardsand
checklists,whichwenowreview.
| tionwewanttomakeclaimsabout(Geirhosetal.,2020). |     |     | In  |     |     |     |     |     |
| ----------------------------------------------- | --- | --- | --- | --- | --- | --- | --- | --- |
ML-basedscience,wheretheaimistocreategeneralizable
Mitchelletal.(2019)introducedmodelcardsforreporting
knowledge,weshouldtakeresultsthatclaimtogeneralizeto
detailsaboutMLmodels,withafocusonpreciselyreporting
adifferentpopulationfromtheonemodelswereevaluated
onwithcaution. 2Themodelinfosheettemplateisavailableonourwebsite:
https://reproducible.cs.princeton.edu

LeakageandtheReproducibilityCrisisinML-basedScience KapoorandNarayanan
theintendedusecasesofMLmodels. Theyalsoaddressed aboutthecorrectnessofthefeaturesused,sincetheincorrect
fairness and transparency concerns: they require that the useofasinglefeatureinthemodelcancauseleakage. That
performance of ML models on different groups of users said,thesameargumentforwhyafeatureislegitimatecan
(e.g., on the basis of race, gender, age) is reported and oftenapplytoawholesetoffeatures. Forexample,fora
documentedtransparently. Thesemodelcardscomplement studyusingindividuals’locationhistoryasafeaturevector,
thedatasheetsintroducedbyGebruetal.(2021)todocument theuseoftheentirevectorcanbejustifiedtogether. Note
detailsaboutdatasetsinastandardformat. thatwedonotaskfortheresearchertolisteachfeatureused
intheirmodel. Rather,weaskthatthejustificationprovided
Theuseofchecklistshasalsobeenimpactfulinimproving
forthelegitimacyofthefeaturesusedintheirmodelshould
reportingpracticesinthefewfieldsthathaveadoptedthem
covereveryfeatureusedintheirmodel.
(Hanetal.,2017). Whilechecklistsandmodelcardspro-
videconcretebestpracticesforreportingstandards(Mongan [L3]Testsetisdrawnfromthedistributionofscientific
etal.,2020;Collinsetal.,2015;Mitchelletal.,2019;Garbin interest.Ifthedistributionaboutwhichthescientificclaims
& Marques, 2022), current efforts do not address pitfalls aremadeisdifferentfromtheoneonwhichthemodelis
arising due to leakage. Further, even though several sci- tested, then any claims about the performance of an ML
entificfields—especiallythoserelatedtomedicine—have modelontheevaluationstepfallshort.Theresearcherneeds
adopted checklists to improve reporting standards, most tojustifythatthetestsetisdrawnfromthedistributionof
checklistsaredevelopedforspecificscientificorresearch scientificinterestandthereisnoselectionorsamplingbias
communitiesinsteadofML-basedscienceingeneral. inthedatacollectionprocess. Thisstepcanhelpclarifythe
distributionaboutwhichscientificclaimsarebeingmade
3.2.Scientificargumentstosurfaceandprevent anddetecttemporalleakage.
leakage
3.3.Modelinfosheetsandourtheoryofchange
WhenMLmodelsareusedtomakescientificclaims,itis
notenoughtosimplyseparatethetrainingandtestsetsand Modelinfosheetscaninfluenceresearchpracticesintwo
reportperformancemetricsonthetestset. Unlikeresearch ways: first, researchers who introduce a scientific model
inMLmethods,whereamodel’sperformanceonahypo- alongsideapapercanusemodelinfosheetstodetectand
theticaltask(i.e.,onethatisnotlinkedtoaspecificscientific prevent leakage in their models. These info sheets can
claim)isstillofinteresttotheresearcherinsomecases(Raji be included as supplementary materials with their paper
etal.,2021),inML-basedscience,claimsaboutamodel’s for transparently reporting details about their models. In
performanceneedtobeconnectedtoscientificclaimsusing scientific fields where the use of ML methods is not yet
explicitarguments. Theburdenofproofforensuringthe widespread,usingtransparentreportingpracticesatanearly
correctnessoftheseargumentsisontheresearchermaking stage could enable easier adoption and more trust in ML
thescientificclaims(Lundbergetal.,2021). methods. Thiswouldalsohelpassuagereviewerconcerns
aboutreproducibility.
Inourmodels,weaskresearcherstopresentthreearguments
thatareessentialfordeterminingthatscientificresultswhich Second,journalsubmissionguidelinescouldencourageor
useMLmethodsdonotsufferfromdataleakage. Notethat requireauthorstofilloutmodelinfosheetsifapaperdoes
most ML-based science papers do not present any of the nottransparentlyreporthowthemodelwascreated. Inthis
threearguments,althoughtheysometimespartiallyaddress case,modelinfosheetscanbeusedtostartaconversation
the first argument (clean train-test separation) by report- betweenauthorsandreviewersaboutthedetailsofthemod-
ingout-of-samplepredictionperformance. Thearguments els introduced in a paper. Current peer-review practices
below are based on our taxonomy of data leakage issues oftendonotrequiretheauthorstodiscloseanycodeordata
presentedinSection2.4,andinformthemainsectionsof duringthereviewprocess(Liu&Salganik,2019). Evenif
themodelinfosheet. thecodeanddataareavailabletoreviewers,reproducingre-
sultsandspottingerrorsincodeisatimeconsumingprocess
[L1]Cleantrain-testseparation. Theresearcherneedsto
thatoftencannotbecarriedoutundercurrentpeer-review
arguewhythetestsetdoesnotinteractwithtrainingdata
practices. Model infosheets offera middleground: they
during any of the preprocessing, modeling or evaluation
couldenableacloserscrutinyofmethodswithoutmaking
stepstoensureacleantrain-testseparation.
theprocessonerousforreviewers.
[L2] Each feature in the model is legitimate. The re-
searcherneedstoarguewhyeachfeatureusedintheirmodel 3.4.Limitationsofmodelinfosheets
islegitimate,i.e.,aclaimmadeusingeachfeatureisofscien-
Whilemodelinfosheetscanenablethedetectionofalltypes
tificinterest. Notethatsomemodelsmightusehundredsof
ofleakageweidentifyinoursurvey,theysufferfromlimi-
features. Insuchcases,itisevenmoreimportanttoreason
tationsowingtothelackofcomputationalreproducibility

LeakageandtheReproducibilityCrisisinML-basedScience KapoorandNarayanan
of results in scientific research, incorrect claims made in switchedtopredictivemodelingusingcomplexMLmod-
modelinfosheets,andthelackofexpertiseofauthorsand els such as Random Forests and Adaboost instead of LR
reviewers. (see Figure 2), with several papers claiming near-perfect
performanceofthesemodelsforcivilwarprediction(Much-
First,theclaimsmadeinmodelinfosheetscannotbeveri-
linskietal.,2016;Colaresi&Mahmood,2017;Wang,2019;
| fiedintheabsenceofcomputationalreproducibility. |     |     |     |     |     | Thatis, |                     |     |     |                                |     |     |     |     |
| ----------------------------------------------- | --- | --- | --- | --- | --- | ------- | ------------------- | --- | --- | ------------------------------ | --- | --- | --- | --- |
|                                                 |     |     |     |     |     |         | Kaufmanetal.,2019). |     |     | Whiletheliteraturewereviewedin |     |     |     |     |
unlessthecode,dataandcomputingenvironmentrequired
oursurveyhighlightedthepitfallsinadoptingMLmethods
toreproducetheresultsinapaperaremadeavailable,there
(Table1),wegofurtherthanmostpreviousresearchtoin-
| is no way | to ascertain | if  | model info | sheets | are filled | out |     |     |     |     |     |     |     |     |
| --------- | ------------ | --- | ---------- | ------ | ---------- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
vestigatewhethertheclaimsmadeinthereviewedstudies
| correctly. | Ensuring | the | computational | reproducibility |     | of  |     |     |     |     |     |     |     |     |
| ---------- | -------- | --- | ------------- | --------------- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
surviveoncetheerrorsarecorrected.
resultsthereforeremainsanimportantgoalforimproving
scientificresearchstandards. Systematic search of predictive modeling literature in
|     |     |     |     |     |     |     | civilwarresearch. |     | Weconductedasystematicsearchto |     |     |     |     |     |
| --- | --- | --- | --- | --- | --- | --- | ----------------- | --- | ------------------------------ | --- | --- | --- | --- | --- |
Second,incorrectclaimsmadeinmodelinfosheetsmight
|     |     |     |     |     |     |     | find relevant | literature |     | (detailed | in  | Appendix | B.1). | This |
| --- | --- | --- | --- | --- | --- | --- | ------------- | ---------- | --- | --------- | --- | -------- | ----- | ---- |
providefalseassurancestoreviewersaboutthecorrectness
|                          |     |     |                        |     |     |     | yielded124papers. |     | Wenarrowedthislisttothe12papers |     |     |     |     |     |
| ------------------------ | --- | --- | ---------------------- | --- | --- | --- | ----------------- | --- | ------------------------------- | --- | --- | --- | --- | --- |
| oftheclaimsmadeinapaper. |     |     | However,byrequiringau- |     |     |     |                   |     |                                 |     |     |     |     |     |
thatfocusedonpredictingcivilwar,evaluatedperformance
thorstopreciselystatedetailsabouttheirmodelingprocess,
|     |     |     |     |     |     |     | usingatrain-testsplit, |     |     | andsharedthecompletecodeand |     |     |     |     |
| --- | --- | --- | --- | --- | --- | --- | ---------------------- | --- | --- | --------------------------- | --- | --- | --- | --- |
modelinfosheetsenableincorrectclaimstobechallenged
|               |      |           |            |         |       |     | data. For | these | 12, | we attempted |     | to identify | errors | and |
| ------------- | ---- | --------- | ---------- | ------- | ----- | --- | --------- | ----- | --- | ------------ | --- | ----------- | ------ | --- |
| more directly | than | in status | quo, where | details | about | the |           |       |     |              |     |             |        |     |
reproducibilityissuesfromthetextandthroughreviewing
modelingprocessareoftenleftundisclosed.
|     |     |     |     |     |     |     | the code | provided | with | the | papers. | When | we identified |     |
| --- | --- | --- | --- | --- | --- | --- | -------- | -------- | ---- | --- | ------- | ---- | ------------- | --- |
Fillingoutandevaluatingmodelinfosheetsrequiressome errors,were-analyzedthedatawiththeerrorscorrected.
expertiseinML.Infieldswherebothauthorsandreviewers
|     |     |     |     |     |     |     | Finding | 1: Data | leakage | causes |     | irreproducible |     | results. |
| --- | --- | --- | --- | --- | --- | --- | ------- | ------- | ------- | ------ | --- | -------------- | --- | -------- |
lackanyMLexpertise,subtlecasesofleakagemightslip
|           |       |         |            |       |              |     | We present | our | results | in Figure | 1.  | We found | errors | in 4 |
| --------- | ----- | ------- | ---------- | ----- | ------------ | --- | ---------- | --- | ------- | --------- | --- | -------- | ------ | ---- |
| under the | radar | despite | the use of | model | info sheets. | In  |            |     |         |           |     |          |        |      |
ofthe12papers—exactlythe4papersthatclaimedsupe-
suchcases,wehopethatmodelinfosheetsreleasedpublicly
riorperformanceofcomplexMLmodelsoverbaselineLR
| along with | papers | will enable | discourse | within | scientific |     |                              |     |     |     |                         |     |     |     |
| ---------- | ------ | ----------- | --------- | ------ | ---------- | --- | ---------------------------- | --- | --- | --- | ----------------------- | --- | --- | --- |
|            |        |             |           |        |            |     | modelsforpredictingcivilwar. |     |     |     | Allpaperssufferfromdif- |     |     |     |
communitiesontheshortcomingsofscientificmodels.
|     |     |     |     |     |     |     | ferent forms | of  | leakage. | All | 4 papers | were | published | in  |
| --- | --- | --- | --- | --- | --- | --- | ------------ | --- | -------- | --- | -------- | ---- | --------- | --- |
Finally,weacknowledgethatourunderstandingofleakage top-10journalsinthefieldof“PoliticalScienceandInterna-
mayevolve,andmodelinfosheetsmayneedtoevolvewith tionalRelations”(sci,2020). Whentheerrorsarecorrected,
it. Tothatend,wehaveversionedmodelinfosheets,and complex ML models perform no better than baseline LR
plan to update them as we continue to better understand models in each case except Wang (2019), where the dif-
leakageinML-basedscience. ferencebetweentheAUCofthecomplexMLmodelsand
|     |     |     |     |     |     |     | LR models | drops | from | 0.14 | to 0.01. | Further, | while | none |
| --- | --- | --- | --- | --- | --- | --- | --------- | ----- | ---- | ---- | -------- | -------- | ----- | ---- |
4.Acasestudyofcivilwarprediction oftheseerrorscouldhavebeencaughtbyreadingthepa-
|     |     |     |     |     |     |     | per, model | info | sheets | enable | the detection |     | of leakage | in  |
| --- | --- | --- | --- | --- | --- | --- | ---------- | ---- | ------ | ------ | ------------- | --- | ---------- | --- |
Tounderstandtheimpactofdataleakageandtheefficacy eachcase(AppendixC).Beyondreproducibility,ourresults
ofmodelinfosheetsinaddressingit,weundertakearepro- showthatcomplexMLmodelsarenotsubstantivelybetter
ducibilitystudyinafieldwhereMLmodelsarebelievedto atcivilwarpredictionthandecadesoldLRmodels. This
vastlyoutperformolderstatisticalmodelssuchasLogistic isconsistentwithsimilarsoberingfindingsinothertasks
Regression(LR)forpredictivemodeling: civilwarpredic- involvingpredictingsocialoutcomessuchaschildren’slife
|             |        |      |              |        |            |     | outcomes      | (Salganik | et                                   | al., 2020) | and | recidivism |     | (Dressel |
| ----------- | ------ | ---- | ------------ | ------ | ---------- | --- | ------------- | --------- | ------------------------------------ | ---------- | --- | ---------- | --- | -------- |
| tion (Bara, | 2020). | Over | the last few | years, | this field | has |               |           |                                      |            |     |            |     |          |
|             |        |      |              |        |            |     | &Farid,2018). |           | Ourfindingsstronglysuggesttheneedfor |            |     |            |     |          |
temperingtheoptimismaboutpredictivemodelinginthe
|     |     |     |     |     |     |     | field of           | civil war | prediction                      |     | and question |     | the use | of ML    |
| --- | --- | --- | --- | --- | --- | --- | ------------------ | --------- | ------------------------------- | --- | ------------ | --- | ------- | -------- |
|     |     |     |     |     |     |     | modelsinthisfield. |           | Weprovideadetailedoverviewofour |     |              |     |         |          |
|     |     |     |     |     |     |     | methodology        | for       | correcting                      |     | the errors   | and | show    | that our |
resultsholdunderseveralrobustnesschecksinAppendixB.
|     |     |     |     |     |     |     | Finding2:   | Nosignificancetestingoruncertaintyquan- |     |     |     |     |     |     |
| --- | --- | --- | --- | --- | --- | --- | ----------- | --------------------------------------- | --- | --- | --- | --- | --- | --- |
|     |     |     |     |     |     |     | tification. | Wefoundthat9ofthe12papersforwhichcom-   |     |     |     |     |     |     |
pletecodeanddatawereavailableincludednosignificance
Figure2.Numberofpoliticalsciencepaperscontainingtheterms testsoruncertaintyquantificationforclassifierperformance
"civilwar"AND"machinelearning"inthedimensionsdatabase comparison(TableA6). Especiallywhensamplesizesare
ofacademicresearch(Hooketal.,2018).Notethesharpincrease small,significancetestinganduncertaintyquantificationare
inpapersusingMLmethodsinthelastfewyears.

LeakageandtheReproducibilityCrisisinML-basedScience KapoorandNarayanan
importantstepstowardsreproducibility(McDermottetal., Error Rate for a task), then once the achievable accuracy
2021; Gorman & Bedrick, 2019). As an illustration, we hasbeenreached,wecanavoidafutileefforttoincreaseit
examinethisissueindetailinthecaseofBlair&Sambanis furtherandcanapplyincreasedskepticismtowardsresults
(2020)sincetheirtestdatasethasaparticularlysmallnum- thatclaimtoviolateknownbounds.
| berofinstancesofcivilwaronset(only11). |     |     |     |     | Theypropose |            |              |     |     |             |         |     |
| -------------------------------------- | --- | --- | --- | --- | ----------- | ---------- | ------------ | --- | --- | ----------- | ------- | --- |
|                                        |     |     |     |     |             | [D2] Hype, | overoptimism |     | and | publication | biases. | The |
amodelofcivilwaronsetthatusestheoreticallyinformed
hypeaboutcommercialAIapplicationscanspilloverinto
featuresandreportthatitoutperformsotherbaselinemodels
ML-basedscience,leadingtooveroptimismabouttheirper-
ofcivilwaronsetusingtheAUCmetriconanout-of-sample
|     |     |     |     |     |     | formance. | Non-replicablefindingsarecitedmorethanrepli- |     |     |     |     |     |
| --- | --- | --- | --- | --- | --- | --------- | -------------------------------------------- | --- | --- | --- | --- | --- |
dataset. Wefindthattheperformanceoftheirmodelisnot
cableones(Serra-Garcia&Gneezy,2021),whichcanresult
significantlybetterthanotherbaselinemodelsforcivilwar
prediction.3 in feedback loops of overoptimism in ML-based science.
Further, allmodelshavelargeconfidencein-
Besides,publicationbiasesthathavebeendocumentedin
| tervalsfortheirout-of-sampleperformance. |     |     |     |     | Forinstance, |     |     |     |     |     |     |     |
| ---------------------------------------- | --- | --- | --- | --- | ------------ | --- | --- | --- | --- | --- | --- | --- |
severalscientificfields(Shi&Lin,2019;Gurevitchetal.,
whilethesmoothedAUCperformancereportedbytheau-
|     |     |     |     |     |     | 2018) can | also | affect ML-based |     | science | (Hofman | et al., |
| --- | --- | --- | --- | --- | --- | --------- | ---- | --------------- | --- | ------- | ------- | ------- |
thorsis0.85,the95%confidenceintervalcalculatedusing
2017;Islametal.,2017).
bootstrappedtestsetre-samplingis[0.66-0.95].
|     |     |     |     |     |     | [R2] Treat | results | from | ML-based | science | as  | tentative. |
| --- | --- | --- | --- | --- | --- | ---------- | ------- | ---- | -------- | ------- | --- | ---------- |
Whenoveroptimismisprevalentinafield,itisimportant
| 5.Beyondleakage: |     |     | enhancingthe |     |     |           |      |         |          |          |       |             |
| ---------------- | --- | --- | ------------ | --- | --- | --------- | ---- | ------- | -------- | -------- | ----- | ----------- |
|                  |     |     |              |     |     | to engage | with | results | emerging | from the | field | critically. |
reproducibilityofML-basedscience
UntilreproducibilityissuesinML-basedsciencearewidely
|         |          |     |         |               |            | addressed | and | resolved, | results | from this | body | of work |
| ------- | -------- | --- | ------- | ------------- | ---------- | --------- | --- | --------- | ------- | --------- | ---- | ------- |
| We have | outlined | how | the use | of model info | sheets can |           |     |           |         |           |      |         |
addressdataleakageinML-basedscience. Inadditionto shouldbetreatedwithcaution.
leakage,wefoundanumberofotherreproducibilityissues
|                                              |       |     |         |                |            | [D3] Inadequate                           |     | expertise. |     | The rapid | adoption | of ML    |
| -------------------------------------------- | ----- | --- | ------- | -------------- | ---------- | ----------------------------------------- | --- | ---------- | --- | --------- | -------- | -------- |
| in our survey.                               | Here, | we  | present | five diagnoses | for repro- |                                           |     |            |     |           |          |          |
|                                              |       |     |         |                |            | methodsinascientificfieldcanleadtoerrors. |     |            |     |           |          | Thesecan |
| ducibilityfailuresinfieldsadoptingMLmethods. |       |     |         |                | Eachof     |                                           |     |            |     |           |          |          |
becausedduetothelackofexpertiseofdomainexpertsin
ourdiagnosesispairedwitharecommendationtoaddress usingMLmethodsandvice-versa.
it.
|     |     |     |     |     |     | [R3] Inter-disciplinary |     |     | collaborations | and | communica- |     |
| --- | --- | --- | --- | --- | --- | ----------------------- | --- | --- | -------------- | --- | ---------- | --- |
[D1] Lack of understanding of the limits to prediction. tion of best-practices. Literature in the ML community
Recentresearchforpredictingsocialoutcomeshasshown
shouldaddressthedifferentfailuremodesthatariseduring
| that even | with | complex | models | and large | datasets, there |              |          |     |             |      |           |       |
| --------- | ---- | ------- | ------ | --------- | --------------- | ------------ | -------- | --- | ----------- | ---- | --------- | ----- |
|           |      |         |        |           |                 | the modeling | process. |     | Researchers | with | expertise | in ML |
arestronglimitstopredictiveperformance(Salganiketal.,
methodsshouldclearlycommunicatebestpracticesinde-
| 2020; Dressel | &   | Farid, | 2018). | However, | results like the |     |     |     |     |     |     |     |
| ------------- | --- | ------ | ------ | -------- | ---------------- | --- | --- | --- | --- | --- | --- | --- |
ployingMLforscientificresearch(Lones,2021).Havingan
better-than-humanperformanceofMLmodelsinperception interdisciplinaryteamconsistingofresearcherswithdomain
taskssuchasimageclassification(Heetal.,2015;Szeliski,
expertiseaswellasMLexpertisecanavoiderrors.
2021)givetheimpressionofMLmodelssurpassinghuman
|             |              |     |       |                        |     | [D4]Lackofstandardization. |     |     |     | SeveralappliedMLfields, |     |     |
| ----------- | ------------ | --- | ----- | ---------------------- | --- | -------------------------- | --- | --- | --- | ----------------------- | --- | --- |
| performance | acrosstasks, |     | which | can confuseresearchers |     |                            |     |     |     |                         |     |     |
abouttheperformancetheyshouldrealisticallyexpectfrom such as engineering applications and modeling contests,
haveadoptedpracticessuchasstandardizedtrain-testsplits,
MLmodels.
evaluationmetrics,andmodelingtaskstoensurethevalidity
[R1]Understandandcommunicatelimitstoprediction.
ofthemodelingandevaluationprocess(Russakovskyetal.,
A research agenda which investigates the efficacy of ML 2015;Kohetal.,2021). However,manyofthesehavenot
modelsintasksacrossscientificfieldswouldincreaseour
|                                       |     |     |     |                  |     | yetbeenadoptedwidelyinML-basedscience. |     |     |     |     |     | Thisleads |
| ------------------------------------- | --- | --- | --- | ---------------- | --- | -------------------------------------- | --- | --- | --- | --- | --- | --------- |
| understandingofthelimitstoprediction. |     |     |     | Thiscanalleviate |     |                                        |     |     |     |     |     |           |
tosubtleerrorsinthemodelingprocessthatcanbehardto
| theoveroptimismthatarisesfromconfusingprogressinone |     |     |     |     |     | detect. |     |     |     |     |     |     |
| --------------------------------------------------- | --- | --- | --- | --- | --- | ------- | --- | --- | --- | --- | --- | --- |
task(e.g.,imageclassification)withanother(e.g.,predicting
socialoutcomes). Ifwecanidentifyupperboundsonthe [R4]Adoptthecommontaskframeworkwhenpossible.
Thecommontaskframeworkallowsustocomparetheper-
| predictive | accuracy | of  | tasks | (i.e., lower bound | the Bayes |     |     |     |     |     |     |     |
| ---------- | -------- | --- | ----- | ------------------ | --------- | --- | --- | --- | --- | --- | --- | --- |
formanceofcompetingMLmodelsusinganagreed-upon
3Z=0.64,1.09,0.42,0.67;p=0.26,0.14,0.34,0.25foraone- training dataset and evaluation metrics, a secret holdout
tailedsignificancetestcomparingthesmoothedAUCperformance
dataset,andapublicleaderboard(Rocca&Yarkoni,2021;
ofthemodelproposedinthepaper—theescalationmodel—with
|                                               |     |     |     |     |            | Donoho,2017). |     | Datasetcreationandmodelevaluationis |     |     |     |     |
| --------------------------------------------- | --- | --- | --- | --- | ---------- | ------------- | --- | ----------------------------------- | --- | --- | --- | --- |
| otherbaselinemodelsreportedintheirpaper—quad, |     |     |     |     | goldstein, |               |     |                                     |     |     |     |     |
lefttoimpartialthirdpartieswhohavetheexpertiseandin-
| cameoandaveragerespectively. |     |     |     | Weimplementthecomparison |     |     |     |     |     |     |     |     |
| ---------------------------- | --- | --- | --- | ------------------------ | --- | --- | --- | --- | --- | --- | --- | --- |
testforsmoothedROCcurvesdetailedbyRobinetal.(Robinetal., centivestoavoiderrors. However,oneundesirableoutcome
2011).Notethatwedonotcorrectformultiplecomparisons;such thathasbeenobservedincommunitiesthathaveadoptedthe
acorrectionwouldfurtherreducethesignificanceoftheresults.
commontaskframeworkisasingularfocusonoptimizinga

LeakageandtheReproducibilityCrisisinML-basedScience KapoorandNarayanan
| particularaccuracymetrictotheexclusionofotherscientific |     |     |     |     |     |     | References |     |     |     |     |     |     |
| ------------------------------------------------------- | --- | --- | --- | --- | --- | --- | ---------- | --- | --- | --- | --- | --- | --- |
andnormativelydesirablepropertiesofmodels(Paullada
Imputationbeforeoraftersplittingintotrainandtest?(URL:
etal.,2020;Marieetal.,2021;Gorman&Bedrick,2019).
https://stats.stackexchange.com/questions/95083/imputation-
[D5]Lackofcomputationalreproducibility. Thelackof before-or-after-splitting-into-train-and-test).
computationalreproducibilityhindersverificationofresults
|                                       |     |     |     |     |               |     | Easing | the burden | of code | review. |     | Nature | Methods, |
| ------------------------------------- | --- | --- | --- | --- | ------------- | --- | ------ | ---------- | ------- | ------- | --- | ------ | -------- |
| byindependentresearchers(Section2.5). |     |     |     |     | Whilecomputa- |     |        |            |         |         |     |        |          |
tionalreproducibilitydoesnotmeanthatthecodeiserror- 15(9):641–641, September 2018. ISSN 1548-7105.
|     |     |     |     |     |     |     | Bandiera_abtest: |     | aCg_type: |     | NatureResearchJournals |     |     |
| --- | --- | --- | --- | --- | --- | --- | ---------------- | --- | --------- | --- | ---------------------- | --- | --- |
free,itcanmaketheprocessoffindingerrorseasier,since
|     |     |     |     |     |     |     | Number: | 9   | Primary_atype: |     | Editorial | Publisher: | Na- |
| --- | --- | --- | --- | --- | --- | --- | ------- | --- | -------------- | --- | --------- | ---------- | --- |
researchersattemptingtoreproduceresultsdonothaveto
|     |     |     |     |     |     |     | turePublishingGroupSubject_term: |     |     |     |     | Computationalbi- |     |
| --- | --- | --- | --- | --- | --- | --- | -------------------------------- | --- | --- | --- | --- | ---------------- | --- |
spendtimegettingthecodetorun.
|             |               |     |     |                  |     |           | ology | and bioinformatics;Publishing |     |     |     | Subject_term_id: |     |
| ----------- | ------------- | --- | --- | ---------------- | --- | --------- | ----- | ----------------------------- | --- | --- | --- | ---------------- | --- |
| [R5] Ensure | computational |     |     | reproducibility. |     | Platforms |       |                               |     |     |     |                  |     |
computational-biology-and-bioinformatics;publishing.
suchasCodeOcean(Clyburne-Sherinetal.,2019),acloud
http://archive.
computing platform which replicates the exact computa- ScimagoJournalandCountryRank.
tionalenvironmentusedtocreatetheoriginalresults,can today/oUs4K,2020.
beusedtoensurethelongtermreproducibilityofresults.
|     |     |     |     |     |     |     | Alves, V. | M., Borba, | J., | Capuzzi, | S. J., | Muratov, | E., An- |
| --- | --- | --- | --- | --- | --- | --- | --------- | ---------- | --- | -------- | ------ | -------- | ------- |
Wefollowseveralacademicjournalsandresearchersinrec-
|     |     |     |     |     |     |     | drade, | C. H., | Rusyn, | I., and | Tropsha, | A.  | Oy Vey! A |
| --- | --- | --- | --- | --- | --- | --- | ------ | ------ | ------ | ------- | -------- | --- | --------- |
ommendingthatfutureresearchinfieldsusingMLmethods
|     |     |     |     |     |     |     | Comment | on  | “Machine | Learning | of  | Toxicological | Big |
| --- | --- | --- | --- | --- | --- | --- | ------- | --- | -------- | -------- | --- | ------------- | --- |
shouldusesimilarmethodstoensurecomputationalrepro-
DataEnablesRead-AcrossStructureActivityRelation-
ducibility(noa,2018;Liu&Salganik,2019).
|              |     |     |     |     |     |     | shipsOutperformingAnimalTestReproducibility”. |           |             |     |         |       | Tox- |
| ------------ | --- | --- | --- | --- | --- | --- | --------------------------------------------- | --------- | ----------- | --- | ------- | ----- | ---- |
|              |     |     |     |     |     |     | icological                                    | Sciences, | 167(1):3–4, |     | January | 2019. | ISSN |
| 6.Conclusion |     |     |     |     |     |     | 1096-6080.                                    |           |             |     |         |       |      |
The attractiveness of adopting ML methods in scientific Arp,D.,Quiring,E.,Pendlebury,F.,Warnecke,A.,Pierazzi,
researchisinpartduetothewidespreadavailabilityofoff-
|     |     |     |     |     |     |     | F., Wressnegger, |     | C., Cavallaro, |     | L., | and Rieck, | K. Dos |
| --- | --- | --- | --- | --- | --- | --- | ---------------- | --- | -------------- | --- | --- | ---------- | ------ |
the-shelf tools to create models without expertise in ML andDon’tsofMachineLearninginComputerSecurity.
| methods | (Hutson, | 2019). | However, | this | laissez | faire ap- |     |     |     |     |     |     |     |
| ------- | -------- | ------ | -------- | ---- | ------- | --------- | --- | --- | --- | --- | --- | --- | --- |
USENIXSecuritySymposium,2022.
proachleadstocommonpitfallsspreadingtoallscientific
fields that use ML. So far, each research community has Athey, S. and Imbens, G. W. Machine Learning Meth-
independentlyrediscoveredthesepitfalls. Withoutfunda- ods That Economists Should Know About. An-
|     |     |     |     |     |     |     | nual | Review | of Economics, |     | 11(1):685–725, |     | 2019. |
| --- | --- | --- | --- | --- | --- | --- | ---- | ------ | ------------- | --- | -------------- | --- | ----- |
mentalchangestoresearchandreportingpractices,werisk
losingpublictrustowingtotheseverityandprevalenceof _eprint: https://doi.org/10.1146/annurev-economics-
| the reproducibility |                   | crisis  | across       | disciplines. | Our            | paper is  | 080217-053433.           |                                          |      |                         |     |     |        |
| ------------------- | ----------------- | ------- | ------------ | ------------ | -------------- | --------- | ------------------------ | ---------------------------------------- | ---- | ----------------------- | --- | --- | ------ |
| a call for          | interdisciplinary |         | efforts      | to address   | the            | crisis by |                          |                                          |      |                         |     |     |        |
|                     |                   |         |              |              |                |           | Bara,C.                  | Forecastingcivilwarandpoliticalviolence. |      |                         |     |     | Rout-  |
| developing          | and               | driving | the adoption | of           | best practices | for       |                          |                                          |      |                         |     |     |        |
|                     |                   |         |              |              |                |           | ledge,                   | May 2020.                                | ISBN | 978-1-00-302242-8.      |     |     | Pages: |
| ML-based            | science.          | Model   |              | info sheets  | for detecting  | and       |                          |                                          |      |                         |     |     |        |
|                     |                   |         |              |              |                |           | 177-193PublicationTitle: |                                          |      | ThePoliticsandScienceof |     |     |        |
preventingleakageareafirststepinthatdirection.
Prevision.
| Materials | and | methods.   | The | code and  | data required | to     |                                                |     |     |     |     |     |     |
| --------- | --- | ---------- | --- | --------- | ------------- | ------ | ---------------------------------------------- | --- | --- | --- | --- | --- | --- |
|           |     |            |     |           |               |        | Barnett,E.,Onete,D.,Salekin,A.,andFaraone,S.V. |     |     |     |     |     | Ge- |
| reproduce | our | case study | on  | civil war | prediction    | is up- |                                                |     |     |     |     |     |     |
loaded to a CodeOcean capsule (https://doi.org/ nomicMachineLearningMeta-regression: Insightson
|                          |     |     |     |                    |     |     | Associations |     | of Study | Features | with | Reported | Model |
| ------------------------ | --- | --- | --- | ------------------ | --- | --- | ------------ | --- | -------- | -------- | ---- | -------- | ----- |
| 10.24433/CO.4899453.v1). |     |     |     | AppendixBcontainsa |     |     |              |     |          |          |      |          |       |
detaileddescriptionofourmethodsandresultsfromaddi- Performance. Technicalreport,medRxiv,January2022.
| tionalrobustnesschecks. |     |     |     |     |     |     | Type: | article. |     |     |     |     |     |
| ----------------------- | --- | --- | --- | --- | --- | --- | ----- | -------- | --- | --- | --- | --- | --- |
Acknowledgements. WearegratefultoJessicaHullman, Becker,D. DataLeakage,2018.
MatthewJ.SalganikandBrandonStewartfortheirvaluable
|          |           |     |             |          |        |        | Beger,A. | @andybeega(AndreasBeger): |             |     |              | Thisisgreat.One |               |
| -------- | --------- | --- | ----------- | -------- | ------ | ------ | -------- | ------------------------- | ----------- | --- | ------------ | --------------- | ------------- |
| feedback | on drafts | of  | this paper. | We thank | Robert | Blair, |          |                           |             |     |              |                 |               |
|          |           |     |             |          |        |        | thing    | I’d add                   | is that for | the | @DMuchlinski |                 | et al data... |
AaronKaufman,DavidMuchlinskiandYuWangforquick
http://archive.today/VV9nC,2021.
| andhelpfulresponsestodraftsofthispaper. |     |     |     |     | Weareespe- |     |     |     |     |     |     |     |     |
| --------------------------------------- | --- | --- | --- | --- | ---------- | --- | --- | --- | --- | --- | --- | --- | --- |
ciallythankfultoMatthewSun,whoreviewedourcodeand
|     |     |     |     |     |     |     | Beger, A., | Morgan, | R.K., | andWard, |     | M.D. | Reassessing |
| --- | --- | --- | --- | --- | --- | --- | ---------- | ------- | ----- | -------- | --- | ---- | ----------- |
providedhelpfulsuggestionsandcorrectionsforensuring
theRoleofTheoryandMachineLearninginForecast-
thecomputationalreproducibilityofourownresults,and
|     |     |     |     |     |     |     | ing Civil | Conflict. | Journal |     | of Conflict | Resolution, | pp. |
| --- | --- | --- | --- | --- | --- | --- | --------- | --------- | ------- | --- | ----------- | ----------- | --- |
toAngelinaWang,OrestisPapakyriakopolous,andAnne
|     |     |     |     |     |     |     | 0022002720982358,July2021. |     |     |     | ISSN0022-0027. |     | Pub- |
| --- | --- | --- | --- | --- | --- | --- | -------------------------- | --- | --- | --- | -------------- | --- | ---- |
Kohlbrennerfortheirfeedbackonmodelinfosheets. lisher: SAGEPublicationsInc.

LeakageandtheReproducibilityCrisisinML-basedScience KapoorandNarayanan
Bell,S.J.andKampman,O.P. PerspectivesonMachine Colaresi,M.andMahmood,Z. Dotherobot: Lessonsfrom
LearningfromPsychology’sReproducibilityCrisis.April machinelearningtoimproveconflictforecasting.Journal
| 2021.      |              |       |              |            | ofPeaceResearch,54(2):193–214,March2017. |                                 |     |     | ISSN |
| ---------- | ------------ | ----- | ------------ | ---------- | ---------------------------------------- | ------------------------------- | --- | --- | ---- |
|            |              |       |              |            | 0022-3433.                               | Publisher: SAGEPublicationsLtd. |     |     |      |
| Blagus, R. | and Lusa, L. | Joint | use of over- | and under- |                                          |                                 |     |     |      |
samplingtechniquesandcross-validationforthedevelop- Collier,P.andHoeffler,A. OntheIncidenceofCivilWar
mentandassessmentofpredictionmodels. BMCBioin- inAfrica. JournalofConflictResolution,46(1):13–28,
formatics,16(1):363,November2015. ISSN1471-2105. February 2002. ISSN 0022-0027. Publisher: SAGE
PublicationsInc.
| Blair,R.A.andSambanis,N. |     | ForecastingCivilWars: |     | The- |     |     |     |     |     |
| ------------------------ | --- | --------------------- | --- | ---- | --- | --- | --- | --- | --- |
oryandStructureinanAgeof“BigData”andMachine Collins,G.S.,Reitsma,J.B.,Altman,D.G.,andMoons,
| Learning. | JournalofConflictResolution,64(10):1885– |     |     |     |     |     |     |     |     |
| --------- | ---------------------------------------- | --- | --- | --- | --- | --- | --- | --- | --- |
K.G. Transparentreportingofamultivariableprediction
1915, November 2020. ISSN 0022-0027. Publisher: modelforindividualprognosisordiagnosis(TRIPOD):
SAGEPublicationsInc. theTRIPODStatement. BMCMedicine,13(1):1,January
2015. ISSN1741-7015.
| Blair,R.A.andSambanis,N. |            | IsTheoryUsefulforConflict |         |           |                   |                         |     |     |        |
| ------------------------ | ---------- | ------------------------- | ------- | --------- | ----------------- | ----------------------- | --- | --- | ------ |
| Prediction?              | A Response | to Beger,                 | Morgan, | and Ward. |                   |                         |     |     |        |
|                          |            |                           |         |           | Collins-Thompson, | K. DataLeakage-Module4: |     |     | Super- |
JournalofConflictResolution,pp.00220027211026748, visedMachineLearning-Part2.
| July2021. | ISSN0022-0027. | Publisher: |     | SAGEPublica- |                 |                                         |     |     |     |
| --------- | -------------- | ---------- | --- | ------------ | --------------- | --------------------------------------- | --- | --- | --- |
|           |                |            |     |              | Dietterich,T.G. | Approximatestatisticaltestsforcomparing |     |     |     |
tionsInc.
Neural
|     |     |     |     |     | supervised | classification learning | algorithms. |     |     |
| --- | --- | --- | --- | --- | ---------- | ----------------------- | ----------- | --- | --- |
Bone, D., Goodwin, M.S., Black, M.P., Lee, C.-C., Au- computation,10(7):1895–1923,1998.
| dhkhasi, | K., and Narayanan, |     | S. Applying | Machine |     |     |     |     |     |
| -------- | ------------------ | --- | ----------- | ------- | --- | --- | --- | --- | --- |
LearningtoFacilitateAutismDiagnostics: Pitfallsand Donders, A. R. T., van der Heijden, G. J. M. G., Stijnen,
|           |            |        |                   |      | T.,andMoons,K.G.M. | Review: | Agentleintroduction |     |     |
| --------- | ---------- | ------ | ----------------- | ---- | ------------------ | ------- | ------------------- | --- | --- |
| Promises. | Journal of | Autism | and Developmental | Dis- |                    |         |                     |     |     |
orders,45(5):1121–1136,May2015. ISSN0162-3257, to imputation of missing values. Journal of Clinical
|     |     |     |     |     | Epidemiology,59(10):1087–1091,October2006. |     |     |     | ISSN |
| --- | --- | --- | --- | --- | ------------------------------------------ | --- | --- | --- | ---- |
1573-3432.
0895-4356.
Bouwmeester,W.,Zuithoff,N.P.A.,Mallett,S.,Geerlings,
|     |     |     |     |     | Donoho, D. | 50 Years | of Data | Science. | Jour- |
| --- | --- | --- | --- | --- | ---------- | -------- | ------- | -------- | ----- |
M.I.,Vergouwe,Y.,Steyerberg,E.W.,Altman,D.G.,
andMoons, K.G.M. ReportingandMethodsinClin- nal of Computational and Graphical Statistics,
|                         |     |                    |     |      | 26(4):745–766, | October | 2017. | ISSN | 1061- |
| ----------------------- | --- | ------------------ | --- | ---- | -------------- | ------- | ----- | ---- | ----- |
| icalPredictionResearch: |     | ASystematicReview. |     | PLOS |                |         |       |      |       |
Medicine,9(5):e1001221,May2012. ISSN1549-1676. 8600. Publisher: Taylor & Francis _eprint:
Publisher: PublicLibraryofScience. https://doi.org/10.1080/10618600.2017.1384734.
Brownlee,J. DataLeakageinMachineLearning,August Dressel,J.andFarid,H. Theaccuracy,fairness,andlimits
|     |     |     |     |     | ofpredictingrecidivism. | Scienceadvances,4(1),2018. |     |     |     |
| --- | --- | --- | --- | --- | ----------------------- | -------------------------- | --- | --- | --- |
2016.
|     |     |     |     |     | ErikGundersen,O. | Thefundamentalprinciplesofrepro- |     |     |     |
| --- | --- | --- | --- | --- | ---------------- | -------------------------------- | --- | --- | --- |
Carter,B.,Jain,S.,Mueller,J.,andGifford,D.Overinterpre-
tationrevealsimageclassificationmodelpathologies. Ad- ducibility. PhilosophicalTransactionsoftheRoyalSoci-
vancesinNeuralInformationProcessingSystems,2021. etyA:Mathematical,PhysicalandEngineeringSciences,
|                           |     |                         |     |     | 379(2197):20200210,May2021. |     | Publisher: | RoyalSoci- |     |
| ------------------------- | --- | ----------------------- | --- | --- | --------------------------- | --- | ---------- | ---------- | --- |
| Chiba,D.andGleditsch,K.S. |     | Theshapeofthingstocome? |     |     |                             |     |            |            |     |
ety.
Expandingtheinequalityandgrievancemodelforcivil
warforecastswitheventdata. JournalofPeaceResearch, Fawcett, T. An introduction to ROC analysis. Pattern
54(2):275–297,March2017.ISSN0022-3433.Publisher: Recognition Letters, 27(8):861–874, June 2006. ISSN
| SAGEPublicationsLtd. |     |     |     |     | 0167-8655. |     |     |     |     |
| -------------------- | --- | --- | --- | --- | ---------- | --- | --- | --- | --- |
Christodoulou,E.,Ma,J.,Collins,G.S.,Steyerberg,E.W., Fearon,J.D.andLaitin,D.D. Ethnicity,Insurgency,and
Verbakel,J.Y.,andVanCalster,B. Asystematicreview Civil War. The American Political Science Review, 97
showsnoperformancebenefitofmachinelearningover (1):75–90,2003. ISSN0003-0554. Publisher: [Ameri-
logisticregressionforclinicalpredictionmodels. Journal canPoliticalScienceAssociation,CambridgeUniversity
| ofClinicalEpidemiology,110:12–22,June2019. |     |     |     | ISSN | Press]. |     |     |     |     |
| ------------------------------------------ | --- | --- | --- | ---- | ------- | --- | --- | --- | --- |
0895-4356.
|     |     |     |     |     | Filho,A.C.,Batista,A.F.D.M.,andSantos,H.G.d. |     |     |     | Data |
| --- | --- | --- | --- | --- | -------------------------------------------- | --- | --- | --- | ---- |
Clyburne-Sherin,A.,Fei,X.,andGreen,S.A. Computa- LeakageinHealthOutcomesPredictionWithMachine
tionalreproducibilityviacontainersinsocialpsychology. Learning. Comment on “Prediction of Incident Hyper-
Meta-Psychology,3,2019. tensionWithintheNextYear: ProspectiveStudyUsing

LeakageandtheReproducibilityCrisisinML-basedScience KapoorandNarayanan
StatewideElectronicHealthRecordsandMachineLearn- Han, S., Olonisakin, T.F., Pribis, J.P., Zupetic, J., Yoon,
ing”.JournalofMedicalInternetResearch,23(2):e10969, J. H., Holleran, K. M., Jeong, K., Shaikh, N., Rubio,
February2021. Company: JournalofMedicalInternet D. M., and Lee, J. S. A checklist is associated with
Research Distributor: Journal of Medical Internet Re- increasedqualityofreportingpreclinicalbiomedicalre-
searchInstitution: JournalofMedicalInternetResearch search:Asystematicreview.PLoSONE,12(9):e0183591,
Label: JournalofMedicalInternetResearchPublisher: September2017. ISSN1932-6203.
JMIRPublicationsInc.,Toronto,Canada.
|     |     |     |     |     |     | He, K., | Zhang, | X., Ren, | S., and | Sun, | J. Delving | deep |
| --- | --- | --- | --- | --- | --- | ------- | ------ | -------- | ------- | ---- | ---------- | ---- |
Fraser,C. TheTreacheryofLeakage,August2016. intorectifiers: Surpassinghuman-levelperformanceon
|                        |     |     |                          |     |     | imagenetclassification. |     |     | CoRR,abs/1502.01852,2015. |     |     |     |
| ---------------------- | --- | --- | ------------------------ | --- | --- | ----------------------- | --- | --- | ------------------------- | --- | --- | --- |
| Garbin,C.andMarques,O. |     |     | AssessingMethodsandTools |     |     |                         |     |     |                           |     |     |     |
to Improve Reporting, Increase Transparency, and Re- Hegre, H. and Sambanis, N. Sensitivity Analysis of Em-
duceFailuresinMachineLearningApplicationsinHealth piricalResultsonCivilWarOnset:. JournalofConflict
| Care. Radiology: |     | ArtificialIntelligence,4(2):e210127, |     |     |     | Resolution,2006. |     |            |                         |     |     |     |
| ---------------- | --- | ------------------------------------ | --- | --- | --- | ---------------- | --- | ---------- | ----------------------- | --- | --- | --- |
|                  |     |                                      |     |     |     |                  |     | Publisher: | SagePublicationsSageCA: |     |     |     |
| March2022.       |     |                                      |     |     |     | ThousandOaks,CA. |     |            |                         |     |     |     |
Gebru,T.,Morgenstern,J.,Vecchione,B.,Vaughan,J.W., Hegre,H.,Buhaug,H.,Calvin,K.V.,Nordkvelle,J.,Wald-
Wallach,H.,III,H.D.,andCrawford,K. Datasheetsfor hoff, S. T., and Gilmore, E. Forecasting civil conflict
|     | Communications |     | of the | ACM, |     |     |     |     |     |     |     |     |
| --- | -------------- | --- | ------ | ---- | --- | --- | --- | --- | --- | --- | --- | --- |
datasets. 64(12):86–92, alongthesharedsocioeconomicpathways. Environmen-
November2021. ISSN0001-0782. tal Research Letters, 11(5):054002, April 2016. ISSN
|     |     |     |     |     |     | 1748-9326. | Publisher: |     | IOPPublishing. |     |     |     |
| --- | --- | --- | --- | --- | --- | ---------- | ---------- | --- | -------------- | --- | --- | --- |
Geirhos,R.,Rubisch,P.,Michaelis,C.,Bethge,M.,Wich-
mann,F.A.,andBrendel,W.ImageNet-trainedCNNsare
|     |     |     |     |     |     | Hegre, | H., Allansson, |     | M., Basedau, |     | M., Colaresi, | M., |
| --- | --- | --- | --- | --- | --- | ------ | -------------- | --- | ------------ | --- | ------------- | --- |
biasedtowardstexture;increasingshapebiasimproves Croicu, M., Fjelde, H., Hoyles, F., Hultman, L., Hög-
accuracyandrobustness. September2018. bladh, S., Jansen, R., Mouhleb, N., Muhammad, S.A.,
Nilsson,D.,Nygård,H.M.,Olafsdottir,G.,Petrova,K.,
Geirhos,R.,Jacobsen,J.-H.,Michaelis,C.,Zemel,R.,Bren-
Randahl,D.,Rød,E.G.,Schneider,G.,Uexkull,N.v.,
| del, W., | Bethge, | M., and | Wichmann, | F. A. | Shortcut |     |     |     |     |     |     |     |
| -------- | ------- | ------- | --------- | ----- | -------- | --- | --- | --- | --- | --- | --- | --- |
andVestby,J.ViEWS:Apoliticalviolenceearly-warning
| learningindeepneuralnetworks. |     |     | NatureMachineIntelli- |     |     |     |     |     |     |     |     |     |
| ----------------------------- | --- | --- | --------------------- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
system:.JournalofPeaceResearch,February2019a.Pub-
gence,2(11):665–673,November2020.ISSN2522-5839.
lisher: SAGEPublicationsSageUK:London,England.
| Bandiera_abtest: |     | aCg_type: | NatureResearchJournals |     |     |     |     |     |     |     |     |     |
| ---------------- | --- | --------- | ---------------------- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
Number: 11 Primary_atype: Reviews Publisher: Na- Hegre, H., Hultman, L., and Nygård, H. M. Evaluating
| turePublishingGroupSubject_term: |     |     |     | Computationalsci- |     |     |     |     |     |     |     |     |
| -------------------------------- | --- | --- | --- | ----------------- | --- | --- | --- | --- | --- | --- | --- | --- |
theConflict-ReducingEffectofUNPeacekeepingOper-
ence;Humanbehaviour;Informationtechnology;Network ations. TheJournalofPolitics,81(1):215–232,January
| modelsSubject_term_id:                           |     |     | computational-science;human- |     |     |               |                |     |            |     |                 |     |
| ------------------------------------------------ | --- | --- | ---------------------------- | --- | --- | ------------- | -------------- | --- | ---------- | --- | --------------- | --- |
|                                                  |     |     |                              |     |     | 2019b.        | ISSN0022-3816. |     | Publisher: |     | TheUniversityof |     |
| behaviour;information-technology;network-models. |     |     |                              |     |     | ChicagoPress. |                |     |            |     |                 |     |
Ghani, R., Walsh, J., and Wang, J. Top 10 ways your Hegre,H.,Nygård,H.M.,andLandsverk,P.CanWePredict
| Machine | Learning | models | may have | leakage | (URL: |       |           |     |           |         |     |           |
| ------- | -------- | ------ | -------- | ------- | ----- | ----- | --------- | --- | --------- | ------- | --- | --------- |
|         |          |        |          |         |       | Armed | Conflict? | How | the First | 9 Years | of  | Published |
http://www.rayidghani.com/2020/01/24/top-10-ways-
|     |     |     |     |     |     | Forecasts | Stand | Up to | Reality. | International |     | Studies |
| --- | --- | --- | --- | --- | --- | --------- | ----- | ----- | -------- | ------------- | --- | ------- |
your-machine-learning-models-may-have-leakage/), Quarterly,(sqaa094),January2021. ISSN0020-8833.
January2020.
|                        |     |             |                        |             |       | Hirose,                   | K., Imai, | K., and | Lyall,                   | J. Can | civilian | attitudes |
| ---------------------- | --- | ----------- | ---------------------- | ----------- | ----- | ------------------------- | --------- | ------- | ------------------------ | ------ | -------- | --------- |
| Gorman,K.andBedrick,S. |     |             | WeNeedtoTalkaboutStan- |             |       |                           |           |         |                          |        |          |           |
|                        |     |             |                        |             |       | predictinsurgentviolence? |           |         | Ideologyandinsurgenttac- |        |          |           |
|                        |     | Proceedings | of the                 | 57th Annual | Meet- |                           |           |         |                          |        |          |           |
dard Splits. In ticalchoiceincivilwar. JournalofPeaceResearch,54
ingoftheAssociationforComputationalLinguistics,pp.
|     |     |     |     |     |     | (1):47–63, | January2017. |     | ISSN0022-3433. |     |     | Publisher: |
| --- | --- | --- | --- | --- | --- | ---------- | ------------ | --- | -------------- | --- | --- | ---------- |
2786–2791,Florence,Italy,July2019.Associationfor
SAGEPublicationsLtd.
ComputationalLinguistics.
|     |     |     |     |     |     | Hofman, | J. M., | Sharma, | A., and | Watts, | D. J. | Prediction |
| --- | --- | --- | --- | --- | --- | ------- | ------ | ------- | ------- | ------ | ----- | ---------- |
Gurevitch, J., Koricheva, J., Nakagawa, S., and Stew- andexplanationinsocialsystems. Science,355(6324):
| art, G.           | Meta-analysis |            | and                | the science | of re- |                       |                                      |         |                          |     |     |     |
| ----------------- | ------------- | ---------- | ------------------ | ----------- | ------ | --------------------- | ------------------------------------ | ------- | ------------------------ | --- | --- | --- |
|                   |               |            |                    |             |        | 486–488,February2017. |                                      |         | ISSN0036-8075,1095-9203. |     |     |     |
| search synthesis. |               | Nature,    | 555(7695):175–182, |             | March  |                       |                                      |         |                          |     |     |     |
|                   |               |            |                    |             |        | Publisher:            | AmericanAssociationfortheAdvancement |         |                          |     |     |     |
| 2018.             | ISSN          | 1476-4687. | Bandiera_abtest:   |             | a      |                       |                                      |         |                          |     |     |     |
|                   |               |            |                    |             |        | ofScienceSection:     |                                      | Essays. |                          |     |     |     |
| Cg_type:          | Nature        | Research   | Journals           | Number:     | 7695   |                       |                                      |         |                          |     |     |     |
Primary_atype: Reviews Publisher: Nature Publishing Hofman, J. M., Goldstein, D. G., Sen, S., Poursabzi-
Group Subject_term: Biodiversity;Outcomes research Sangdeh,F.,Allen,J.,Dong,L.L.,Fried,B.,Gaur,H.,
Subject_term_id: biodiversity;outcomes-research. Hoq, A., Mbazor, E., Moreira, N., Muso, C., Rapp, E.,

LeakageandtheReproducibilityCrisisinML-basedScience KapoorandNarayanan
andTerrero,R.Expandingthescopeofreproducibilityre- Kaufman,S.,Rosset,S.,Perlich,C.,andStitelman,O.Leak-
searchthroughdataanalysisreplications. Organizational age in data mining: Formulation, detection, and avoid-
BehaviorandHumanDecisionProcesses,164:192–202, ance. ACMTransactionsonKnowledgeDiscoveryfrom
May2021a. ISSN0749-5978. Data, 6(4):15:1–15:21, December 2012. ISSN 1556-
4681.
Hofman,J.M.,Watts,D.J.,Athey,S.,Garip,F.,Griffiths,
T.L.,Kleinberg,J.,Margetts,H.,Mullainathan,S.,Sal- Koh,P.W.,Sagawa,S.,Marklund,H.,Xie,S.M.,Zhang,
ganik, M. J., Vazire, S., Vespignani, A., and Yarkoni, M., Balsubramani, A., Hu, W., Yasunaga, M., Phillips,
T. Integrating explanation and prediction in computa- R.L.,Gao,I.,Lee,T.,David,E.,Stavness,I.,Guo,W.,
Earnshaw,B.,Haque,I.,Beery,S.M.,Leskovec,J.,Kun-
| tionalsocialscience. |     | Nature,595(7866):181–188,July |     |     |     |     |     |     |     |
| -------------------- | --- | ----------------------------- | --- | --- | --- | --- | --- | --- | --- |
2021b. ISSN1476-4687. Bandiera_abtest: aCg_type: daje,A.,Pierson,E.,Levine,S.,Finn,C.,andLiang,P.
NatureResearchJournalsNumber: 7866Primary_atype: WILDS:ABenchmarkofin-the-WildDistributionShifts.
Reviews Publisher: Nature Publishing Group Sub- InProceedingsofthe38thInternationalConferenceon
ject_term: Interdisciplinary studies;Scientific commu- Machine Learning, pp. 5637–5664. PMLR, July 2021.
ISSN:2640-3498.
| nitySubject_term_id: |     | interdisciplinary-studies;scientific- |     |     |     |     |     |     |     |
| -------------------- | --- | ------------------------------------- | --- | --- | --- | --- | --- | --- | --- |
community.
|     |     |     |     |     |     | Kuhn, M. | and Johnson, | K. Applied Predictive | Modeling. |
| --- | --- | --- | --- | --- | --- | -------- | ------------ | --------------------- | --------- |
Hook, D. W., Porter, S. J., and Herzog, C. Dimensions: Springer-Verlag, New York, 2013. ISBN 978-1-4614-
| BuildingContextforSearchandEvaluation. |            |            |     | Frontiers |     | 6848-6.               |                              |                               |      |
| -------------------------------------- | ---------- | ---------- | --- | --------- | --- | --------------------- | ---------------------------- | ----------------------------- | ---- |
| inResearchMetricsandAnalytics,3,2018.  |            |            |     | ISSN2504- |     |                       |                              |                               |      |
|                                        |            |            |     |           |     | Leek,J.T.andPeng,R.D. |                              | Opinion: Reproducibleresearch |      |
| 0537.                                  | Publisher: | Frontiers. |     |           |     |                       |                              |                               |      |
|                                        |            |            |     |           |     | canstillbewrong:      | Adoptingapreventionapproach. |                               | Pro- |
Hullman,J.,Kapoor,S.,Nanayakkara,P.,Gelman,A.,and ceedings of the National Academy of Sciences, 112(6):
|              |                       |     |     |              |     | 1645–1646,February2015. |     | ISSN0027-8424,1091-6490. |     |
| ------------ | --------------------- | --- | --- | ------------ | --- | ----------------------- | --- | ------------------------ | --- |
| Narayanan,A. | Theworstofbothworlds: |     |     | Acomparative |     |                         |     |                          |     |
analysisoferrorsinlearningfromdatainpsychologyand Publisher: NationalAcademyofSciencesSection: Opin-
|     |     | arXiv:2203.06498[cs],March2022. |     |     |     | ion. |     |     |     |
| --- | --- | ------------------------------- | --- | --- | --- | ---- | --- | --- | --- |
machinelearning.
arXiv: 2203.06498.
|           |                   |     |                     |     |     | Liu,D.M.andSalganik,M.J.      |     | Successesandstruggleswith |     |
| --------- | ----------------- | --- | ------------------- | --- | --- | ----------------------------- | --- | ------------------------- | --- |
|           |                   |     |                     |     |     | computationalreproducibility: |     | Lessonsfromthefragile     |     |
| Hutson,M. | Nocodingrequired: |     | Companiesmakeiteas- |     |     |                               |     |                           |     |
ier than ever for scientists to use artificial intelligence. familieschallenge. Socius,5:2378023119849803,2019.
ScienceNews,July2019.
|                         |                                         |     |                           |     |     | Lones, M.                    | A. How to avoid | machine learning      | pitfalls: a |
| ----------------------- | --------------------------------------- | --- | ------------------------- | --- | --- | ---------------------------- | --------------- | --------------------- | ----------- |
|                         |                                         |     |                           |     |     | guideforacademicresearchers. |                 | arXiv:2108.02497[cs], |             |
| Imbens,G.W.             | StatisticalSignificance,p-Values,andthe |     |                           |     |     |                              |                 |                       |             |
|                         |                                         |     |                           |     |     | August2021.                  | arXiv:          | 2108.02497.           |             |
| ReportingofUncertainty. |                                         |     | JournalofEconomicPerspec- |     |     |                              |                 |                       |             |
tives,35(3):157–174,August2021. ISSN0895-3309. Lundberg, I., Johnson, R., and Stewart, B. M. What Is
|                                    |     |     |     |                  |     | YourEstimand?                | DefiningtheTargetQuantityConnects |                      |     |
| ---------------------------------- | --- | --- | --- | ---------------- | --- | ---------------------------- | --------------------------------- | -------------------- | --- |
| Iniesta,R.,Stahl,D.,andMcGuffin,P. |     |     |     | Machinelearning, |     |                              |                                   |                      |     |
|                                    |     |     |     |                  |     | StatisticalEvidencetoTheory. |                                   | AmericanSociological |     |
statisticallearningandthefutureofbiologicalresearchin
|     |     |     |     |     |     | Review,86(3):532–565,June2021. |     | ISSN0003-1224. |     |
| --- | --- | --- | --- | --- | --- | ------------------------------ | --- | -------------- | --- |
PsychologicalMedicine,46(12):2455–2465,
psychiatry.
September2016.ISSN0033-2917,1469-8978.Publisher: Lyu, Y., Li, H., Sayagh, M., Jiang, Z. M. J., and Hassan,
CambridgeUniversityPress.
|            |            |                |     |                |     | A.E. AnEmpiricalStudyoftheImpactofDataSplitting |     |     |     |
| ---------- | ---------- | -------------- | --- | -------------- | --- | ----------------------------------------------- | --- | --- | --- |
|            |            |                |     |                |     | DecisionsonthePerformanceofAIOpsSolutions.      |     |     | ACM |
| Islam, R., | Henderson, | P., Gomrokchi, |     | M., andPrecup, | D.  |                                                 |     |     |     |
TransactionsonSoftwareEngineeringandMethodology,
| Reproducibility                    |     | of Benchmarked | Deep | Reinforcement |     |                      |     |                          |     |
| ---------------------------------- | --- | -------------- | ---- | ------------- | --- | -------------------- | --- | ------------------------ | --- |
|                                    |     |                |      |               |     | 30(4):1–38,July2021. |     | ISSN1049-331X,1557-7392. |     |
| LearningTasksforContinuousControl. |     |                |      | August2017.   |     |                      |     |                          |     |
Malik,M.M.AHierarchyofLimitationsinMachineLearn-
| Ivanescu, | A. E., Li, | P., George, | B., Brown, | A. W.,          | Keith, |                    |     |     |     |
| --------- | ---------- | ----------- | ---------- | --------------- | ------ | ------------------ | --- | --- | --- |
|           |            |             |            |                 |        | ing. February2020. |     |     |     |
| S.W.,     | Raju, D.,  | andAllison, | D.B.       | Theimportanceof |        |                    |     |     |     |
prediction model validation and assessment in obesity Marie,B.,Fujita,A.,andRubino,R. ScientificCredibility
| andnutritionresearch. |     | InternationalJournalofObesity, |     |     |     |                               |     |                    |     |
| --------------------- | --- | ------------------------------ | --- | --- | --- | ----------------------------- | --- | ------------------ | --- |
|                       |     |                                |     |     |     | ofMachineTranslationResearch: |     | AMeta-Evaluationof |     |
40(6):887–894,June2016. ISSN1476-5497. Number: 6 769Papers. arXiv:2106.15195[cs],June2021. arXiv:
| Publisher: | NaturePublishingGroup. |     |     |     |     | 2106.15195. |     |     |     |
| ---------- | ---------------------- | --- | --- | --- | --- | ----------- | --- | --- | --- |
Kaufman,A.R.,Kraft,P.,andSen,M. ImprovingSupreme McDermott,M.B.A.,Wang,S.,Marinsek,N.,Ranganath,
CourtForecastingUsingBoostedDecisionTrees. Politi- R., Foschini, L., andGhassemi, M. Reproducibilityin
calAnalysis,27(3):381–387,July2019.ISSN1047-1987, machine learning for health research: Still a ways to
1476-4989. Publisher: CambridgeUniversityPress. go. Science Translational Medicine, 13(586), March

LeakageandtheReproducibilityCrisisinML-basedScience KapoorandNarayanan
2021. ISSN1946-6234,1946-6242. Publisher: Ameri- Oner, M. U., Cheng, Y.-C., Lee, H. K., and Sung, W.-K.
canAssociationfortheAdvancementofScienceSection: Trainingmachinelearningmodelsonpatientleveldata
Perspective. segregation is crucial in practical clinical applications.
|     |     |     |     |     |     |     | Technical | report, | April | 2020. | Company: | Cold | Spring |
| --- | --- | --- | --- | --- | --- | --- | --------- | ------- | ----- | ----- | -------- | ---- | ------ |
Mitchell,M.,Wu,S.,Zaldivar,A.,Barnes,P.,Vasserman, HarborLaboratoryPressDistributor:ColdSpringHarbor
| L., Hutchinson,                 |     | B., Spitzer, |     | E., Raji, | I. D.,          | and Gebru, |                       |          |     |                            |     |     |     |
| ------------------------------- | --- | ------------ | --- | --------- | --------------- | ---------- | --------------------- | -------- | --- | -------------------------- | --- | --- | --- |
|                                 |     |              |     |           |                 |            | LaboratoryPressLabel: |          |     | ColdSpringHarborLaboratory |     |     |     |
| T. ModelCardsforModelReporting. |     |              |     |           | InProceedingsof |            | PressType:            | article. |     |                            |     |     |     |
theConferenceonFairness,Accountability,andTrans-
parency,FAT*’19,pp.220–229,NewYork,NY,USA,
|     |     |     |     |     |     |     | OpenScienceCollaboration. |     |     |     | Estimatingthereproducibility |     |     |
| --- | --- | --- | --- | --- | --- | --- | ------------------------- | --- | --- | --- | ---------------------------- | --- | --- |
January 2019. Association for Computing Machinery. of psychological science. Science, 349(6251), August
ISBN978-1-4503-6125-5.
|     |     |     |     |     |     |     | 2015. | ISSN0036-8075,1095-9203. |     |     | Publisher: |     | Ameri- |
| --- | --- | --- | --- | --- | --- | --- | ----- | ------------------------ | --- | --- | ---------- | --- | ------ |
canAssociationfortheAdvancementofScienceSection:
| Mongan,J.,Moy,L.,andKahn,C.E. |     |     |     | ChecklistforArtifi- |     |     | ResearchArticle. |     |     |     |     |     |     |
| ----------------------------- | --- | --- | --- | ------------------- | --- | --- | ---------------- | --- | --- | --- | --- | --- | --- |
cialIntelligenceinMedicalImaging(CLAIM):AGuide
| forAuthorsandReviewers. |     |     |     | Radiology: | ArtificialIntelli- |     |           |           |        |         |        |         |         |
| ----------------------- | --- | --- | --- | ---------- | ------------------ | --- | --------- | --------- | ------ | ------- | ------ | ------- | ------- |
|                         |     |     |     |            |                    |     | Paullada, | A., Raji, | I. D., | Bender, | E. M., | Denton, | E., and |
gence,2(2):e200029,March2020. Publisher: Radiologi- Hanna,A.Dataandits(dis)contents:Asurveyofdataset
calSocietyofNorthAmerica.
|     |     |     |     |     |     |     | developmentanduseinmachinelearningresearch. |     |     |     |     |     | arXiv |
| --- | --- | --- | --- | --- | --- | --- | ------------------------------------------- | --- | --- | --- | --- | --- | ----- |
preprintarXiv:2012.05345,2020.
| Muchlinski,D.,Siroky,D.,He,J.,andKocher,M. |     |     |     |     |     | Com- |     |     |     |     |     |     |     |
| ------------------------------------------ | --- | --- | --- | --- | --- | ---- | --- | --- | --- | --- | --- | --- | --- |
paringRandomForestwithLogisticRegressionforPre-
|                                           |     |     |     |     |     |           | Pineau,          | J., Vincent-Lamarre, |     |         | P., Sinha, | K.,      | Larivière, |
| ----------------------------------------- | --- | --- | --- | --- | --- | --------- | ---------------- | -------------------- | --- | ------- | ---------- | -------- | ---------- |
| dictingClass-ImbalancedCivilWarOnsetData. |     |     |     |     |     | Political |                  |                      |     |         |            |          |            |
|                                           |     |     |     |     |     |           | V., Beygelzimer, |                      | A., | d’Alché | Buc,       | F., Fox, | E., and    |
Analysis,24(1):87–103,2016. ISSN1047-1987,1476- Larochelle, H. Improving Reproducibility in Machine
| 4989.       | Publisher: | CambridgeUniversityPress. |     |         |             |       |                          |          |        |             |                            |         |      |
| ----------- | ---------- | ------------------------- | --- | ------- | ----------- | ----- | ------------------------ | -------- | ------ | ----------- | -------------------------- | ------- | ---- |
|             |            |                           |     |         |             |       | Learning                 | Research |        | (A Report   | from the                   | NeurIPS | 2019 |
|             |            |                           |     |         |             |       | ReproducibilityProgram). |          |        |             | arXiv:2003.12206[cs,stat], |         |      |
| Muchlinski, | D.         | A., Siroky,               | D., | He, J., | and Kocher, | M. A. |                          |          |        |             |                            |         |      |
|             |            |                           |     |         |             |       | December2020.            |          | arXiv: | 2003.12206. |                            |         |      |
SeeingtheForestthroughtheTrees.PoliticalAnalysis,27
| (1):111–113,January2019. |                           |         |       | ISSN1047-1987,1476-4989. |        |          |           |                                       |           |     |                |                |           |
| ------------------------ | ------------------------- | ------- | ----- | ------------------------ | ------ | -------- | --------- | ------------------------------------- | --------- | --- | -------------- | -------------- | --------- |
|                          |                           |         |       |                          |        |          | Poldrack, | R. A.,                                | Huckins,  | G., | and Varoquaux, |                | G. Estab- |
| Publisher:               | CambridgeUniversityPress. |         |       |                          |        |          |           |                                       |           |     |                |                |           |
|                          |                           |         |       |                          |        |          | lishment  | of Best                               | Practices |     | for Evidence   | for Prediction |           |
|                          |                           |         |       |                          |        |          | AReview.  | JAMApsychiatry,77(5):534–540,May2020. |           |     |                |                |           |
| Nakanishi,               | M.,                       | Xu, M., | Wang, | Y., Chiang,              | K.-J., | Han, J., |           |                                       |           |     |                |                |           |
ISSN2168-622X.
| and Jung, | T.-P. | Questionable |     | Classification |     | Accuracy |     |     |     |     |     |     |     |
| --------- | ----- | ------------ | --- | -------------- | --- | -------- | --- | --- | --- | --- | --- | --- | --- |
Reportedin“DesigningaSumofSquaredCorrelations
Poulin,P.,Jörgens,D.,Jodoin,P.-M.,andDescoteaux,M.
| FrameworkforEnhancingSSVEP-BasedBCIs”. |     |     |     |     |     | IEEE |              |     |             |     |           |         |           |
| -------------------------------------- | --- | --- | --- | --- | --- | ---- | ------------ | --- | ----------- | --- | --------- | ------- | --------- |
|                                        |     |     |     |     |     |      | Tractography |     | and machine |     | learning: | Current | state and |
TransactionsonNeuralSystemsandRehabilitationEngi-
|                                    |     |     |     |     |                |     | openchallenges.  |     | MagneticResonanceImaging,64:37– |                |     |     |     |
| ---------------------------------- | --- | --- | --- | --- | -------------- | --- | ---------------- | --- | ------------------------------- | -------------- | --- | --- | --- |
| neering,28(4):1042–1043,April2020. |     |     |     |     | ISSN1558-0210. |     |                  |     |                                 |                |     |     |     |
|                                    |     |     |     |     |                |     | 48,December2019. |     |                                 | ISSN0730-725X. |     |     |     |
ConferenceName:IEEETransactionsonNeuralSystems
andRehabilitationEngineering.
Raji,D.,Denton,E.,Bender,E.M.,Hanna,A.,andPaullada,
|         |             |     |              |     |               |     | A. AI | and the | Everything |     | in the Whole | Wide | World |
| ------- | ----------- | --- | ------------ | --- | ------------- | --- | ----- | ------- | ---------- | --- | ------------ | ---- | ----- |
| Nalepa, | J., Myller, | M., | and Kawulok, |     | M. Validating | Hy- |       |         |            |     |              |      |       |
perspectralImageSegmentation. IEEEGeoscienceand Benchmark. ProceedingsoftheNeuralInformationPro-
cessingSystemsTrackonDatasetsandBenchmarks,1,
RemoteSensingLetters,16(8):1264–1268,August2019.
December2021.
| ISSN1558-0571. |     | ConferenceName: |     |     | IEEEGeoscience |     |     |     |     |     |     |     |     |
| -------------- | --- | --------------- | --- | --- | -------------- | --- | --- | --- | --- | --- | --- | --- | --- |
andRemoteSensingLetters.
|          |           |     |           |                    |     |     | Recht,B.,Roelofs,R.,Schmidt,L.,andShankar,V. |     |     |     |     |            | DoIm- |
| -------- | --------- | --- | --------- | ------------------ | --- | --- | -------------------------------------------- | --- | --- | --- | --- | ---------- | ----- |
|          |           |     |           |                    |     |     | ageNetClassifiersGeneralizetoImageNet?       |     |     |     |     | InProceed- |       |
| National | Academies | of  | Sciences, | E. Reproducibility |     | and |                                              |     |     |     |     |            |       |
ReplicabilityinScience. May2019. ISBN978-0-309- ings of the 36th International Conference on Machine
Learning,pp.5389–5400.PMLR,May2019.
48616-3.
Neunhoeffer,M.andSternberg,S. HowCross-Validation Roberts, D. R., Bahn, V., Ciuti, S., Boyce, M. S.,
|     |     |     |     |     | PoliticalAnal- |     | Elith, | J., Guillera-Arroita, |     |     | G., Hauenstein, | S., | Lahoz- |
| --- | --- | --- | --- | --- | -------------- | --- | ------ | --------------------- | --- | --- | --------------- | --- | ------ |
CanGoWrongandWhattoDoAboutIt.
|                      |     |     |         |       |      |            | Monfort, | J.  | J., Schröder, |     | B., Thuiller, | W., | Warton, |
| -------------------- | --- | --- | ------- | ----- | ---- | ---------- | -------- | --- | ------------- | --- | ------------- | --- | ------- |
| ysis, 27(1):101–106, |     |     | January | 2019. | ISSN | 1047-1987, |          |     |               |     |               |     |         |
1476-4989. Publisher: CambridgeUniversityPress. D. I., Wintle, B. A., Hartig, F., and Dormann, C. F.
|     |     |     |     |     |     |     | Cross-validation |     | strategies |     | for data | with | temporal, |
| --- | --- | --- | --- | --- | --- | --- | ---------------- | --- | ---------- | --- | -------- | ---- | --------- |
Nisbet,R.,Elder,J.,andMiner,G. HandbookofStatistical spatial,hierarchical,orphylogeneticstructure. Ecogra-
AnalysisandDataMiningApplications. Elsevier,2009. phy, 40(8):913–929, 2017. ISSN 1600-0587. _eprint:
ISBN978-0-12-374765-5. https://onlinelibrary.wiley.com/doi/pdf/10.1111/ecog.02881.

LeakageandtheReproducibilityCrisisinML-basedScience KapoorandNarayanan
Roberts, M., Driggs, D., Thorpe, M., Gilbey, J., Ye- Wang,J.,Wang,F.,Weissman,S.,Whitaker,K.,Wolters,
ung, M., Ursprung, S., Aviles-Rivero, A. I., Etmann, M.K.,Woon,W.L.,Wu,J.,Wu,C.,Yang,K.,Yin,J.,
C., McCague, C., Beer, L., Weir-McCall, J. R., Teng, Zhao, B., Zhu, C., Brooks-Gunn, J., Engelhardt, B.E.,
Z., Gkrania-Klotsas, E., Rudd, J. H. F., Sala, E., and Hardt,M.,Knox,D.,Levy,K.,Narayanan,A.,Stewart,
Schönlieb, C.-B. Common pitfalls and recommenda- B.M.,Watts,D.J.,andMcLanahan,S. Measuringthe
tions for using machine learning to detect and prog- predictabilityoflifeoutcomeswithascientificmasscol-
nosticate for COVID-19 using chest radiographs and laboration. ProceedingsoftheNationalAcademyofSci-
CTscans. NatureMachineIntelligence,3(3):199–217, ences,117(15):8398–8403,April2020. ISSN0027-8424,
March 2021. ISSN 2522-5839. Bandiera_abtest: a 1091-6490. Publisher: National Academy of Sciences
Cc_license_type: cc_byCg_type: NatureResearchJour- Section: SocialSciences.
| nalsNumber:                      | 3Primary_atype: | ResearchPublisher: |                   | Na- |             |             |             |     |     |                     |     |
| -------------------------------- | --------------- | ------------------ | ----------------- | --- | ----------- | ----------- | ----------- | --- | --- | ------------------- | --- |
|                                  |                 |                    |                   |     | Schafer, J. | L. Multiple | imputation: |     | a   | primer. Statistical |     |
| turePublishingGroupSubject_term: |                 |                    | Computationalsci- |     |             |             |             |     |     |                     |     |
MethodsinMedicalResearch,8(1):3–15,February1999.
ence;Diagnosticmarkers;Prognosticmarkers;SARS-CoV-
|                    |                                   |     |     |     | ISSN 0962-2802. |     | Publisher: |     | SAGE | Publications | Ltd |
| ------------------ | --------------------------------- | --- | --- | --- | --------------- | --- | ---------- | --- | ---- | ------------ | --- |
| 2 Subject_term_id: | computational-science;diagnostic- |     |     |     |                 |     |            |     |      |              |     |
STM.
markers;prognostic-markers;sars-cov-2.
|                |                     |               |       |          | Scheuerman,M.K.,Hanna,A.,andDenton,E. |     |              |                       |        | DoDatasets  |     |
| -------------- | ------------------- | ------------- | ----- | -------- | ------------------------------------- | --- | ------------ | --------------------- | ------ | ----------- | --- |
| Robin, X.,     | Turck, N., Hainard, | A., Tiberti,  | N.,   | Lisacek, |                                       |     |              |                       |        |             |     |
|                |                     |               |       |          | Have Politics?                        |     | Disciplinary |                       | Values | in Computer | Vi- |
| F., Sanchez,   | J.-C., and          | Müller, M.    | pROC: | an open- |                                       |     |              |                       |        |             |     |
|                |                     |               |       |          | sionDatasetDevelopment.               |     |              | ProceedingsoftheACMon |        |             |     |
| source package | for R and           | S+ to analyze | and   | compare  |                                       |     |              |                       |        |             |     |
Human-ComputerInteraction,5(CSCW2):317:1–317:37,
ROCcurves.BMCBioinformatics,12(1):77,March2011.
October2021.
ISSN1471-2105.
|                       |                  |                             |              |           | Schrider,D.R.andKern,A.D.         |     |     | SupervisedMachineLearn- |     |                |     |
| --------------------- | ---------------- | --------------------------- | ------------ | --------- | --------------------------------- | --- | --- | ----------------------- | --- | -------------- | --- |
| Rocca,R.andYarkoni,T. |                  | PuttingPsychologytotheTest: |              |           |                                   |     |     |                         |     |                |     |
|                       |                  |                             |              |           | ingforPopulationGenetics:         |     |     | ANewParadigm.           |     | Trendsin       |     |
| Rethinking            | Model Evaluation | Through                     | Benchmarking |           |                                   |     |     |                         |     |                |     |
|                       |                  |                             |              |           | Genetics,34(4):301–312,April2018. |     |     |                         |     | ISSN0168-9525. |     |
| and Prediction.       | Advances         | in Methods                  | and          | Practices |                                   |     |     |                         |     |                |     |
inPsychologicalScience,4(3):251524592110268,July Schutte,S. RegionsatRisk: PredictingConflictZonesin
2021. ISSN2515-2459,2515-2467. AfricanInsurgencies*. PoliticalScienceResearchand
|     |     |     |     |     | Methods, | 5(3):447–465, |     | July | 2017. | ISSN 2049-8470, |     |
| --- | --- | --- | --- | --- | -------- | ------------- | --- | ---- | ----- | --------------- | --- |
Russakovsky,O.,Deng,J.,Su,H.,Krause,J.,Satheesh,S.,
|     |     |     |     |     | 2049-8489. | Publisher: | CambridgeUniversityPress. |     |     |     |     |
| --- | --- | --- | --- | --- | ---------- | ---------- | ------------------------- | --- | --- | --- | --- |
Ma,S.,Huang,Z.,Karpathy,A.,Khosla,A.,Bernstein,
M.,Berg,A.C.,andFei-Fei,L. ImageNetLargeScale Serra-Garcia,M.andGneezy,U.Nonreplicablepublications
Visual Recognition Challenge. International Journal arecitedmorethanreplicableones. ScienceAdvances,7
of Computer Vision, 115(3):211–252, December 2015. (21):eabd1705,May2021. ISSN2375-2548. Publisher:
| ISSN1573-1405. |     |     |     |     | AmericanAssociationfortheAdvancementofScience |                  |     |     |     |     |     |
| -------------- | --- | --- | --- | --- | --------------------------------------------- | ---------------- | --- | --- | --- | --- | --- |
|                |     |     |     |     | Section:                                      | ResearchArticle. |     |     |     |     |     |
Salganik,M.J.,Lundberg,I.,Kindel,A.T.,Ahearn,C.E.,
Al-Ghoneim,K.,Almaatouq,A.,Altschul,D.M.,Brand, Shi,L.andLin,L. Thetrim-and-fillmethodforpublication
J.E.,Carnegie,N.B.,Compton,R.J.,Datta,D.,David- bias: practical guidelines and recommendations based
son, T., Filippova, A., Gilroy, C., Goode, B.J., Jahani, onalargedatabaseofmeta-analyses. Medicine,98(23):
E.,Kashyap,R.,Kirchner,A.,McKay,S.,Morgan,A.C., e15987,June2019. ISSN0025-7974.
| Pentland, | A., Polimis, | K., Raes, L., | Rigobon, | D. E., |           |      |            |        |       |          |      |
| --------- | ------------ | ------------- | -------- | ------ | --------- | ---- | ---------- | ------ | ----- | -------- | ---- |
|           |              |               |          |        | Shim, M., | Lee, | S.-H., and | Hwang, | H.-J. | Inflated | pre- |
Roberts,C.V.,Stanescu,D.M.,Suhara,Y.,Usmani,A.,
dictionaccuracyofneuropsychiatricbiomarkerscaused
Wang,E.H.,Adem,M.,Alhajri,A.,AlShebli,B.,Amin,
|     |     |     |     |     | by data | leakage | in feature | selection. |     | Scientific | Re- |
| --- | --- | --- | --- | --- | ------- | ------- | ---------- | ---------- | --- | ---------- | --- |
R.,Amos,R.B.,Argyle,L.P.,Baer-Bositis,L.,Büchi,
|     |     |     |     |     | ports, 11(1):7980, |     | April | 2021. |     | ISSN 2045-2322. |     |
| --- | --- | --- | --- | --- | ------------------ | --- | ----- | ----- | --- | --------------- | --- |
M.,Chung,B.-R.,Eggert,W.,Faletto,G.,Fan,Z.,Freese,
|     |     |     |     |     | Bandiera_abtest: |     | a Cc_license_type: |     |     | cc_by Cg_type: |     |
| --- | --- | --- | --- | --- | ---------------- | --- | ------------------ | --- | --- | -------------- | --- |
J.,Gadgil,T.,Gagné,J.,Gao,Y.,Halpern-Manners,A.,
|     |     |     |     |     | Nature | Research | Journals | Number: |     | 1 Primary_atype: |     |
| --- | --- | --- | --- | --- | ------ | -------- | -------- | ------- | --- | ---------------- | --- |
Hashim,S.P.,Hausen,S.,He,G.,Higuera,K.,Hogan,B.,
|     |     |     |     |     | Research | Publisher: | Nature |     | Publishing | Group | Sub- |
| --- | --- | --- | --- | --- | -------- | ---------- | ------ | --- | ---------- | ----- | ---- |
Horwitz,I.M.,Hummel,L.M.,Jain,N.,Jin,K.,Jurgens,
|     |     |     |     |     | ject_term: | Biomarkers;Diagnostic |     |     |     | markers;Predictive |     |
| --- | --- | --- | --- | --- | ---------- | --------------------- | --- | --- | --- | ------------------ | --- |
D.,Kaminski,P.,Karapetyan,A.,Kim,E.H.,Leizman,
|     |     |     |     |     | markers;Prognostic |     | markers;Psychiatric |     |     | disorders | Sub- |
| --- | --- | --- | --- | --- | ------------------ | --- | ------------------- | --- | --- | --------- | ---- |
B.,Liu,N.,Möser,M.,Mack,A.E.,Mahajan,M.,Man-
|     |     |     |     |     | ject_term_id: | biomarkers;diagnostic-markers;predictive- |     |     |     |     |     |
| --- | --- | --- | --- | --- | ------------- | ----------------------------------------- | --- | --- | --- | --- | --- |
dell,N.,Marahrens,H.,Mercado-Garcia,D.,Mocz,V.,
markers;prognostic-markers;psychiatric-disorders.
| Mueller-Gastell, | K., Musse, | A., Niu, | Q., Nowak, | W., |     |     |     |     |     |     |     |
| ---------------- | ---------- | -------- | ---------- | --- | --- | --- | --- | --- | --- | --- | --- |
Omidvar,H.,Or,A.,Ouyang,K.,Pinto,K.M.,Porter,E., Szegedy,C.,Zaremba,W.,Sutskever,I.,Bruna,J.,Erhan,
Porter,K.E.,Qian,C.,Rauf,T.,Sargsyan,A.,Schaffner, D.,Goodfellow,I.,andFergus,R. Intriguingproperties
T.,Schnabel,L.,Schonfeld,B.,Sender,B.,Tang,J.D., of neural networks. Proceedings of the International
Tsurkov,E.,Loon,A.v.,Varol,O.,Wang,X.,Wang,Z., ConferenceonLearningRepresentations,2014.

LeakageandtheReproducibilityCrisisinML-basedScience KapoorandNarayanan
Szeliski,R. Computervision: algorithmsandapplications,
2nded. https://szeliski.org/Book,2021.
Tonidandel, S., King, E.B., andCortina, J.M. BigData
Methods: LeveragingModernDataAnalyticTechniques
to Build Organizational Science. Organizational Re-
searchMethods,21(3):525–547,July2018. ISSN1094-
4281. Publisher: SAGEPublicationsInc.
Tu, F., Zhu, J., Zheng, Q., and Zhou, M. Be careful of
when: anempiricalstudyontime-relatedmisuseofissue
trackingdata. InProceedingsofthe201826thACMJoint
MeetingonEuropeanSoftwareEngineeringConference
andSymposiumontheFoundationsofSoftwareEngineer-
ing,pp.307–318,LakeBuenaVistaFLUSA,October
2018.ACM. ISBN978-1-4503-5573-5.
Valavi,R.,Elith,J.,Lahoz-Monfort,J.,andGuillera-Arroita,
G. Blockcross-validationforspeciesdistributionmod-
elling,2021.
Valletta, J. J., Torney, C., Kings, M., Thornton, A., and
Madden, J. Applications of machine learning in ani-
malbehaviourstudies. AnimalBehaviour,124:203–220,
February2017. ISSN0003-3472.
Vandewiele, G., Dehaene, I., Kovács, G., Sterckx, L.,
Janssens, O., Ongenae, F., De Backere, F., De Turck,
F.,Roelens,K.,Decruyenaere,J.,VanHoecke,S.,and
Demeester,T. Overlyoptimisticpredictionresultsonim-
balanceddata:acasestudyofflawsandbenefitswhenap-
plyingover-sampling. ArtificialIntelligenceinMedicine,
111:101987,January2021. ISSN0933-3657.
Wang,Y. ComparingRandomForestwithLogisticRegres-
sion for Predicting Class-Imbalanced Civil War Onset
Data: A Comment. Political Analysis, 27(1):107–110,
January2019. ISSN1047-1987,1476-4989. Publisher:
CambridgeUniversityPress.
Whelan,R.andGaravan,H.WhenOptimismHurts:Inflated
PredictionsinPsychiatricNeuroimaging. BiologicalPsy-
chiatry,75(9):746–748,May2014. ISSN0006-3223.
Yarkoni,T.andWestfall,J.ChoosingPredictionOverExpla-
nationinPsychology: LessonsFromMachineLearning.
PerspectivesonPsychologicalScience,12(6):1100–1122,
November 2017. ISSN 1745-6916. Publisher: SAGE
PublicationsInc.
Zech, J. R., Badgeley, M. A., Liu, M., Costa, A. B., Ti-
tano,J.J.,andOermann,E.K. Variablegeneralization
performanceofadeeplearningmodeltodetectpneumo-
niainchestradiographs: Across-sectionalstudy. PLOS
Medicine,15(11):e1002683,November2018.ISSN1549-
1676. Publisher: PublicLibraryofScience.

LeakageandtheReproducibilityCrisisinML-basedScience KapoorandNarayanan
Appendix
OverviewoftheAppendix. InAppendixA,wejustifyourchoiceofthewordreproducibility. InAppendixB,weprovide
adetaileddescriptionofthemethodsweusedtoselectpapersforourreviewofcivilwarpredictionandfixreproducibility
issuesinthepaperswitherrors. InAppendixC,weshowthateachtypeofleakageidentifiedinoursurvey(Section2.4)is
addressedbymodelinfosheets. Weprovideatemplateofmodelinfosheetsandalistofall124papersthatweconsidered
forourliteraturereviewincivilwarpredictiononourwebsite(https://reproducible.cs.princeton.edu).
A.Whydowecallthesereproducibilityissues?
Weacknowledgethatthereisn’tconsensusaboutthetermreproducibility,andtherehavebeenanumberofrecentattempts
todefinethetermandcreateconsensus(NationalAcademiesofSciences,2019). Onepossibledefinitioniscomputational
reproducibility—whentheresultsinapapercanbereplicatedusingtheexactcodeanddatasetprovidedbytheauthors(Liu
&Salganik,2019). Wearguethatthisdefinitionistoonarrowbecauseevencasesofoutrightbugsinthecodewouldnotbe
consideredirreproducibleunderthisdefinition. Thereforeweadvocateforastandardwherebugsandothererrorsindata
analysisthatchangeorchallengeapaper’sfindingsconstituteirreproducibility.
Thegoalofpredictivemodelingistoestimate(andimprove)theaccuracyofpredictionsthatonemightmakeinareal-world
scenario. Thisistrueregardlessofthespecificresearchquestiononewishestostudybybuildingapredictivemodel. In
practiceonesetsupthedataanalysistomimicthisreal-worldscenarioascloselyaspossible. Therearelimitstohowwell
wecandothisandconsequentlythereisalwaysmethodologicaldebateonsomeissues,buttherearealsosomeclearrules.
Ifananalysischoicecanbeshowntoleadtoincorrectestimatesofpredictiveaccuracy,thereisusuallyconsensusintheML
communitythatitisanerror. Forexample,violatingthetrain-testsplit(orthelearn-predictseparation)isanerrorbecause
thetestsetisintendedtoprovideanaccurateestimateof’out-of-sample’performance—modelperformanceonadataset
thatwasnotusedfortraining(Kuhn&Johnson,2013). Thus,todefinewhatisanerror,welooktothisconsensusintheML
community(e.g. intextbooks)andofferourownargumentswhennecessary.
B.MaterialsandMethods: Reproducibilityissuesincivilwarprediction
Differentresearchersmighthavedifferentaimswhencomparingtheperformanceoncivilwarprediction—determiningthe
absoluteperformance,orcomparingtherelativeperformanceofdifferentmodelsofcivilwarprediction. Whethertheaimis
todeterminetherelativeorabsoluteperformanceofmodelsofcivilwarprediction,dataleakagecausesadeeperissueinthe
findingsofeachofthe4paperswitherrorsthatleadstoinaccurateestimatesofbothrelativeandabsoluteout-of-sample
performance.
Incorrectingthepaperswitherrors(Muchlinskietal.,2016;Colaresi&Mahmood,2017;Wang,2019;Kaufmanetal.,
2019),ouraimistoreportout-of-sampleperformanceofthevariousmodelsofcivilwarpredictionaftercorrectingthedata
leakage,whilekeepingallotherfactorsasclosetotheoriginalimplementationaspossible. Fixingtheerrorsallowsamore
accurateestimateofout-of-sampleperformance.
At the same time, we caution that just because our corrected results offer a more accurate estimate of out-of-sample
performancedoesn’tmeanthatweendorseallothermethodologicalchoicesmadeinthepapers. Forexample,tocorrectthe
resultsreportedbyMuchlinskietal.(2016),weuseimputationonanout-of-sampledatasetthathas95%missingvalues.
Whileanimputationmodelcreatedonlyusingthetrainingdataavoidsdataleakage,itdoesnotmeanthatusingadataset
with95%missingvaluestomeasureout-of-sampleperformanceisdesirable.
B.1.Paperselectionforreview
Tofindrelevantpapersoncivilwarpredictionforourreview,weusedthesearchresultsfromadatasetofacademicliterature
(Hooketal.,2018)forpaperswiththeterms‘civil’AND‘war’AND(‘prediction’OR‘predicting’OR‘forecast’)intheir
titleorabstract,aswellaspapersthatwerecitedinarecentreviewofthefield(Bara,2020). Tokeepthenumberofpapers
tractable,welimitedourselvestothosethatwerepublishedinthelast5years,specifically,paperspublishedbetween1st
January2016and14thMay2021. Thisyielded124papers. Wenarrowedthislisttothe15papersthatwerefocusedon
predictingcivilwarandevaluatedperformanceusingatrain-testsplit. Ofthe15papersthatmeetourinclusioncriteria,12
sharethecompletecodeanddata. Forthese12,weattemptedtoidentifyerrorsandreproducibilityissuesfromthetextand
throughreviewingthecodeprovidedwiththepapers. Whenweidentifiederrors,were-analyzedthedatawiththeerrors

LeakageandtheReproducibilityCrisisinML-basedScience KapoorandNarayanan
corrected. Wenowaddressthereproducibilityissueswefoundineachpaperindetail.
B.2.Muchlinskietal.(2016)
Imputationiscommonlyusedtofillinmissingvaluesindatasets(Dondersetal.,2006). Imputingthetrainingandtest
datasetstogetherreferstousingdatafromthetrainingaswellasthetestdatasetstocreateanimputationmodelthatfillsin
allmissingvaluesinthedataset. Thisisanerroneousimputationmethodforthepredictivemodelingparadigm,sinceit
canleadtodataleakage,whichresultsinincorrect,over-optimisticperformanceclaims. Thispitfalliswellknowninthe
predictivemodelingcommunity—discussedinMLtextbooks(Kuhn&Johnson,2013),blogs(Ghanietal.,2020)and
popularonlineforums(noa).
Muchlinskietal.(2016)claimthataRandomForestsmodelvastlyoutperformsLogisticRegressionmodelsintermsof
out-of-sampleperformanceusingtheAUCmetric(Fawcett,2006). However,sincetheyimputethetrainingandtestdatasets
together,theirresultssufferfromdataleakage. Theimpactofleakageisespeciallyseverebecauseofthelevelofmissingness
intheirout-of-sampletestdataset: over95%ofthevaluesaremissing(whichisnotreportedinthepaper),and70ofthe90
variablesusedintheirmodelaremissingforallinstancesintheout-of-sampletestset.4 Whentheirimputationmethodis
corrected,theirRandomForestsmodelperformsnobetterthantheLogisticRegressionmodelsthattheycomparedagainst.
Wefocusonreproducingtheout-of-sampleresultsreportedbyMuchlinskietal.(2016). TableA1providesthecomparisons
betweentheresultsreportedinMuchlinskietal.(2016),ourreproductionsoftheirreported(incorrect)results,aswellas
thecorrectedversionoftheirresults. Muchlinskietal.(2016)receivedtwocritiquesofthemethodsusedintheirpaper
(Wang,2019;Neunhoeffer&Sternberg,2019). 5. Inresponse,theypublishedareplywithclarificationsandrevisedcode
addressingbothcritiques(Muchlinskietal.,2019). Weusetherevisedversionoftheircode. Wefindthattheerrorintheir
imputationmethodsexistsintherevisedcodeaswellastheoriginalcode,andwasnotidentifiedbythepreviouscritiques.
Muchlinskietal.(2016)re-usethedatasetfromHegre&Sambanis(2006)whentrainingtheirmodels,andprovideaseparate
out-of-sampletestsetforevaluation. Toaddressmissingvalues,theyuseaRandomForestsbasedimputationmethodin
RcalledrfImpute. However,thetrainingandtestsetsareimputedtogether,whichleadstoadataleakage. Thisresultsin
overoptimisticperformanceclaims. Below,wedetailthestepswetaketocorrecttheirresults,provideavisualizationofthe
dataleakage,andprovideasimulationshowcasinghowthedataleakagecanresultinoveroptimisticclaimsofperformance.
Correctingthedataimputation. Tocorrectthiserror,weusethemicepackageinRwhichusesmultipleimputationfor
imputingmissingdata. Thisisbecausethemicepackageallowsustospecifywhichrowsinthedatasetareapartofthe
testsetanditdoesnotusethoserowsforcreatingtheimputationmodel,whereasrfImpute—theoriginalmethodusedto
imputethemissingdataintheoriginalresultsbyMuchlinskietal.(2016)—doesnothavethisfeature. Theauthorsimputed
thetrainingsettogetherwiththeout-of-sampletestsetusingrfImpute,whichledtodataleakage. TableA1providesthe
comparisonsbetweentheresultsreportedinMuchlinskietal.(2016),ourreproductionsoftheirreported(incorrect)results,
aswellasthecorrectedversionoftheirresults.
Usingmultipleimputationfillsinmissingvalueswithoutregardingtheunderlyingvariable’soriginaldistribution. For
example,usingmultipleimputationfillsindifferentmissingvaluesforthevariablerepresentingthepercentageofrough
terraininacountryindifferentyears(Beger,2021),whereasthisparticularvariable(percentageofroughterrain)isconstant
overtime. However,whenmultipleimputationisusedwithatrain-testsplit,thereisstillnoleakagebetweenthetraining
andtestsets,sincetheimputationmodelonlyusesdatafromthetrainingsettofillinmissingvaluesinthetestset.
Whycan’tweuserfImputeinthecorrectedresults? Insteadofusingthemicepackage,anotherwaytoimputethedata
correctly,i.e.,withoutdataleakage,wouldbetoruntheimputationusingrfImputeonthetrainingandtestdataseparately
—creatingtwoseparateimputationmodels—oneforthetrainingdataandoneforthetestdata. Wecouldnotusethis
imputationmethodbecause70ofthe90variablesusedinMuchlinskietal.(2016)’smodelasfeaturesdonothaveany
valuesintheout-of-sampletestdataprovided—i.e. theyaremissingforallobservationsintheout-of-sampledataset—
andrfImputerequiresatleastsomevaluesforeachvariabletonotbemissing. Inotherwords,themicepackageallowsusto
trainanimputationmodelonthetrainingsetanduseittofillinmissingvaluesinthetestset.
4Whileleakageisparticularlyseriousinpredictivemodeling,adatasetwith95%ofvaluesmissingisproblematicevenforexplanatory
modeling.
5Hofmanetal.(2021a)alsooutlinetheshortcomingsintheinitialcodereleasedbyMuchlinskietal.(2016).

LeakageandtheReproducibilityCrisisinML-basedScience KapoorandNarayanan
Subtledifferencesbetweenexplanatoryandpredictivemodeling. Intheexplanatorymodelingparadigm,theaimisto
drawinferencesfromdata,asopposedtooptimizingandevaluatingout-of-samplepredictiveperformance. Inthiscase,
dataimputation wouldbeconsidereda partofthe datapre-processingstep, eventhoughitis stillimportanttokeepin
mindthevariousassumptionsbeingmadeinthisprocessSchafer(1999). Contrarily,inthepredictivemodelingparadigm,
the imputation is a part of the modeling step (Kuhn & Johnson, 2013) because the aim of the modeling exercise is to
validateperformanceonanout-of-sampletestset,whichthemodeldoesnothaveaccesstoduringthetraining. Inthiscase,
imputingthetrainingandtestdatasetstogetherleadstoleakinginformationfromthetestsettothetrainingsetandthusthe
performanceevaluationonthepurportedly“out-of-sample”testsetwouldbeanover-estimate.
What is the precise mechanism by which the leakage occurs in Muchlinski et al. (2016)? When Muchlinski et al.
(2016)imputethemissingvaluesintheout-of-sampletestset,theimputationmodelhasaccesstotheentiretrainingdata
aswellasthelabelsofthetargetvariablesinthetestdata—theyalsoincludethetargetvariableinthelistofvariables
whichtheimputationmodeltreatsasindependentvariableswhencarryingouttheimputation. Themodelthereforeuses
correlationsbetweenthetargetvariableandindependentvariablesinthetrainingdatasetandusesthemtofillinthemissing
values in the test dataset — i.e. the model uses the labels of the target variables in the test data and correlations from
thetrainingdatatofillinmissingvalues. Thisleadstothetestdatasethavingsimilarcorrelationsbetweenthetargetand
independentvariablesastheonespresentinthetrainingdata. Further,themissingdataisfilledininsuchawaythatitfavors
MLmodelssuchasRandomForestsoverLogisticRegressionmodels,asweshowinthevisualizationbelow.
Visualizingtheleakage. WecanvisuallyobserveaninstanceofdataleakageinFigureA1. Wefocusonthedistribution
ofthefeatureagexp,whichrepresentstheproportionofagriculturalexportsintheGDPofacountry. Wechoosethisfeature
becauseintheMuchlinskietal. paper,thisfeaturehadthehighestginiindexfortherandomforestsmodel—whichmeans
thatitwasanimportantfeatureforthemodel. Whileweonlyvisualizeonefeaturehere,similarresultsholdacrossmultiple
featuresusedinthemodel. Below,wereconstructtheprocessbywhichthedataleakagewasgenerated—followingthe
exactstepsMuchlinskietal.(2016)usedtocreateandevaluatethedataset:
• FigureA1arepresentsthedistributionoftheagexpvariableforwarandpeacedatapointsintheoriginaldatasetby
Hegre&Sambanis(2006),ignoringmissingvalues.
• FigureA1bshowsthesamedistributionafterincludingtheimputedvaluesofagexp. Inparticular,weseetwopeaksin
thedatasetforwarandpeacedatapointsalike,oneduetowarinstancesandoneduetopeaceinstances.
• IfwelookonlyatthedatapointsthatwereimputedusingtherfImputemethod(FigureA1c),weseethatthedistribution
oftheimputeddatapointsforwarandpeacearecompletelyseparated,incontrasttotheoriginaldistributionwhere
therewasasignificantoverlapbetweenthedistributions.
• Finally,FigureA1dshowstheeffectofimputingthisalready-imputeddatasetwiththeout-of-sampletestset—we
seethattheout-of-sampledatasetonlyhasthepeakforpeacedatapoints,whereasthedistributionforwarisalmost
uniform.
Further,therandomforestsmodelcanlearnthepeakfortheagexpvariableinthepeaceinstancesfromthetrainingdataset
afterimputation,sincethepeakforthetrainingandtestsetsissimilar. Itcandistinguishbetweenwarandpeacedatapoints
muchmoreeasilycomparedtoalogisticregressionmodelthatonlyusesoneparameterperfeature—logisticregression
modelsaremonotonicfunctionsoftheindependentvariablesandthereforecannotlearnthatavariableonlylieswithina
smallrangeforagivenlabel. ThishighlightsthereasonbehindRandomForestsoutperformingLogisticRegressioninthis
setting—imputingthetrainingandtestdatasetstogetherleadstovariablevaluesbeingartificallyconcentratedwithinavery
smallrangeforboththetrainingandtestdatasets—andfurther,beingneatlyseparatedacrosswarandpeaceinstances. The
impactoftheimputationbecomesevenclearerwhenweconsiderthattheout-of-sampletestdatasetprovidedbyMuchlinski
etal.(2016)hasover95%ofthedatamissing,and70outof90variablesaremissingforallinstancesintheout-of-sample
dataset.
Asimulationshowcasingtheimpactofmissingnessonperformanceestimatesinthepresenceofleakage. Wecan
observeavisualexampleofhowdataleakageaffectsperformanceevaluationinFigureA2. Wedescribethesimulation
below:

LeakageandtheReproducibilityCrisisinML-basedScience KapoorandNarayanan
0.100
0.20
0.075
0.15
|               |     |     | warstds |         |     | warstds |
| ------------- | --- | --- | ------- | ------- | --- | ------- |
| ytisned 0.050 |     |     |         | ytisned |     |         |
|               |     |     | peace   |         |     | peace   |
|               |     |     | war     | 0.10    |     | war     |
0.025
0.05
| 0.000 |       |       |     | 0.00 |       |     |
| ----- | ----- | ----- | --- | ---- | ----- | --- |
| 0     | 25    | 50 75 |     | 0 25 | 50 75 |     |
|       | agexp |       |     |      | agexp |     |
(a)Distributionoftheagexpvariableforpeaceandwar (b)Distributionoftheagexpvariableforpeaceandwar
datapointsfortheoriginalHegreetal.dataset,ignoring datapointsfortheimputedHegreetal.datasetusedby
| missingvalues |     |     |     | Muchlinskietal.fortraining |     |     |
| ------------- | --- | --- | --- | -------------------------- | --- | --- |
12
6
8
| ytisned |     |     | warstds.y |     |     |     |
| ------- | --- | --- | --------- | --- | --- | --- |
peace
war
4
|     |     |     |     | ytisned |     | warstds.y |
| --- | --- | --- | --- | ------- | --- | --------- |
peace
war
4
2
0
| 8   | 10 agexp.y | 12 14 |     |     |     |     |
| --- | ---------- | ----- | --- | --- | --- | --- |
0
| (c) Distribution | of the agexp | variable for peace | and |     |               |     |
| ---------------- | ------------ | ------------------ | --- | --- | ------------- | --- |
|                  |              |                    |     | 9   | agexp.y 11 13 | 15  |
wardatapointsonlyforthedatapointsthatwereadded
duringimputation(i.e.thedatapointsthatweremissing (d)Distributionoftheagexpvariableforpeaceandwar
| intheoriginaldataset) |     |     |     | datapointsfortheout-of-sampletestset |     |     |
| --------------------- | --- | --- | --- | ------------------------------------ | --- | --- |
FigureA1.DistributionoftheagexpvariableforpeaceandwardatapointsfordifferentimputationstepsinMuchlinskietal.(2016).Note
thatthedistributionofpeaceinstancesinthetestset(D)hasapeakthatisclosetothedistributionintheimputedtrainingset(B,C)—
whichallowstherandomforestsmodeltolearnthesmallrangeofvalueswherepeacedatapointsareconcentrated. Whilewereport
resultsfortheagexpvariable,similartrendsappearacrossindependentvariablesinthedataset.

LeakageandtheReproducibilityCrisisinML-basedScience KapoorandNarayanan
• therearetwovariables—thetargetvariableonsetandtheindependentvariablegdp.
• onsetisabinaryvariable. gdpisdrawnfromanormaldistributionanddependsononsetasfollows:
gdp=N(0,1)+onset.
• Wegenerate1000sampleswithonset=0and1000sampleswithonset=1tocreatethedataset.
• Werandomlysplitthedataintotraining(50%)andtest(50%)sets,andcreatearandomforestsmodelthatistrainedon
thetrainingsetandevaluatedonthetestset.
• Toobservetheimpactofimputingthetrainingandtestsetstogether,werandomlydeleteacertainpercentageofvalues
ofgdp,andimputeitusingtheimputationmethodusedinMuchlinskietal.(2016).
• Wevarytheproportionofmissingvaluesfrom0%to95%inincrementsof5%andplottheaccuracyoftherandom
forestsclassifieronthetestset.
• Weruntheentireprocess100timesandreportthemeanand95%CIoftheaccuracyinFigureA2;the95%CIistoo
smalltobeseenintheFigure.
Wefindthatimputingthetrainingandtestsetstogetherleadstoanincreasingimprovementinthepurportedly“out-of-sample”
accuracyofthemodel. Estimatesofmodelperformanceinthiscaseareartificiallyhigh. Thisexamplealsohighlightsthe
impactofthehighpercentageofmissingvalues—sincetheout-of-sampletestsetusedbyMuchlinskietal.(2016)contains
over95%missingvalues,theimpactofimputingthetrainingandtestsetstogetherisveryhigh.
FigureA2.Resultsofasimulationthatshowcasehowimputingthetrainingandtestsetstogetherleadstooveroptimisticestimatesof
modelperformance.The95%ConfidenceIntervalsaretoosmalltobeseen.
B.3.Colaresi&Mahmood(2017)
Colaresi&Mahmood(2017)reportthatMLmodelsvastlyoutperformLogisticRegressionforpredictingcivilwaronset.
However,theyre-usetheimputedversionofthedatasetinHegre&Sambanis(2006)whichisprovidedbyMuchlinskietal.
(2016). Theyusetheimputeddatasetbothfortrainingandtestingviaatrain-testsplit;theydonotusetheout-of-sampletest
setprovidedbyMuchlinskietal. ThismeansthattheresultsinColaresi&Mahmood(2017)aresubjecttoexactlythesame

LeakageandtheReproducibilityCrisisinML-basedScience KapoorandNarayanan
|                  | Algorithm          | Reported Reportedresults(reproduced) |      | Correctedresults |      |
| ---------------- | ------------------ | ------------------------------------ | ---- | ---------------- | ---- |
|                  | FearonandLaitin    | 0.69                                 | 0.78 |                  | 0.54 |
|                  | CollierandHoeffler | 0.90                                 | 0.83 |                  | 0.57 |
| HegreandSambanis |                    | 0.83                                 | 0.82 |                  | 0.68 |
|                  | Muchlinskietal.    | 0.94                                 | 0.95 |                  | 0.64 |
TableA1.OriginalandcorrectedresultsinMuchlinskietal.(2016). Whiletherearedifferencesbetweenthereportedresultsandour
reproductionofthereportedresults,especiallyfortheFearonandLaitinaswellastheCollierandHoefflermodels,therelativeorderof
themodelperformanceforbothresultsisthesame.
|                    | Algorithm                                                                 | Reported Reportedresults(reproduced) |      |     | Correctedresults |
| ------------------ | ------------------------------------------------------------------------- | ------------------------------------ | ---- | --- | ---------------- |
|                    | FearonandLaitin                                                           | 0.77                                 | 0.77 |     | 0.79             |
|                    | Muchlinskietal.                                                           | 0.89                                 | 0.89 |     | 0.73             |
| ColaresiandMahmood |                                                                           | 0.91                                 | 0.91 |     | 0.75             |
|                    | TableA2. OriginalresultsfromColaresi&Mahmood(2017)andourcorrectedresults. |                                      |      |     |                  |
pitfallasinMuchlinskietal.(2016),albeitwithaslightlydifferentdataset. Correctingtheimputationmethoddramatically
reducestheperformanceoftheMLmodelsproposed.
WefocusonreproducingthefinalroundofresultsreportedinthepaperColaresi&Mahmood(2017),whichconsistsofa
comparisonof3modelsofcivilwaronset—theRandomForestsmodelproposedinMuchlinskietal.(2016),theRandom
ForestsmodelproposedinColaresi&Mahmood(2017)aswellastheLogisticRegressionmodelproposedinFearon&
Laitin(2003). Theirdatasethas17.4%valuesmissing,andthetestsethas19%valuesmissing. Theproportionofmissing
valuesinindividualvariablescanbeevenhigher—forexample,theagexp,whichrepresentstheproportionofagricultural
exportsintheGDPofacountry,ismissingfor54.3%oftherowsinthetestset. Inourcorrectedresults,weusetheoriginal
datasetfromHegre&Sambanis(2006)andimputethetrainingandtestdataseparatelyusingtherfImputefunction. Thetest
setconsistsofdatafromtheyearsafter1988. Oneoftheindependentvariables,milper,ismissingforallinstancesinthe
testsetofColaresi&Mahmood(2017)soweexcludethisvariablefromourmodels. TableA2providesthecomparisons
betweentheresultsreportedinColaresi&Mahmood(2017),ourreproductionsoftheirreported(incorrect)results,aswell
asthecorrectedversionoftheirresults.
Colaresi&Mahmood(2017)andWang(2019)reusethedatasetreleasedbyMuchlinskietal.(2016). Thisistheimputed
versionofthedatasetreleasedbyHegre&Sambanis(2006). However,for777rowsintheimputeddatasetreleasedby
Muchlinskietal.(2016),theoriginaldatasetbyHegre&Sambanis(2006)hasamissingtargetvariable(i.e. thevariable
representingcivilwaronsetismissing)whereastheimputedversionofthedataset(i.e. thedatasetreleasedbyMuchlinski
etal.(2016))hasavalueofpeaceforthetargetvariablerepresentingcivilwaronset. SinceMuchlinskietal.(2016)do
notsharethecodethattheyuseforimputingtheHegre&Sambanis(2006)dataset,itisunclearhowthemissingvaluesin
thetargetvariablewereimputedinthedataset,especiallysincetheimputationmethodtheyuse—rfImpute—requires
non-missingvaluesinthetargetvariable. Still,thenumberofinstancesofcivilwaronset(i.e. instanceswherethevariable
representingcivilwaronsethasthevaluewar)intheHegre&Sambanis(2006)datasetaswellastheMuchlinskietal.
(2016)datasetarethesame.
B.4.Wang(2019)
SimilartoColaresi&Mahmood(2017),Wang(2019)reportthatMLmodelsvastlyoutperformLogisticRegressionfor
predicting civil war onset. However, they too re-use the imputed version of the dataset in Hegre & Sambanis (2006)
providedbyMuchlinskietal. (Muchlinskietal.,2016). Theyusetheimputeddatasetbothfortrainingandtestingviak-fold
cross-validation;theydonotusetheout-of-sampletestsetprovidedbyMuchlinskietal. Correctingtheimputationmethod
dramaticallyreducestheperformanceoftheMLmodelsproposed.
Wefocusonreproducingtheresultsofthenestedcross-validationimplementationreportedbyWang(2019). Wang(2019)
reusestheimputeddatasetprovidedbyMuchlinskietal.(2016),insteadofusingtheoriginaldatasetprovidedbyHegre&
Sambanis(2006)andimputingthetrainingandtestsetsseparately. Thedatasethas17.4%valuesmissing. Theproportion
ofmissingvaluesinindividualvariablescanbeevenhigher—forexample,theagexp,whichrepresentstheproportionof
agriculturalexportsintheGDPofacountry,ismissingfor49.8%oftherowsinthedataset. Inourcorrectedresults,we

LeakageandtheReproducibilityCrisisinML-basedScience KapoorandNarayanan
Algorithm Reported Reported(reproduced) k-foldCV(corrected) Out-of-sample(corrected)
FearonandLaitin 0.76 0.76 0.77 0.78
CollierandHoeffler 0.78 0.78 0.72 0.77
HegreandSambanis 0.80 0.80 0.81 0.80
Muchlinskietal. 0.92 0.92 0.78 0.73
AdaBoost 0.94* 0.94 0.82 0.77
GBT 0.94* 0.94 0.81 0.75
TableA3.OriginalandcorrectedresultsintheWang(2019).Wefindthatusinganout-of-sampletestsetfurtherfavorsLogisticRegression
modelsoverMLmodels. ThemetricforallresultsisAUC.*Theseresultswerenotreportedusingnestedcross-validationinWang
(2019).Inourreproductionofthesereportedresults,weusenestedcross-validation,whichensuresthatwedonotgetover-estimatesof
performance.
usetheoriginaldatasetfromHegre&Sambanis(2006)andimputethetrainingandtestdataseparatelyusingtherfImpute
functionwithineachcrossvalidationfold. Thisensuresthatthereisnodataleakagebetweenthetrainingandtestsetsin
eachfold. TableA3providesthecomparisonsbetweentheresultsreportedinWang(2019), ourreproductionsoftheir
reported(incorrect)results,aswellasthecorrectedversionoftheirresults.
Wealsoconductanadditionalrobustnessanalysisinwhichweuseaseparateout-of-sampletestsetinsteadofk−foldcross
validation,sinceusingk−foldcrossvalidationwithtemporaldatacanalsoleadtoleakageacrossthetrain-testsplit. To
maintaincomparabilitybetweentheoriginalandcorrectedresultsbytestingonthesameinstancesofcivilwar,wecontinue
tousek−foldcrossvalidationinthecorrectedresultsinFigure1. WereporttheresultsaftermakingthischangeinTableA3.
Weusethesametrain-testsplitasColaresi&Mahmood(2017)—year<1988astrainingdataandtherestastestdata
—fortheout-of-sampletestset. Thetestsetconsistsofdatafromtheyearsafter1988. Oneoftheindependentvariables,
milper, ismissingforallinstancesinthetestsetofColaresi&Mahmood(2017)soweexcludethisvariablefromour
models.
Notethattheimputationmethodthatshouldbeuseddependsontheexactmodeldeploymentscenario,andshouldmimicit
ascloselyaspossibleforaccurateperformanceestimates. Forexample,insomemodeldeploymentsettingssamplesfor
predictioncomeinoneatatimeandinsomecasestheycomeinbatches. Intheformersetting,imputingtheentiretestset
togethermayresultinoveroptimisticperformanceevaluationsaswell,sincethedeployedmodeldoesn’thaveaccesstoa
batchofsamples. Ourresultsmaythusofferanupperboundontheperformanceofcivilwarpredictionmodelsinthecase
ofColaresi&Mahmood(2017)andWang(2019).
B.5.Kaufmanetal.(2019)
WefocusonreproducingtheresultsoncivilwarpredictioninKaufmanetal.(2019). Thereareseveralissuesinthepaper’s
results. WeoutlineeachissuebelowandprovideacomparisonofvariousscenariosinTableA4thathighlighttheprecise
causeoftheperformancedifferencebetweentheoriginalandcorrectedresults,andvisualizetherobustnessofourcorrected
results. WefindthateventhoughthereareseveralissuesinKaufmanetal.(2019),themaindifferenceinperformance
betweentheoriginalresultstheyreportandourcorrectedresultsisduetodataleakage.
Dataleakageduetoproxyvariables. ThedatasetusedbyKaufmanetal.(2019)hasseveralvariablesthat,ifusedas
independentvariablesinmodelsofcivilwarprediction,couldcausedataleakage,sincetheyareproxiesoftheoutcome
variable. TableA5liststhevariablesintheFearon&Laitin(2003)datasetthatcauseleakage. Thefirst4rowsoutline
variablesthatcouldbeaffectedbycivilwars,asoutlinedinFearon&Laitin(2003). Therefore,followingFearon&Laitin
(2003),weuselaggedversionsofthesevariablesinourcorrection. TheothervariablesinTableA5areeitherdirectproxies
ofoutcomesofinterestoraremissingforallinstancesforcivilwar.
ParameterselectionfortheLassomodel. Kaufmanetal.(2019)useanincorrectparameterselectiontechniquewhen
creating their Lasso model that leads to the model always predicting peace (i.e. all coefficients of the variables in the
modelarealwayszero). Wecorrectthisusingastandardtechniqueforparameterselection. Insteadofchoosingmodel
parameterssuchthatthemodelalwayspredictspeace,weusethecv.glmnetfunctioninRtochooseasuitablevaluefor
modelparametersbasedonthetrainingdata.

LeakageandtheReproducibilityCrisisinML-basedScience KapoorandNarayanan
Usingk−foldcrossvalidationwithtemporaldata. k−foldcrossvalidationshufflesthedatasetbeforeitisdividedinto
trainingandtestdatasets. Whenthedatasetcontainstemporaldata,thetrainingdatasetcouldcontaindatafromalaterdate
thanthetestdatasetbecauseofbeingshuffled. Tomaintaincomparabilitybetweentheoriginalandcorrectedresultsby
testingonthesameinstancesofcivilwar,wecontinuetousek−foldcrossvalidationinthecorrectedresultsinFigure1. To
evaluateout-of-sampleperformancewithoutusingcross-validation,weuseaseparatetrain-testsplitinsteadofk−foldcross
validationandreportthedifferenceinresultsforthisscenariointherowCorrected(out-of-sample)inTableA4. Wefind
thatthereisnosubstantialdifferencebetweentheresultswhenusingtheout-of-sampletestsetandk−foldcrossvalidation
—ineachcase,noneofthemodelsoutperformsabaselinethatpredictstheoutcomeofthepreviousyear. Weusethesame
train-testsplitasColaresi&Mahmood(2017)—year<1988astrainingdataandtherestastestdata.
Replacingmissingvalueswithzeros. Kaufmanetal.(2019)replacemissingvaluesintheirdatasetwithzeros,instead
ofimputingthemissingdataorremovingtherowswithmissingvalues. Thisisamethodologicallyunsoundwayofdealing
withmissingdata: forexample,themodelswouldnotbeabletodiscernwhetheravariablehasavalueofzerobecause
of missing data or because it was the true value of the variable for that instance. This risks getting underestimates of
performance,asopposedtooveroptimisticperformanceclaims. Asarobustnesscheck,weimputethetrainingandtestdata
separatelyineachcross-validationfoldusingtherfImputefunctioninRandreporttheresultsintheCorrected(imputation)
rowofTableA4. Wefindthatthechoiceofimputationmethoddoesnotcauseadifferenceinperformance,perhapsbecause
only0.6%ofthevaluesofvariablesaremissinginthedataset.
Choiceofcut-offsforcalculatingaccuracy. Insteadofcalculatingmodelcutoffsbasedonthebestcutoffinthetraining
set,Kaufmanetal. usethedistributionofmodelscorestodecidethecutoffsforcalculatingaccuracy. Weincluderobustness
resultswhenwechangethecutoffselectionproceduretochoosingthebestcutoffsforthetrainingsetintheCorrected
(cutoffchoice)rowofTableA5. Wefindthatthechoiceofcutoffdoesnotimpactthemainclaim—theperformanceofthe
bestmodelisstillworsethanabaselinethatpredictstheoutcomeofthepreviousyear.
WeakBaseline. Kaufmanetal.(2019)comparetheirresultsagainstabaselinemodelthatalwayspredictspeace. Wefind
thatabaselinethatpredictswariftheoutcomeofthetargetvariablewascivilwarinthepreviousyearandpredictspeace
otherwiseisastrongerbaseline(Accuracy: 97.5%vs. 86.1%;χ2=633.7,p=7.836e-140usingMcNemar’stestasdetailed
inDietterich(1998)),andreportresultsagainstthisstrongerbaselineinTableA4.
Confusionaboutthetargetvariable. Kaufmanetal.(2019)useongoingcivilwarinsteadofcivilwaronsetasthetarget
variableintheirmodels. Whiletheirabstractmentionsthatthepredictiontasktheyattemptiscivilwaronsetprediction,they
switchtousingthetermcivilwarincidenceinlatersections,withoutformallydefiningthisterm. Toattempttodetermine
whattheymeanbythisterm,welookedatthepaperstheycite;oneofthemhasthetermcivilwarincidenceinthetitle
Collier&Hoeffler(2002),anddefinescivilwarincidenceas‘observations[that]experiencedastartofacivilwar’. Atthe
sametime,intheintroduction,theystatethattheyare‘predictingwhethercivilwaroccursinacountryinagivenyear’—
whichreferstoongoingcivilwarinsteadofcivilwaronset. Thismightconfuseareaderaboutthespecificpredictiontask
theyundertake.
Scenario ADT RF SVM ERF Lasso LR Baseline StrongerBaseline
Reported 0.990 0.989 0.983 0.990 0.862 0.987 0.861 0.000
Reported(reproduction) 0.990 0.990 0.983 0.989 0.861 0.987 0.861 0.000
Corrected 0.974 0.959 0.974 0.957 0.975 0.972 0.861 0.975
Corrected(out-of-sample) 0.966 0.936 0.962 0.927 0.966 0.963 0.796 0.966
Corrected(imputation) 0.974 0.959 0.974 0.957 0.975 0.975 0.861 0.975
Corrected(cutoffchoice) 0.974 0.972 0.966 0.967 0.975 0.971 0.861 0.975
TableA4.ResultsforthevariousscenariosinKaufmanetal.(2019).Wereportresultsupto3significantfiguresinthistablebecausethe
smalldifferenceinperformancebetweenAdaBoostandLogisticRegressionthatisascribedsignifanceinKaufmanetal.(2019)canonly
beobservedinthethirddecimalpoint.Thefirst2valuesof‘StrongerBaseline’arereportedas0becausethisbaselinewasnotincludedin
theresultsofKaufmanetal.(2019).

LeakageandtheReproducibilityCrisisinML-basedScience KapoorandNarayanan
Variablename Reasonforleakage Variabledefinitionindatadocumentation
| pop     | affectedbytargetvariable |     | population;in1000s |
| ------- | ------------------------ | --- | ------------------ |
| lpop    | affectedbytargetvariable |     | logofpopulation    |
| polity2 | affectedbytargetvariable |     | revisedpolityscore |
gdpen affectedbytargetvariable gdp/popbasedonpwt5.6;wdi2001;cowenergydata
| onset    | codescivilwaronset |     | 1forcivilwaronset      |
| -------- | ------------------ | --- | ---------------------- |
| ethonset | codescivilwaronset |     | 1ifonset=1andethwar∼=0 |
| durest   | NAifonset=0        |     | estimatedwarduration   |
aim NAifonset=0 1=rebelsaimatcenter;3=aimatexitorautonomy;2=mixedorambig.
| ended    | NAifonset=0        |                                    | warends=1;0=ongoing          |
| -------- | ------------------ | ---------------------------------- | ---------------------------- |
| ethwar   | NAifonset=0        | 0=notethnic;1=ambig/mixed;2=ethnic |                              |
| emponset | codescivilwaronset |                                    | onsetcodedfordatawithempires |
sdwars codesongoingcivilwar NumberofSambanis/Doylecivwarsinprogress
| sdonset | codescivilwaronset |     | onsetofSambanis/Doylewar |
| ------- | ------------------ | --- | ------------------------ |
colwars codesongoingcivilwar NumberofCollier/Hoefflerwarsinprogress
| colonset | codescivilwaronset   |     | onsetofCollier/Hoefflerwar   |
| -------- | -------------------- | --- | ---------------------------- |
| cowwars  | codesongoingcivilwar |     | NumberofCOWcivwarsinprogress |
| cowonset | codescivilwaronset   |     | onsetofCOWcivwar             |
TableA5.ThistablehighlightsthevariablesincludedasindependentvariablesinKaufmanetal.(2019)whichcauseadataleakage.In
theoriginaluseofthedataset,Fearon&Laitin(2003)includelaggedversionsofthefirst4variablesinthelistasindependentvariablesin
theirmodeltoavoidleakage.Followingtheiruseoflaggedversionsofthesevariables,wedothesameinourcorrectiontoavoidleakage.
Theothervariablesareproxiesfortheoutcomesofinterestandhenceweremovethemfromthemodelstoavoiddataleakage.
B.6.Blair&Sambanis(2020)
Blair&Sambanis(2020)statethattheirescalationmodeloutperformsothermodelsacrossavarietyofsettings. However,
they do not test the performance evaluations to see if the difference is statistically significant. We find that there is no
significantdifferencebetweenthesmoothedAUCvaluesoftheescalationmodel’sperformanceandothermodelsthey
compareittowhenweuseatestforsignificance. Further,weprovideavisualizationofthe95%confidenceintervalsof
specificitiesandsensitivitiesinthesmoothedROCcurvetheyreportfortheirmodel(escalation)aswellasforabaseline
model(cameo)—andfindthatthe95%confidenceintervalsarelarge(seeFigureA3).
Uncertaintyquantification,p-valuesandZ-valuesfortestsofstatisticalsignificance.
• Wereportp-valuesandZvaluesforaone-tailedsignificancetestcomparingthesmoothedAUCperformanceofthe
escalationmodelwithotherbaselinemodelsreportedintheirpaper—quad,goldstein,cameoandaveragerespectively.
Notethatwedonotcorrectformultiplecomparisons;suchacorrectionwouldfurtherreducethesignificanceofthe
results. WeimplementthecomparisontestforsmoothedROCcurvesdetailedinRobinetal.(2011).
– 1monthforecasts: Z=0.64,1.09,0.42,0.67;p=0.26,0.14,0.34,0.25
– 6monthsforecasts: Z=0.41,0.08,0.70,0.69;p=0.34,0.47,0.24,0.25
• The95%confidenceintervalsforthe1monthmodelsare:
| – escalation: | 0.66-0.95 |     |     |
| ------------- | --------- | --- | --- |
| – quad:       | 0.63-0.95 |     |     |
| – goldstein:  | 0.62-0.93 |     |     |
| – cameo:      | 0.65-0.95 |     |     |
| – average:    | 0.65-0.95 |     |     |
• The95%confidenceintervalsforthe6monthmodelsare:
| – escalation: | 0.64-0.93 |     |     |
| ------------- | --------- | --- | --- |
| – quad:       | 0.60-0.90 |     |     |
| – goldstein:  | 0.68-0.93 |     |     |

LeakageandtheReproducibilityCrisisinML-basedScience KapoorandNarayanan
– cameo: 0.58-0.92
– average: 0.60-0.92
Whileasmallp-valueisusedtorejectthenullhypothesis(inthiscase—thattheout-of-sampleperformancedoesnot
differbetweenthemodelsbeingcompared),asingularfocusonatestforstatisticalsignificanceatapre-definedthreshold
canbeharmful(see,forexampleImbens(2021)). BlairandSambanisdoreportperformanceevaluationsforavarietyof
differentmodelspecifications. However,thepurposeofsuchrobustnesschecksistodeterminewhethermodelperformance
sensitivetotheparameterchoices;itisunclearwhetherithelpsdealwithissuesarisingfromsamplingvariance. Atany
rate,BlairandSambanis’sresultsturnouttobehighlysensitivetoanothermodelingchoice: thefactthattheycomputethe
AUCmetriconthesmoothedROCcurveinsteadoftheempiricalcurvethattheirmodelproduces. Smoothingreferstoa
transformationoftheROCcurvetomakethepredictedprobabilitiesforthewarandpeaceinstancesnormallydistributed
insteadofusingtheempiricalROCcurve(seeRobinetal.(2011)). ThisissuewaspointedoutbyBegeretal.(2021)and
completelychangestheiroriginalresults;Blair&Sambanis(2021)discussitintheirrebuttal.
B.7.OverviewofpapersinTableA6
TableA6providesthelistof12papersincludedinourreview,showinginformationaboutwhethertheyreportconfidence
intervals,conducttestsofstatisticalsignificancewhencomparingclassifierperformance,whichmetricstheyreport,the
numberofrowsandthenumberofpositiveinstances(i.e. instancesofwar/conflict)inthetestset,andwhethertheirmain
claimreliesonout-of-sampleevaluationofclassifierperformance. Wedetailinformationaboutthenumberswereportin
TableA6below.
• Hegreetal.(2016): Wereportthenumberofrowsandnumberofpositiveinstancesofcivilwarincidenceforthedates
between2001and2013intheUCDPdataset,i.e. allyearsforwhichout-of-sampleestimatesareprovided. Wereport
theout-of-sampleAUCperformancedifferencefortheMajorconflictsetting. Out-of-sampleevaluationresultsare
notincludedinthemaintextofthepaper,hencewereportthatthepaper’smainclaimdoesnotrelyonout-of-sample
evaluations.
• Muchlinski et al. (2016): We report the number of rows and number of positive instances of civil war onset for
thedatesafter2000intheout-of-sampledatasetprovidedbyMuchlinskietal. Wereporttheout-of-sampleAUC
performancedifferencebetweentheRandomForestsandthebestLogisticRegressionsetting.Out-of-sampleevaluation
resultsareusedtojustifytheperformanceimprovementofusingRandomForestsmodels,hencewereportthatthe
paper’smainclaimreliesonout-of-sampleevaluations.
• Chiba&Gleditsch(2017): Wereportthetotalnumberofinstancesandthenumberofpositiveinstancesofgovern-
mentalonsetsintheyears2013-14(thetestsetdates). WereportthedifferencebetweentheterritorialonsetAUC’s
reported in the paper. Note that while Chiba & Gleditsch (2017) do report small number of data points that are
usedinoneoftheirsettings,theydonotaddresshowtoestimatevarianceorperformtestsofstatisticalsignificance.
Out-of-sampleevaluationresultsarenotusedasthemainevidenceofbetterperformanceinthemaintextofthepaper,
hencewereportthatthepaper’smainclaimdoesnotrelyonout-of-sampleevaluations.
• Colaresi&Mahmood(2017): Wereportthenumberofrowsandonsetsofcivilwaraftertheyear1988(thetestset
dates). Wereporttheout-of-sampleAUCdifferencebetweenthetworandomforestsmodelscomparedinthepaper.
Out-of-sampleevaluationresultsareusedtojustifytheperformanceimprovementofusinganiterativemethodfor
modelimprovement,hencewereportthatthepaper’smainclaimreliesonout-of-sampleevaluations.
• Hiroseetal.(2017): Wereportthenumberoflocationsincludedintheout-of-sampleresults. Sincethepaperdoes
notattemptbinaryclassification,wedonotreportthenumberofpositiveinstancesinthiscase. Wereporttheout-of-
sampleperformancegainofaddingrelativeISAFsupporttothebaselinemodelintheIEDattacksettingofthepaper.
Out-of-sampleevaluationresultsareusedasimportantevidenceofbettermodelperformanceinthemaintextofthe
paper,hencewereportthatthepaper’smainclaimreliesonout-of-sampleevaluations.
• Schutte(2017): Wereportthenumberofrowsintheentiredataset,sincethepaperusesk-foldcrossvalidationand
thereforeallinstancesareusedfortesting. Sincethepaperdoesnotattemptbinaryclassification,wedonotreport
thenumberofpositiveinstancesinthiscase. Wereporttheout-of-samplenormalizedMAEdifferencebetweenthe
populationmodelandthebestperformingmodelcomparedinthepaper. Out-of-sampleevaluationresultsareusedas

LeakageandtheReproducibilityCrisisinML-basedScience KapoorandNarayanan
(a)Visualizingthe95%confidenceintervalsofthespecificities (b)Visualizingthe95%confidenceintervalsofthesensitivities
forthe1monthforecastinthesmoothedROCcurvereported forthe1monthforecastinthesmoothedROCcurvereported
inBlair&Sambanis(2020). inBlair&Sambanis(2020).
(c)Visualizingthe95%confidenceintervalsofthespecificities (d)Visualizingthe95%confidenceintervalsofthesensitivities
forthe6monthforecastinthesmoothedROCcurvereported forthe6monthforecastinthesmoothedROCcurvereported
inBlair&Sambanis(2020). inBlair&Sambanis(2020).
FigureA3.The wide confidence intervals for sensitivities and specificities reported in Blair and Sambanis. Here, we visualize the
escalationandcameomodelsforthe1monthand6monthforecastinthebasespecification(reportedinFigure1oftheirpaper).
importantevidenceofbettermodelperformanceinthemaintextofthepaper,hencewereportthatthepaper’smain
claimreliesonout-of-sampleevaluations.
• Hegreetal.(2019b): Wereportthenumberofrowsandnumberofpositiveinstancesofcivilwarincidenceforthe
datesbetween2001and2013intheUCDPdataset,i.e. allyearsforwhichout-of-sampleestimatesareprovided. We
reporttheout-of-sampleAUCperformancedifferencefortheMajorconflictsetting. Out-of-sampleevaluationresults
arenotusedastheprimaryevidenceofbettermodelperformanceinthemaintextofthepaper,hencewereportthatthe

LeakageandtheReproducibilityCrisisinML-basedScience KapoorandNarayanan
|                       | Stat.sig |                | Num.rows Num.positive      | MainClaim OOSperformance |
| --------------------- | -------- | -------------- | -------------------------- | ------------------------ |
| Paper                 | CI?      | Metric(s)      |                            |                          |
|                       | test?    |                | intestset testsetinstances | OOS? delta               |
| Hegreetal.(2016)      | No No    | AUC,Brierscore | 2197 321                   | No 0.006                 |
| Muchlinskietal.(2016) | No No    | AUC,F1score    | 896 19                     | Yes 0.04                 |
| Chiba&Gleditsch(2017) | No No    | AUC,Brierscore | 4176 15                    | No 0.03                  |
Colaresi&Mahmood(2017) No No AUC,Precision,Recall 1778 29 Yes 0.02
| Hiroseetal.(2017) | No *  | MAE,RMSE | 14,606 — | Yes 0.16 |
| ----------------- | ----- | -------- | -------- | -------- |
| Schutte(2017)     | No No | MAE      | 3744 —   | Yes 0.09 |
| Hegreetal.(2019b) | No No | AUC      | 2197 321 | No 0.02  |
AUC,Brierscore,AUPR,Accuracy,
| Hegreetal.(2019a) | No No |     | 384,372 1848 | Yes 0.01 |
| ----------------- | ----- | --- | ------------ | -------- |
F1score,cost-basedthreshold
| Kaufmanetal.(2019) | No No  | Accuracy             | 6610 918 | Yes 0.03 |
| ------------------ | ------ | -------------------- | -------- | -------- |
| Wang(2019)         | Yes No | AUC,Precision,Recall | 6363 116 | Yes 0.12 |
Blair&Sambanis(2020) No No AUC,Precision,Recall 15,744 11 Yes 0.03
| Hegreetal.(2021) | Yes No | AUC,AUPR,TPR/FPR | 3042 79 | Yes — |
| ---------------- | ------ | ---------------- | ------- | ----- |
TableA6.Alistofpapersforwhichcodeanddatasetwereavailable,showinginformationaboutwhethertheyreportconfidenceintervals,
conducttestsofstatisticalsignificancewhencomparingclassifierperformance,whichmetricstheyreport,thenumberofrowsandthe
numberofpositiveinstances(i.e. instancesofwarorconflictoronsetthereof)inthetestset,andwhethertheirmainclaimrelieson
out-of-sampleevaluationofclassifierperformance.AUC=AreaUnderROC,MAE=MeanAbsoluteError,RMSE=RootMeanSquared
Error,AUPR=AreaUnderPrecision-RecallCurve,TPR=TruePositiveRate,FPR=FalsePositiveRate,OOSperformancedelta=the
performancedifferenceforthemostsalientperformancecomparisonreportedinthepaper(detailsinSectionB.7).*Hiroseetal.state
thattheout-of-sampleperformanceissignificantlybetterintheSupplementoftheirpaper,butwecouldnotfindthefiguretheyciteas
evidenceofthisclaimintheirSupplement.
paper’smainclaimdoesnotrelyonout-of-sampleevaluations.
• Hegreetal.(2019a): WereportthenumberinstanceswithstatebasedconflictintheViEWSMonthlyOutcomesat
PRIO-GridLeveldatabetween2015and2017—theyearsforwhichtheout-of-sampleresultsarereportedinthe
paper. Wereporttheout-of-sampleAUCperformancedifferenceforthestate-basedconflictsetting. Out-of-sample
evaluationresultsareusedastheprimaryevidenceofbettermodelperformanceinthemaintextofthepaper,hencewe
reportthatthepaper’smainclaimreliesonout-of-sampleevaluations.
• Kaufmanetal.(2019): Wereportthetotalnumberofrowsandallinstancesofcivilwarincidenceinthedatasetused
byKaufmanetal.,sincetheyusek-foldcrossvalidationandthereforeallinstancesareusedfortesting. Wereportthe
out-of-sampleaccuracydifferencebetweentheAdaboostandLogisticRegressionsettings. Out-of-sampleevaluation
resultsareusedastheprimaryevidenceofbettermodelperformanceinthemaintextofthepaper,hencewereportthat
thepaper’smainclaimreliesonout-of-sampleevaluations.
• Wang(2019): WereportthetotalnumberofrowsandonsetsofcivilwarusedinthedatasetusedbyWangsince
theyusek-foldcrossvalidationandthereforeallinstancesareusedfortesting. Wereporttheout-of-sampleAUC
performancedifferencebetweentheAdaboostandLogisticRegressionmodels. Out-of-sampleevaluationresultsare
usedastheprimaryevidenceofbettermodelperformanceinthemaintextofthepaper,hencewereportthatthepaper’s
mainclaimreliesonout-of-sampleevaluations.
• Blair&Sambanis(2020): Wereportthenumberofrowsandonsetsofcivilwaraftertheyear2007(thetestsetdates).
Wereporttheout-of-sampleAUCperformancedifferencebetweentheescalationandcameomodelsfortheone-month
basesetting. Out-of-sampleevaluationresultsareusedastheprimaryevidenceofbettermodelperformanceinthe
maintextofthepaper,hencewereportthatthepaper’smainclaimreliesonout-of-sampleevaluations.
• Hegreetal.(2021): Wereportthenumber ofrowsand numberofpositiveinstancesforcivilwar onsetthedates
between2001and2018,i.e.allyearsforwhichout-of-sampleestimatesareprovided.Wedon’treporttheout-of-sample
performancedifferencebecausethepaperdoesnotperformcomparisonsbetweenmodels. Out-of-sampleevaluation
resultsareusedastheprimaryevidenceofmodelperformanceinthemaintextofthepaper,hencewereportthatthe
paper’smainclaimreliesonout-of-sampleevaluations.

LeakageandtheReproducibilityCrisisinML-basedScience KapoorandNarayanan
C.ModelinfosheetsfordetectingandpreventingleakageinML-basedscience
WeincludethemodelinfosheettemplateasaMicrosoftWorddocumentonourwebsite(https://reproducible.
cs.princeton.edu). Here,wedetailhowmodelinfosheetswouldaddresseachtypeofleakagethatwefoundinour
survey,aswellasthetypesofleakagewefoundinourcasestudyofcivilwarprediction.
• L1.1Notestset. Modelinfosheetsrequireanexplanationofhowthetrainandtestsetissplitduringallstepsinthe
modelingprocess(Q9-17ofmodelinfosheets).
• L1.2Pre-processingontrainingandtestset. Detailsofhowthetrainandtestsetareseparatedduringthepreprocess-
ingselectionstepneedtobeincludedinthemodelinfosheet(Q12-13). Thiswouldaddressleakageduetoincorrect
imputationMuchlinskietal.(2016);Wang(2019);Colaresi&Mahmood(2017).
• L1.3Featureselectionontrainingandtestset. Detailsofhowthetrainandtestsetareseparatedduringthefeature
selectionstepneedtobeincludedinthemodelinfosheet(Q14-15).
• L1.4Duplicatesindatasets. Modelinfosheetsrequiredetailsofwhetherthereareduplicatesinthedataset,andifso,
howtheyarehandled(Q10).
• L2Modelusesfeaturesthatarenotlegitimate. Foreachfeatureusedinthemodel,researchersneedtoarguewhy
thefeatureislegitimatetobeusedforthemodelingtaskathand(Q21). Thisaddressestheleakageduetotheuseof
proxyvariablesinKaufmanetal.(2019).
• L3.1 Temporal leakage. In case the claim is about predicting future outcomes of interest based on ML methods,
researchersneedtoprovideanexplanationforwhythetimewindowsusedinthetrainingandtestsetareseparate,and
whydatainthetestsetisalwaysalatertimestampcomparedtothedatainthetrainingset(Q20). Thisaddressesthe
temporalleakageinKaufmanetal.(2019);Wang(2019).
• L3.2Dependenciesintrainingandtestdata. Researchersneedtoreasonaboutthedependenciesthatmayexistin
theirdatasetandoutlinehowdependenciesacrosstrainingandtestsetsareaddressed(Q11).
• L3.3 Sampling bias in test distribution. Researchers need to reason about the presence of selection bias in their
datasetandoutlinehowtherowsincludedfordataanalysiswereselected,andhowthetestsetmatchesthedistribution
aboutwhichthescientificclaimsaremade(Q18-19).