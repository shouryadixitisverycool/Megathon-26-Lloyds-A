| Why do        | tree-based | models |                | still | outperform | deep          |
| ------------- | ---------- | ------ | -------------- | ----- | ---------- | ------------- |
|               | learning   |        | on tabular     |       | data?      |               |
| LéoGrinsztajn |            |        | EdouardOyallon |       |            | GaëlVaroquaux |
Soda,InriaSaclay ISIR,CNRS,SorbonneUniversity Soda,InriaSaclay
leo.grinsztajn@inria.fr
2202 luJ 81  ]GL.sc[  1v51880.7022:viXra
Abstract
Whiledeeplearninghasenabledtremendousprogressontextandimagedatasets,
| itssuperiorityontabulardataisnotclear. |     |     |     | Wecontributeextensivebenchmarksof |     |     |
| -------------------------------------- | --- | --- | --- | --------------------------------- | --- | --- |
standardandnoveldeeplearningmethodsaswellastree-basedmodelssuchas
XGBoostandRandomForests,acrossalargenumberofdatasetsandhyperparame-
| tercombinations. | Wedefineastandardsetof45datasetsfromvarieddomainswith |     |     |     |     |     |
| ---------------- | ----------------------------------------------------- | --- | --- | --- | --- | --- |
clearcharacteristicsoftabulardataandabenchmarkingmethodologyaccounting
| forbothfittingmodelsandfindinggoodhyperparameters. |     |     |     |     | Resultsshowthattree- |     |
| -------------------------------------------------- | --- | --- | --- | --- | -------------------- | --- |
basedmodelsremainstate-of-the-artonmedium-sizeddata(∼10Ksamples)even
| withoutaccountingfortheirsuperiorspeed. |     |     |     | Tounderstandthisgap,weconductan |     |     |
| --------------------------------------- | --- | --- | --- | ------------------------------- | --- | --- |
empiricalinvestigationintothedifferinginductivebiasesoftree-basedmodelsand
| NeuralNetworks(NNs).                         |                                                         | Thisleadstoaseriesofchallengeswhichshouldguide |        |                           |                            |                 |
| -------------------------------------------- | ------------------------------------------------------- | ---------------------------------------------- | ------ | ------------------------- | -------------------------- | --------------- |
| researchersaimingtobuildtabular-specificNNs: |                                                         |                                                |        |                           | 1. berobusttouninformative |                 |
| features,                                    | 2. preserve                                             | the orientation                                | of the | data,                     | and 3. be able             | to easily learn |
| irregularfunctions.                          | Tostimulateresearchontabulararchitectures,wecontributea |                                                |        |                           |                            |                 |
| standardbenchmarkandrawdataforbaselines:     |                                                         |                                                |        | everypointofa20000compute |                            |                 |
hourshyperparametersearchforeachlearner.
1 Introduction
Deep learning has enabled tremendous progress for learning on image, language, or even audio
datasets. Ontabulardata,however,thepictureismuddierandensemblemodelsbasedondecision
treeslikeXGBoostremainthego-totoolformostpractitioners[Sta]anddatasciencecompetitions
[Kossenetal.,2021]. Indeeddeeplearningarchitectureshavebeencraftedtocreateinductivebiases
matchinginvariancesandspatialdependenciesofthedata. Findingcorrespondinginvariancesishard
intabulardata,madeofheterogeneousfeatures,smallsamplesizes,extremevalues.
Creatingtabular-specificdeeplearningarchitecturesisaveryactiveareaofresearch(seesection2)
giventhattree-basedmodelsarenotdifferentiable,andthuscannotbeeasilycomposedandjointly
trainedwithotherdeeplearningblocks. Mostcorrespondingpublicationsclaimtobeatormatchtree-
basedmodels,buttheirclaimshavebeenputintoquestion: asimpleResnetseemstobecompetitive
withsomeofthesenewmodels[Gorishniyetal.,2021],andmostofthesemethodsseemtofailonnew
datasets[Shwartz-ZivandArmon,2021]. Indeed,thelackofanestablishedbenchmarkfortabular
datalearningprovidesadditionaldegreesoffreedomtoresearcherswhenevaluatingtheirmethod.
Furthermore, most tabular datasets available online are small compared to benchmarks in other
machinelearningsubdomains,suchasImageNet[Ima],makingevaluationnoisier. Theseissuesadd
uptoothersourcesofunreplicabilityacrossmachinelearning,suchasunequalhyperparameterstuning
efforts[LiptonandSteinhardt,2019]orfailuretoaccountforstatisticaluncertaintyinbenchmarks
[Bouthillieretal.,2021]. Toalleviatetheseconcerns,wecontributeatabulardatabenchmarkwitha
precisemethodologyfordatasetsinclusionandhyperparametertuning. Thisenablesustoevaluate
recent deep learning models which have not yet been independently evaluated, and to show that
Preprint.Underreview.

tree-basedmodelsremainstate-of-the-artonmedium-sizedtabulardatasets,evenwithoutaccounting
fortheslowertrainingofdeeplearningalgorithms.
Impressedbythesuperiorityoftree-basedmodelsontabulardata,westrivetounderstandwhich
inductivebiasesmakethemwell-suitedforthesedata. Bytransformingtabulardatasetstomodify
theperformancesofdifferentmodels,weuncoverdifferingbiasesoftree-basedmodelsanddeep
learningalgorithmswhichpartlyexplaintheirdifferentperformances: neuralnetworksstruggleto
learnirregularpatternsofthetargetfunction,andtheirrotationinvariancehurttheirperformance,in
particularwhenhandlingthenumerousuninformativefeaturespresentintabulardata.
Our contributions are as follow: 1. We create a new benchmark for tabular data, with a precise
methodologyforchoosingandpreprocessingalargenumberofrepresentativedatasets. Weshare
thesedatasetsthroughOpenML[Vanschorenetal.,2014],whichmakesthemeasytouse. 2. We
extensively compare deep learning models and tree-based models on generic tabular datasets in
multiple settings, accounting for the cost of choosing hyperparameters. We also share the raw
resultsofourrandomsearches,whichwillenableresearcherstocheaplytestnewalgorithmsfora
fixedhyperparameteroptimizationbudget. 3. Weinvestigateempiricallywhytree-basedmodels
outperformdeeplearning,byfindingdatatransformationswhichnarroworwidentheirperformance
gap. This highlights desirable biases for tabular data learning, which we hope will help other
researcherstosuccessfullybuilddeeplearningmodelsfortabulardata.
InSec.2wecoverrelatedwork. Sec. 3givesashortdescriptionofourbenchmarkmethodology,
includingdatasets,dataprocessing,andhyper-parametertuning. Then,Sec. 4showsourrawresults
ondeeplearningandtree-basedmodelsafteranextensiverandomsearch. Finally,Sec. 5provides
theresultsofanempiricalstudywhichexhibitdesirableimplicitbiasesoftabulardatasets.
2 Relatedwork
Deep learning for tabular data As described by Borisov et al. [2021] in their review of the
field,therehavebeenvariousattemptstomakedeeplearningworkontabulardata: dataencoding
techniquestomaketabulardatabettersuitedfordeeplearning[HancockandKhoshgoftaar,2020,
Yoonetal.,2020],"hybridmethods"tobenefitfromtheflexibilityofNNswhilekeepingtheinductive
biasesofotheralgorithmsliketree-basedmodels[Layetal.,2018,Popovetal.,2020,Abutbuletal.,
2020,Hehnetal.,2019,Tannoetal.,2019,Chen,2020,Kontschiederetal.,2015,Rodriguezetal.,
2019, Popov et al., 2020, Lay et al., 2018] or Factorization Machines Guo et al. [2017], tabular-
specifictransformersarchitecturesSomepallietal.[2021],Kossenetal.[2021],ArikandPfister
[2019],Huangetal.[2020],andvariousregularizationtechniquestoadaptclassicalarchitecturesto
tabulardata[Lounicietal.,2021,ShavittandSegal,2018,Kadraetal.,2021a,Fiedler,2021]. In
thispaper,wefocusonarchitecturesdirectlyinspiredbyclassicdeeplearningmodels,inparticular
TransformersandMulti-Layer-Perceptrons(MLPs).
Comparisons between NNs and tree-based models The most comprehensive comparisons of
machinelearningalgorithmshavebeenpublishedbeforetheadventofnewdeeplearningmethods,
oronspecificproblems[Fernández-Delgadoetal.,2014,Sakretal.,2017,Korotcovetal.,2017,
Uddinetal.,2019]. Recently, Shwartz-ZivandArmon[2021]evaluatedmoderntabular-specific
deeplearningmethods,buttheirgoalwasmoretorevealthat"Newdeeplearningarchitecturesfail
to generalize to new datasets" than to create a comprehensive benchmark. Borisov et al. [2022]
benchmarkedrecentalgorithmsintheirreviewofdeeplearningfortabulardata,butonlyon3datasets,
and"highlight[ed]theneedforunifiedbenchmarks"fortabulardata. Mostpapersintroducinganew
architecturefortabulardatabenchmarkvariousalgorithms,butwithahighlyvariableevaluation
methodology, a small number of datasets, and the evaluation can be biased toward the authors’
modelShwartz-ZivandArmon[2021]. ThepaperclosesttoourworkisGorishniyetal.[2021],
benchmarkingnovelalgorithms,on11tabulardatasets.Weprovideamorecomprehensivebenchmark,
with45datasets,splitacrossdifferentsettings(medium-sized/large-size,with/withoutcategorical
features),accountingforthehyperparametertuningcost,toestablishastandardbenchmark.
Nostandardbenchmarkfortabulardata Unlikeothermachinelearningsubfieldssuchascom-
putervision[Ima]orNLP[Wangetal.,2020],therearenostandardbenchmarksfortabulardata.
Thereexistgenericmachinelearningbenchmarks,but,totheourknowledge,nonearespecificto
tabulardata. Forinstance,OpenMLbenchmarksCC-18,CC-100,[Bischletal.,2021]andAutoML
2

BenchmarkGijsbersetal.[2019]containtabulardata,butalsoincludeimagesandartificialdatasets,
whichmayexplainwhytheyhavenotbeenusedintabulardeeplearningpapers.
UnderstandingthedifferencebetweenNNsandtree-basedmodels Toourknowledge,thisis
thefirstempiricalinvestigationofwhy tree-basedmodelsoutperformNNsontabulardata. Some
speculativeexplanations,however,havebeenoffered[Klambaueretal.,2017,Borisovetal.,2021].
Kadraetal.[2021a]claimsthatsearchingacross13regularizationtechniquesforMLPstofinda
dataset-specificcombinationgivesstate-of-the-artperformances. Thisprovidesapartialexplanation:
MLPsareexpressiveenoughfortabulardatabutmaysufferfromalackofproperregularization.
3 Abenchmarkfortabularlearning
3.1 45referencetabulardatasets
For our benchmark, we compiled 45 tabular datasets from various domains provided mainly by
OpenML,listedinA.1andselectedviathefollowingcriteria:
Heterogeneouscolumns. Columnsshouldcorrespondtofeaturesofdifferentnature. Thisexcludes
imagesorsignaldatasetswhereeachcolumncorrespondstothesamesignalondifferentsensors.
Nothighdimensional. Weonlykeepdatasetswithad/nratiobelow1/10.
Undocumenteddatasets Weremovedatasetswheretoolittleinformationisavailable. Wedidkeep
datasetswithhiddencolumnnamesifitwasclearthatthefeatureswereheterogeneous.
I.I.D.data. Weremovestream-likedatasetsortimeseries.
Real-worlddata. Weremoveartificialdatasetsbutkeepsomesimulateddatasets. Thedifferenceis
subtle,butwetrytokeepsimulateddatasetsiflearningthesedatasetsareofpracticalimportance
(liketheHiggsdataset),andnotjustatoyexampletotestspecificmodelcapabilities.
Nottoosmall. Weremovedatasetswithtoofewfeatures(<4)andtoofewsamples(<3000). For
benchmarksonnumericalfeaturesonly,weremovecategoricalfeaturesbeforecheckingifenough
featuresandsamplesareremaining.
Nottooeasy. Weremovedatasetswhicharetooeasy. Specifically,weremoveadatasetifadefault
LogisticRegression(orLinearRegressionforregression)reachascorewhoserelativedifference
withthe score ofboth adefault Resnet(from Gorishniyet al. [2021])and adefault HistGradi-
entBoostingmodel(fromscikitlearn)isbelow5%. Otherbenchmarksusedifferentmetricsto
removetooeasydatasets,likeremovingdatasetswhichcanbelearntperfectlybyasingledecision
classifier[Bischletal.,2021],butthisdoesnotaccountfordifferentBayesrateofdifferentdatasets.
Astree-basedmethodshavebeenshowntobesuperiortoLogisticRegression[Fernández-Delgado
etal.,2014]inoursetting,aclosescoreforthesetwotypesofmodelsindicatesthatwemight
alreadybeclosetothebestachievablescore.
Notdeterministic. Weremovedatasetswherethetargetisadeterministicfunctionofthedata. This
mostlymeansremovingdatasetsongameslikepokerandchess. Indeed,webelievethatthese
datasetsareverydifferentfrommostreal-worldtabulardatasets,andshouldbestudiedseparately.
3.2 Removingsideissues
Tokeeplearningtasksashomogeneousaspossibleandfocusonchallengesspecifictotabulardata,
weexcludesubproblemswhichwoulddeservetheirownanalysis:
Medium-sizedtrainingset Wetruncatethetrainingsetto10,000samplesforbiggerdatasets. This
allowsustoinvestigatethemedium-sizeddatasetregime. Westudythelarge-sized(50,000)regime,
forwhichfewerdatasetsmatchingourcriteriaareavailable,inA.2.
Nomissingdata Weremoveallmissingdatafromthedatasets. Indeed,therearenumeroustech-
niquesforhandlingmissingdatabothfortree-basedmodelsandNNs,withvaryingperformances
[Perez-Lebeletal.,2022]. Inpractice,wefirstremovecolumnscontainingmanymissingdata,then
allrowscontainingatleastonemissingentry.
Balancedclasses Forclassification,thetargetisbinarisedifthereareseveralclasses,bytakingthe
twomostnumerousclasses,andwekeephalfofsamplesineachclass.
Lowcardinalitycategoricalfeatures Weremovecategoricalfeatureswithmorethan20items.
Highcardinalitynumericalfeatures Weremovenumericalfeatureswithlessthan10uniqueval-
ues. Numericalfeatureswith2uniquevaluesareconvertedtocategoricalfeatures.
3

3.3 Aproceduretobenchmarkmodelswithhyperparameterselection
Hyperparameter tuning leads to uncontrolled variance on a benchmark [Bouthillier et al., 2021],
especiallywithasmallbudgetofmodelevaluations.Wedesignabenchmarkingprocedurethatjointly
samples the variance of hyperparameter tuning and explores increasingly high budgets of model
evaluations. Itreliesonrandomsearchesforhyper-parametertuning[Bergstraetal.,2013]. Weuse
hyperparametersearchspacesfromtheHyperopt-SklearnKomeretal.[2014]whenavailable,from
theoriginalpaperwhenpossible,andfromGorishniyetal.[2021]forMLP,ResnetandXGBoost
(seeA.3). Werunarandomsearchof≈400iterationsperdataset,onCPUfortree-basedmodels
andGPUforNNs(moredetailsinA.3).
Tostudyperformanceasafunctionofthenumbernofrandomsearchiterations,wecomputethebest
hyperparametercombinationonthevalidationsetontheseniterations(foreachmodelanddataset),
andevaluateitonthetestset. Wedothis15timeswhileshufflingtherandomsearchorderateach
time. Thisgivesusbootstrap-likeestimatesoftheexpectedtestscoreofthebest(onthevalidation
set)modelaftereachnumberofrandomsearchiterations. Inaddition,wealwaysstarttherandom
searcheswiththedefaulthyperparametersofeachmodel.
Resuablecodeandbenchmarkrawdata Thecodeusedforalltheexperimentsandcomparisons
isavailableathttps://github.com/LeoGrin/tabular-benchmark. Tohelpresearcherstocheaplyadd
theirownalgorithmstotheresults,wealsoshareatthesamelinkadatatablecontainingresultsfor
alliterationsofour20,000compute-hourrandomsearches.
3.4 Aggregatingresultsacrossdatasets
Weusethetestsetaccuracy(classification)andR2score(regression)tomeasuremodelperformance.
Toaggregateresultsacrossdatasetsofvaryingdifficulty,weuseametricsimilartothedistanceto
theminimum(oraveragedistancetotheminimum(ADTM)whenaveragedacrossdatasets),used
inFeureretal.[2021]andintroducedinWistubaetal.[2015]. Thismetricconsistsinnormalizing
eachtestaccuracybetween0and1viaanaffinerenormalizationbetweenthetop-performingand
worse-performingmodels. Insteadoftheworse-performingmodel,weusemodelsachievingthe
10%(classification)or50%(regression)testerrorquantile. Indeed,theworsescoresareachievedby
outliermodelsandarenotrepresentativeofthedifficultyofthedataset. Forregressiontasks,weclip
allnegativescores(i.ebelow50%scores)to0toreducetheinfluenceofverylowscores.
3.5 Datapreparation
Westriveforaslittlemanualpreprocessingaspossible,applyingonlythefollowingtransformations:
Gaussianizedfeatures For NN training, the features are Gaussianized with Scikit-learn’s
QuantileTransformer.
Transformedregressiontargets Inregressionsettings,targetvariablesarelog-transformedwhen
theirdistributionsareheavy-tailed(e.ghouseprices,seeA.1). Inaddition,weaddasanhyperpa-
rameterthepossibilitytoGaussienizethetargetvariableformodelfit,andtransformitbackfor
evaluation(viaScikitLearn’sTransformedTargetRegressorandQuantileTransformer).
OneHotEncoder Formodelswhichdonothandlecategoricalvariablesnatively,weencodecategor-
icalfeaturesusingScikitLearn’sOneHotEncoder.
4 Tree-basedmodelsstilloutperformdeeplearningontabulardata.
4.1 Modelsbenchmarked
Fortree-basedmodels,wechoose3state-of-the-artmodelsusedbypractitioners: ScikitLearn’sRan-
domForest,GradientBoostingTrees(GBTs)(orHistGradientBoostingTreeswhenusingcategorical
features),andXGBoostChenandGuestrin[2016]. Webenchmarkthefollowingdeepmodels:
MLP : aclassicalMLPfromGorishniyetal.[2021]. TheonlyimprovementbeyondasimpleMLP
isusingPytorch’sReduceOnPlateaulearningratescheduler.
Resnet : asinGorishniyetal.[2021],similartoMLPwithdropout,batch/layernormalization,and
skipconnections.
4

Classification(15datasets) Regression(19datasets)
Figure 1: Benchmark on medium-sized datasets, with only numerical features. Dotted lines
correspondtothescoreofthedefaulthyperparameters,whichisalsothefirstrandomsearchiteration.
Each value correspondsto the testscore of thebest model (onthe validationset) after aspecific
numberofrandomsearchiterations,averagedon15shufflesoftherandomsearchorder. Theribbon
correspondstotheminimumandmaximumscoresonthese15shuffles.
Classification(7datasets) Regression(14datasets)
Figure2: Benchmarkonmedium-sizeddatasets,withbothnumericalandcategoricalfeatures.
Dottedlinescorrespondtothescoreofthedefaulthyperparameters,whichisalsothefirstrandom
searchiteration. Eachvaluecorrespondstothetestscoreofthebestmodel(onthevalidationset)
afteraspecificnumberofrandomsearchiterations,averagedon15shufflesoftherandomsearch
order. Theribboncorrespondstotheminimumandmaximumscoresonthese15shuffles.
FT_Transformer : asimpleTransformermodelcombinedwithamoduleembeddingcategorical
andnumericalfeatures,createdinGorishniyetal.[2021]. Wechoosethismodelbecauseitwas
benchmarkedinaconvincingwayagainsttree-basedmodelsandothertabular-specificmodels. It
canthusbeconsidereda“bestcase”forDeeplearningmodelsontabulardata.
SAINT :aTransformermodelwithanembeddingmoduleandaninter-samplesattentionmechanism,
proposedinSomepallietal.[2021]. Weincludethismodelbecauseitwasthebestperforming
deepmodelinBorisovetal.[2021],andtoinvestigatetheimpactofinter-sampleattention,which
performswellontabulardataaccordingtoKossenetal.[2022].
4.2 Results
Fig. 1and2givebenchmarkresultsfordifferenttypesofdatasets(appendixA.2givesresultsasa
functionofcomputationtime).
5

Figure 3: Normalized test accuracy of
differentmodelsforvaryingsmoothing
of the target function on the train set.
We smooth the target function through a
GaussianKernelsmoother,whosecovari-
ancematrixisthedatacovariance,multi-
plied by the (squared) lengthscale of the
Gaussiankernelsmoother. Alengthscale
of0correspondstonosmoothing(theorig-
inaldata). AllfeatureshavebeenGaussi-
enizedbeforethesmoothingthroughScik-
itLearn’sQuantileTransformer. Thebox-
plotsrepresentthedistributionofnormal-
izedaccuraciesacross15re-orderingsof
therandomsearch.
TuninghyperparametersdoesnotmakeNNsstate-of-the-art Tree-basedmodelsaresuperior
for every random search budget, and the performance gap stays wide even after a large number
ofrandomsearchiterations. Thisdoesnottakeintoaccountthateachrandomsearchiterationis
generallyslowerforNNsthanfortree-basedmodels(seeA.2).
CategoricalvariablesarenotthemainweaknessofNNs Categoricalvariablesareoftenseen
asamajorproblemforusingNNsontabulardata[Borisovetal.,2021]. Ourresultsonnumerical
variablesonlydorevealanarrowergapbetweentree-basedmodelsandNNsthanincludingcategorical
variables. Still,mostofthisgapsubsistswhenlearningonnumericalfeaturesonly.
5 Empiricalinvestigation: whydotree-basedmodelsstilloutperformdeep
learningontabulardata?
5.1 Methodology: uncoveringinductivebiases
WehaveseeninSec. 4.2thattree-basedmodelsbeatNNsacrossawiderangeofhyperparameter
choices. This hints to inherent properties of these models which explains their performances on
tabular data. Indeed, the best methods on tabular data share two attributes: they are ensemble
methods,bagging(RandomForest)orboosting(XGBoost,GBTs),andtheweaklearnerusedin
theseensemblesisadecisiontree. Thedecisivepointseemstobethetreeaspect: otherboostingand
baggingmethodswithdifferentweaklearnersexistbutarenotcommonlyusedfortabulardata. In
thissection,wetrytounderstandtheinductivebiasesofdecisiontreesthatmakethemwell-suitedfor
tabulardata,andhowtheydifferfromtheinductivebiasesofNNs. Thisisequivalenttosayingthe
reverse: whichfeaturesoftabulardatamakethistypeofdataeasytolearnwithtree-basedmethods
yetmoredifficultwithaNN?
Tothisaim,weapplyvarioustransformationstotabulardatasetswhicheithernarroworwidenthe
generalizationperformancegapbetweenNNsandtree-basedmodels,andthushelpusemphasizetheir
differentinductivebiases. Forthesakeofsimplicity,werestrictouranalysistonumericalvariables
andclassificationtasksonmedium-sizeddatasets. Resultsarepresentedaggregatedacrossdatasets,
anddataset-specificresultsareavailableinA.4,alongwithadditionaldetailsonourexperiments.
5.2 Finding1: NNsarebiasedtooverlysmoothsolutions
Wetransformeachtrain setbysmoothingtheoutputwithaGaussianKernelsmootherforvarying
length-scalevaluesofthekernel(moredetailsareavailableinA.4). Thiseffectivelypreventsmodels
fromlearningirregularpatternsofthetargetfunction. Fig. 3showsmodelperformanceasafunction
ofthelength-scaleofthesmoothingkernel. Forsmalllengthscales,smoothingthetargetfunctionon
thetrainsetdecreasesmarkedlytheaccuracyoftree-basedmodels,butbarelyimpactsthatofNNs.
6

Suchresultssuggestthatthetargetfunctionsinourdatasetsarenotsmooth,andthatNNsstruggleto
fittheseirregularfunctionscomparedtotree-basedmodels. ThisisinlinewithRahamanetal.[2019],
whichfindsthatNNsarebiasedtowardlow-frequencyfunctions. Modelsbasedondecisiontrees,
whichlearnpiece-wiseconstantfunctions,donotexhibitsuchabias. Ourfindingsdonotcontradict
papersclaimingbenefitsfromregularizationfortabulardata[ShavittandSegal,2018,Borisovetal.,
2021,Kadraetal.,2021b,Lounicietal.,2021],asadequateregularizationandcarefuloptimization
mayallowNNstolearnirregularpatterns. InA.4,weshowsomeexamplesofnon-smoothpatterns
whichneuralnetworksfailtolearn,bothintoyandreal-worldsettings.
Note also that our observation could also explain the benefits of the ExU activation used in the
Neural-GAMpaper[Agarwaletal.,2021],andoftheembeddingsusedinGorishniyetal.[2022]:
theperiodicembeddingmighthelpthemodeltolearnthehigh-frequencypartofthetargetfunction,
andthetarget-awarebinningmightmakethetargetfunctionsmoother.
5.3 Finding2: UninformativefeaturesaffectmoreMLP-likeNNs
Tabulardatasetscontainmanyuninformativefeatures Foreachdataset,wedropanincreasingly
largefractionoffeatures,accordingtofeatureimportance(rankedbyaRandomForest). Fig. 4shows
thattheclassificationaccuracyofaGBTisnotmuchaffectedbyremovinguptohalfofthefeatures.
Furthermore,thetestaccuracyofaGBTtrainedontheremovedfeatures(i.ethefeaturesbelowa
certainfeatureimportancethreshold)isverylowupto20%offeaturesremoved,andquitelowuntil
50%,whichsuggeststhatmostofthesefeaturesareuninformative,andnotsolelyredundant.
MLP-likearchitecturesarenotrobusttouninformativefeatures Inthetwoexperimentsshown
in Fig. 5, we can see that removing uninformative features (5a) reduces the performance gap
between MLPs (Resnet) and the other models (FT Transformers and tree-based models), while
addinguninformativefeatureswidensthegap. ThisshowsthatMLPsarelessrobusttouninformative
features,and,giventhefrequencyofsuchfeaturesintabulardatasets,partlyexplaintheresultsfrom
Sec. 4.2.
In Fig. 5a, we also remove informative features as we remove a larger fraction of features. Our
reasoning,whichisbackedby5b,isthatthedecreaseinaccuracyduetotheremovalofthesefeatures
iscompensatedbytheremovalofuninformativefeatures,whichismorehelpfulforMLPsthanfor
othermodels(wealsoremoveredundantfeaturesatthesametime, whichshouldnotimpactour
models)
5.4 Finding3: Dataarenoninvariantbyrotation,soshouldbelearningprocedures
WhyareMLPsmuchmorehinderedbyuninformativefeatures,comparedtoothermodels? One
answeristhatthislearnerisrotationallyinvariantinthesenseofNg[2004]: thelearningprocedure
whichlearnsanMLPonatrainingsetandevaluateitonatestingsetisunchangedwhenapplyinga
rotation(unitarymatrix)tothefeaturesonboththetrainingandtestingset. Indeed,Ng[2004]shows
thatanyrotationalllyinvariantlearningprocedurehasaworst-casesamplecomplexitythatgrowsat
leastlinearlyinthenumberofirrelevantfeatures. Intuitively,toremoveuninformativefeatures,a
rotationalyinvariantalgorithmhastofirstfindtheoriginalorientationofthefeatures,andthenselect
theleastinformativeones: theinformationcontainedintheorientationofthedataislost.
Fig. 6a,whichshowsthechangeintestaccuracywhenrandomlyrotatingourdatasets,confirms
thatonlyResnetsarerotationallyinvariant. Morestriking,randomrotationsreversetheperformance
order: NNsarenowabovetree-basedmodelsandResnetsaboveFTTransformers. Thissuggeststhat
rotationinvarianceisnotdesirable: similarlytovision[Krizhevskyetal.,2012],thereisanatural
basis(here,theoriginalbasis)whichencodesbestdata-biases,andwhichcannotberecoveredby
modelsinvarianttorotationswhichpotentiallymixesfeatureswithverydifferentstatisticalproperties.
Indeed, features of a tabular data typically carry meanings individually, as expressed by column
names: age,weight. Thelinkwithuninformativefeaturesisapparentin6b: removingtheleast
importanthalfofthefeaturesineachdataset(beforerotating),dropstheperformanceofallmodels
exceptResnets,butthedecreaseislesssignificantthanwhenusingallfeatures.
OurfindingsshedlightontheresultsofSomepallietal.[2021]andGorishniyetal.[2022],whichadd
anembeddinglayer,evenfornumericalfeatures,beforeMLPorTransformermodels. Indeed,this
7

Figure 4: Test accuracy of a GBT
for varying proportions of removed fea-
tures,onourclassificationbenchmarkon
numericalfeatures. Featuresareremoved
in increasing order of feature importance
(computedwithaRandomForest),andthe
twolinescorrespondtotheaccuracyusing
the(mostimportant)keptfeatures(blue)or
the(leastimportant)removedfeatures(red).
Ascoreof1.0correspondstothebestscore
acrossallmodelsandhyperparameterson
eachdataset,and0.0correspondtorandom
chance. Thesescoresareaveragedacross
30randomsearchorders, andtheribbons
correspondtothe80%intervalamongthe
differentdatasets.
a. Removingfeatures b. Addingfeatures
Figure5: Testaccuracychangeswhenremoving(a)oradding(b)uninformativefeatures. Fea-
turesareremovedinincreasingorderoffeatureimportance(computedwithaRandomForest).Added
featuresaresampledfromstandardGaussiansuncorrelatedwiththetargetandwithotherfeatures.
Scoresareaveragedacrossdatasets,andtheribbonscorrespondtotheminimumandmaximumscore
amongthe30differentrandomsearchreorders(startingwiththedefaultmodels).
layerbreaksrotationinvariance. Thefactthatverydifferenttypesofembeddingsseemtoimprove
performancesuggeststhatthesheerpresenceofanembeddingwhichbreakstheinvarianceisakey
partoftheseimprovements. Wenotethatapromisingavenueforfurtherresearchwouldbetofind
otherwaystobreakrotationinvariancewhichmightbelesscomputationallycostlythanembeddings.
6 Discussionandconclusion
Limitation Our study leaves open questions for future work: which other inductive biases of
tree-basedmodelsexplaintheirperformancesontabulardata? Howwouldourevaluationchangeon
verysmalldatasets? Onverylargedatasets? Whatisthebestwaytohandlespecificchallengeslike
missingdataorhigh-cardinalitycategoricalfeatures,forNNsandtree-basedmodels? Withthesebest
methods,howwouldtheevaluationchangeincludingmissingdata?
Conclusion Whileeachpublicationonlearningarchitecturesfortabulardatacomestodifferent
resultsusingadifferentbenchmarkingmethodology,oursystematicbenchmark,goingbeyondthe
specificitiesofahandfulofdatasetsandaccountingforhyper-parameterchoice,revealscleartrends.
Onsuchdata,tree-basedmodelsmoreeasilyyieldgoodpredictions,withmuchlesscomputational
8

a. Withallfeatures b. With50%featuresremoved
Figure6: Normalizedtestaccuracyofdifferentmodelswhenrandomlyrotatingourdatasets.
Here,theclassificationbenchmarkonnumericalfeatureswasused. AllfeaturesareGaussianized
before the random rotations. The scores are averaged across datasets, and the boxes depict the
distributionacrossrandomsearchshuffles. Right: thefeaturesareremovedbeforedatarotation.
cost. Thissuperiorityisexplainedbyspecificfeaturesoftabulardata: irregularpatternsinthetarget
function,uninformativefeatures,andnonrotationally-invariantdatawherelinearcombinationsof
featuresmisrepresenttheinformation.Beyondtheseconclusions,ourbenchmarkisreusable,allowing
researcherstouseourmethodologyanddatasetsfornewarchitectures,andtoeasilycomparethemto
thoseweexploredviathesharedbenchmarkrawresults. Wehopethatthisbenchmarkwillstimulate
tabulardeep-learningresearchandfostermorethoroughempiricalevaluationofcontributions.
AcknowledgmentsandDisclosureofFunding
GVandLGacknowledgesupportinpartbytheFrenchAgenceNationaledelaRechercheunderGrant
ANR-20-CHIA-0026(LearnI).EOwassupportedbytheProjectANR-21-CE23-0030ADONISand
EMERG-ADONISfromAllianceSU.
References
StateofDataScienceandMachineLearning2021. https://www.kaggle.com/kaggle-survey-2021.
Jannik Kossen, Neil Band, Clare Lyle, Aidan N. Gomez, Tom Rainforth, and Yarin Gal. Self-
AttentionBetweenDatapoints: GoingBeyondIndividualInput-OutputPairsinDeepLearning.
arXiv:2106.02584[cs,stat],June2021.
YuryGorishniy,IvanRubachev,ValentinKhrulkov,andArtemBabenko. RevisitingDeepLearning
ModelsforTabularData. arXiv:2106.11959[cs],June2021.
Ravid Shwartz-Ziv and Amitai Armon. Tabular Data: Deep Learning is Not All You Need.
arXiv:2106.03253[cs],June2021.
ImageNet: Alarge-scalehierarchicalimagedatabase|IEEEConferencePublication|IEEEXplore.
https://ieeexplore.ieee.org/document/5206848.
ZacharyC.LiptonandJacobSteinhardt. TroublingTrendsinMachineLearningScholarship: Some
MLpaperssufferfromflawsthatcouldmisleadthepublicandstymiefutureresearch. Queue,17
(1):Pages80:45–Pages80:77,February2019. ISSN1542-7730. doi: 10.1145/3317287.3328534.
XavierBouthillier,PierreDelaunay,MirkoBronzi,AssyaTrofimov,BrennanNichyporuk,Justin
Szeto, NazaninMohammadiSepahvand, EdwardRaff, KanikaMadan, VikramVoleti, Samira
EbrahimiKahou,VincentMichalski,TalArbel,ChrisPal,GaelVaroquaux,andPascalVincent.
AccountingforVarianceinMachineLearningBenchmarks. ProceedingsofMachineLearning
andSystems,3:747–769,March2021.
9

JoaquinVanschoren,JanN.vanRijn,BerndBischl,andLuisTorgo. OpenML:Networkedscience
in machine learning. ACM SIGKDD Explorations Newsletter, 15(2):49–60, June 2014. ISSN
1931-0145,1931-0153. doi: 10.1145/2641190.2641198.
VadimBorisov,TobiasLeemann,KathrinSeßler,JohannesHaug,MartinPawelczyk,andGjergji
Kasneci. DeepNeuralNetworksandTabularData: ASurvey. arXiv:2110.01889[cs],October
2021.
JohnT.HancockandTaghiM.Khoshgoftaar. Surveyoncategoricaldataforneuralnetworks. Journal
ofBigData,7(1):28,April2020. ISSN2196-1115. doi: 10.1186/s40537-020-00305-w.
Jinsung Yoon, Yao Zhang, James Jordon, and Mihaela van der Schaar. VIME: Extending
the Success of Self- and Semi-supervised Learning to Tabular Domain. In Advances in
NeuralInformationProcessingSystems,volume33,pages11033–11043.CurranAssociates,Inc.,
2020.
NathanLay,AdamP.Harrison,SharonSchreiber,GiteshDawer,andAdrianBarbu. RandomHinge
ForestforDifferentiableLearning. arXiv:1802.03882[cs,stat],March2018.
SergeiPopov,S.Morozov,andArtemBabenko. NeuralObliviousDecisionEnsemblesforDeep
LearningonTabularData. undefined,2020.
AmiAbutbul,GalElidan,LiranKatzir,andRanEl-Yaniv. DNF-Net: ANeuralArchitecturefor
TabularData,June2020.
ThomasM.Hehn,JulianF.P.Kooij,andF.Hamprecht. End-to-EndLearningofDecisionTreesand
Forests. undefined,2019.
RyutaroTanno,KaiArulkumaran,D.Alexander,A.Criminisi,andA.Nori. AdaptiveNeuralTrees.
undefined,2019.
Y.Chen. Attentionaugmenteddifferentiableforestfortabulardata. undefined,2020.
Peter Kontschieder, Madalina Fiterau, Antonio Criminisi, and Samuel Rota Bulo. Deep Neural
Decision Forests. In 2015 IEEEInternationalConference on ComputerVision (ICCV), pages
1467–1475,Santiago,Chile,December2015.IEEE. ISBN978-1-4673-8391-2. doi: 10.1109/
ICCV.2015.172.
I.D.Rodriguez,TaylorW.Killian,Sung-HyunSon,andM.Gombolay. InterpretableReinforcement
LearningviaDifferentiableDecisionTrees. undefined,2019.
HuifengGuo,RuimingTang,YunmingYe,ZhenguoLi,andXiuqiangHe. DeepFM:AFactorization-
MachinebasedNeuralNetworkforCTRPrediction,March2017.
GowthamiSomepalli,MicahGoldblum,AviSchwarzschild,C.BayanBruss,andTomGoldstein.
SAINT: Improved Neural Networks for Tabular Data via Row Attention and Contrastive Pre-
Training. arXiv:2106.01342[cs,stat],June2021.
SercanÖArikandTomasPfister. TabNet: AttentiveInterpretableTabularLearning. undefined,2019.
XinHuang, AshishKhetan, MilanCvitkovic, andZoharKarnin. TabTransformer: TabularData
ModelingUsingContextualEmbeddings. arXiv:2012.06678[cs],December2020.
KarimLounici,KatiaMeziani,andBenjaminRiu. MuddlingLabelRegularization: DeepLearning
forTabularDatasets. arXiv:2106.04462[cs],June2021.
IraShavittandEranSegal. RegularizationLearningNetworks: DeepLearningforTabularDatasets.
arXiv:1805.06440[cs,stat],October2018.
ArlindKadra,MariusLindauer,FrankHutter,andJosifGrabocka. Well-tunedSimpleNetsExcelon
TabularDatasets,November2021a.
JamesFiedler. SimpleModificationstoImproveTabularNeuralNetworks. arXiv:2108.03214[cs],
August2021.
10

ManuelFernández-Delgado,EvaCernadas,SenénBarro,andDinaniAmorim.DoweNeedHundreds
ofClassifierstoSolveRealWorldClassificationProblems? JournalofMachineLearningResearch,
15(90):3133–3181,2014. ISSN1533-7928.
SherifSakr,RadwaElshawi,AmjadM.Ahmed,WaqasT.Qureshi,ClintonA.Brawner,StevenJ.
Keteyian,MichaelJ.Blaha,andMouazH.Al-Mallah. Comparisonofmachinelearningtechniques
topredictall-causemortalityusingfitnessdata: TheHenryfordexercIsetesting(FIT)project.
BMCMedicalInformaticsandDecisionMaking,17(1):174,December2017. ISSN1472-6947.
doi: 10.1186/s12911-017-0566-6.
AlexandruKorotcov, ValeryTkachenko, DanielP.Russo, andSeanEkins. ComparisonofDeep
LearningWithMultipleMachineLearningMethodsandMetricsUsingDiverseDrugDiscovery
DataSets. https://pubs.acs.org/doi/pdf/10.1021/acs.molpharmaceut.7b00578,November2017.
ShahadatUddin,ArifKhan,MdEkramulHossain,andMohammadAliMoni. Comparingdifferent
supervisedmachinelearningalgorithmsfordiseaseprediction. BMCMedicalInformaticsand
DecisionMaking,19(1):281,December2019.ISSN1472-6947.doi:10.1186/s12911-019-1004-8.
VadimBorisov,TobiasLeemann,KathrinSeßler,JohannesHaug,MartinPawelczyk,andGjergji
Kasneci. DeepNeuralNetworksandTabularData: ASurvey. arXiv:2110.01889[cs],February
2022.
AlexWang,YadaPruksachatkun,NikitaNangia,AmanpreetSingh,JulianMichael,FelixHill,Omer
Levy,andSamuelR.Bowman.SuperGLUE:AStickierBenchmarkforGeneral-PurposeLanguage
UnderstandingSystems,February2020.
BerndBischl,GiuseppeCasalicchio,MatthiasFeurer,PieterGijsbers,FrankHutter,MichelLang,
RafaelG.Mantovani,JanN.vanRijn,andJoaquinVanschoren. OpenMLBenchmarkingSuites,
November2021.
PieterGijsbers,ErinLeDell,JanekThomas,SébastienPoirier,BerndBischl,andJoaquinVanschoren.
AnOpenSourceAutoMLBenchmark,July2019.
GünterKlambauer, ThomasUnterthiner, AndreasMayr, andSeppHochreiter. Self-Normalizing
NeuralNetworks. arXiv:1706.02515[cs,stat],September2017.
AlexandrePerez-Lebel,GaëlVaroquaux,MarineLeMorvan,JulieJosse,andJean-BaptistePoline.
Benchmarkingmissing-valuesapproachesforpredictivemodelsonhealthdatabases. GigaScience,
11:giac013,January2022. ISSN2047-217X. doi: 10.1093/gigascience/giac013.
JBergstra,DYamins,andD.DCox. MakingaScienceofModelSearch: HyperparameterOptimiza-
tioninHundredsofDimensionsforVisionArchitectures. 2013.
BrentKomer,JamesBergstra,andChrisEliasmith. Hyperopt-Sklearn: AutomaticHyperparameter
ConfigurationforScikit-Learn. In PythoninScienceConference, pages32–37, Austin, Texas,
2014. doi: 10.25080/Majora-14bd3278-006.
MatthiasFeurer,KatharinaEggensperger,StefanFalkner,MariusLindauer,andFrankHutter. Auto-
Sklearn2.0: Hands-freeAutoMLviaMeta-Learning,September2021.
MartinWistuba,NicolasSchilling,andLarsSchmidt-Thieme. Learninghyperparameteroptimization
initializations. In2015IEEEInternationalConferenceonDataScienceandAdvancedAnalytics
(DSAA),pages1–10,October2015. doi: 10.1109/DSAA.2015.7344817.
Tianqi Chen and Carlos Guestrin. XGBoost: A Scalable Tree Boosting System. In Proceedings
ofthe22ndACMSIGKDDInternationalConferenceonKnowledgeDiscoveryandDataMining,
pages785–794,August2016. doi: 10.1145/2939672.2939785.
JannikKossen,NeilBand,ClareLyle,AidanN.Gomez,TomRainforth,andYarinGal.Self-Attention
BetweenDatapoints: GoingBeyondIndividualInput-OutputPairsinDeepLearning,February
2022.
Nasim Rahaman, Aristide Baratin, Devansh Arpit, Felix Draxler, Min Lin, Fred A. Hamprecht,
YoshuaBengio,andAaronCourville. OntheSpectralBiasofNeuralNetworks,May2019.
11

ArlindKadra,MariusLindauer,FrankHutter,andJosifGrabocka. RegularizationisallyouNeed:
SimpleNeuralNetscanExcelonTabularData. arXiv:2106.11189[cs],June2021b.
RishabhAgarwal,LeviMelnick,NicholasFrosst,XuezhouZhang,BenLengerich,RichCaruana,
andGeoffreyHinton. NeuralAdditiveModels: InterpretableMachineLearningwithNeuralNets,
October2021.
YuryGorishniy,IvanRubachev,andArtemBabenko. OnEmbeddingsforNumericalFeaturesin
TabularDeepLearning. arXiv:2203.05556[cs],March2022.
AndrewY.Ng.Featureselection,L vs.L regularization,androtationalinvariance.InTwenty-First
1 2
International Conference on Machine Learning - ICML ’04, page 78, Banff, Alberta, Canada,
2004.ACMPress. doi: 10.1145/1015330.1015435.
AlexKrizhevsky,IlyaSutskever,andGeoffreyEHinton. Imagenetclassificationwithdeepconvolu-
tionalneuralnetworks. Advancesinneuralinformationprocessingsystems,25,2012.
LukasBiewald. ExperimentTrackingwithWeightsandBiases,2020.
PauliVirtanen,RalfGommers,TravisE.Oliphant,MattHaberland,TylerReddy,DavidCournapeau,
Evgeni Burovski, Pearu Peterson, Warren Weckesser, Jonathan Bright, Stéfan J. van der Walt,
MatthewBrett,JoshuaWilson,K.JarrodMillman,NikolayMayorov,AndrewR.J.Nelson,Eric
Jones,RobertKern,EricLarson,CJCarey,˙IlhanPolat,YuFeng,EricW.Moore,JakeVanderPlas,
DenisLaxalde,JosefPerktold,RobertCimrman,IanHenriksen,E.A.Quintero,CharlesR.Harris,
AnneM.Archibald,AntônioH.Ribeiro,FabianPedregosa,PaulvanMulbregt,andSciPy1.0
Contributors. SciPy1.0: FundamentalAlgorithmsforScientificComputinginPython. Nature
Methods,17:261–272,2020. doi: 10.1038/s41592-019-0686-2.
12

A Appendix
A.1 Datasetsused
We describe below all datasets used in our benchmarks, along with the link to the origi-
nal dataset, as well as a new OpenML link to the transformed datasets used for our bench-
marks. All datasets considered for the benchmarks, as well as the reason for their selec-
tion or their exclusion, are available at this link: https://docs.google.com/spreadsheets/
d/1Mgh27upycFcd3B6uA7YJyB9Pd4Y3UuY1gBfI02EZUGM/edit?usp=sharing. Instructionson
howtousethesedatasetstobenchmarkyourownalgorithmsareavailableatA.7.
A.1.1 Numericalclassification
OpenML benchmark: https://www.openml.org/search?type=benchmark&study_type=
task&sort=tasks_included&id=298
dataset_name n_samples n_features originallink newlink
electricity 38474 7 https://openml.org/d/151 https://www.openml.org/d/44120
covertype 566602 10 https://openml.org/d/293 https://www.openml.org/d/44121
pol 10082 26 https://openml.org/d/722 https://www.openml.org/d/44122
house_16H 13488 16 https://openml.org/d/821 https://www.openml.org/d/44123
kdd_ipums_la_97-small 5188 20 https://openml.org/d/993 https://www.openml.org/d/44124
MagicTelescope 13376 10 https://openml.org/d/1120 https://www.openml.org/d/44125
bank-marketing 10578 7 https://openml.org/d/1461 https://www.openml.org/d/44126
phoneme 3172 5 https://openml.org/d/1489 https://www.openml.org/d/44127
MiniBooNE 72998 50 https://openml.org/d/41150 https://www.openml.org/d/44128
Higgs 940160 24 https://openml.org/d/42769 https://www.openml.org/d/44129
eye_movements 7608 20 https://openml.org/d/1044 https://www.openml.org/d/44130
jannis 57580 54 https://openml.org/d/41168 https://www.openml.org/d/44131
credit 16714 10 https://www.kaggle.com/c/GiveMeSomeCredit/data?select=cs-training.csv https://www.openml.org/d/44089
california 20634 8 https://www.dcc.fc.up.pt/ltorgo/Regression/cal_housing.html https://www.openml.org/d/44090
wine 2554 11 https://archive.ics.uci.edu/ml/datasets/wine+quality https://www.openml.org/d/44091
Notethatwenoticedabitlatethatthenumberofsamplesinthetransformedwinedatasetwasjust
belowourthreshold,anddecidedtokeepit.
A.1.2 Numericalregression
OpenML benchmark: https://www.openml.org/search?type=benchmark&study_type=
task&sort=tasks_included&id=297
dataset_name n_samples n_features originallink newlink
cpu_act 8192 21 https://openml.org/d/197 https://www.openml.org/d/44132
pol 15000 26 https://openml.org/d/201 https://www.openml.org/d/44133
elevators 16599 16 https://openml.org/d/216 https://www.openml.org/d/44134
isolet 7797 613 https://openml.org/d/300 https://www.openml.org/d/44135
wine_quality 6497 11 https://openml.org/d/287 https://www.openml.org/d/44136
Ailerons 13750 33 https://openml.org/d/296 https://www.openml.org/d/44137
houses 20640 8 https://openml.org/d/537 https://www.openml.org/d/44138
house_16H 22784 16 https://openml.org/d/574 https://www.openml.org/d/44139
diamonds 53940 6 https://openml.org/d/42225 https://www.openml.org/d/44140
Brazilian_houses 10692 8 https://openml.org/d/42688 https://www.openml.org/d/44141
Bike_Sharing_Demand 17379 6 https://openml.org/d/42712 https://www.openml.org/d/44142
nyc-taxi-green-dec-2016 581835 9 https://openml.org/d/42729 https://www.openml.org/d/44143
house_sales 21613 15 https://openml.org/d/42731 https://www.openml.org/d/44144
sulfur 10081 6 https://openml.org/d/23515 https://www.openml.org/d/44145
medical_charges 163065 5 https://openml.org/d/42720 https://www.openml.org/d/44146
MiamiHousing2016 13932 14 https://openml.org/d/43093 https://www.openml.org/d/44147
superconduct 21263 79 https://openml.org/d/43174 https://www.openml.org/d/44148
california 20640 8 https://www.dcc.fc.up.pt/ltorgo/Regression/cal_housing.html https://www.openml.org/d/44025
fifa 18063 5 https://www.kaggle.com/datasets/stefanoleone992/fifa-22-complete-player-dataset https://www.openml.org/d/44026
year 515345 90 https://archive.ics.uci.edu/ml/datasets/yearpredictionmsd https://www.openml.org/d/44027
A.1.3 Categoricalclassification
OpenML benchmark: https://www.openml.org/search?type=benchmark&sort=date&
study_type=task&id=300
13

dataset_name n_samples n_features Originallink Newlink
electricity 38474 8 https://openml.org/d/151 https://www.openml.org/d/44156
eye_movements 7608 23 https://openml.org/d/1044 https://www.openml.org/d/44157
KDDCup09_upselling 5032 45 https://openml.org/d/1114 https://www.openml.org/d/44158
covertype 423680 54 https://openml.org/d/1596 https://www.openml.org/d/44159
rl 4970 12 https://openml.org/d/41160 https://www.openml.org/d/44160
road-safety 111762 32 https://openml.org/d/42803 https://www.openml.org/d/44161
compass 16644 17 https://www.kaggle.com/datasets/danofer/compass?select=cox-violent-parsed.csv https://www.openml.org/d/44162
A.1.4 Categoricalregression
OpenML benchmark: https://www.openml.org/search?type=benchmark&study_type=
task&sort=tasks_included&id=299
dataset_name n_features n_samples Originallink Newlink
yprop_4_1 62 8885 https://openml.org/d/416 https://www.openml.org/d/44054
analcatdata_supreme 7 4052 https://openml.org/d/504 https://www.openml.org/d/44055
visualizing_soil 4 8641 https://openml.org/d/688 https://www.openml.org/d/44056
black_friday 9 166821 https://openml.org/d/41540 https://www.openml.org/d/44057
diamonds 9 53940 https://openml.org/d/42225 https://www.openml.org/d/44059
Mercedes_Benz_Greener_Manufacturing 359 4209 https://openml.org/d/42570 https://www.openml.org/d/44061
Brazilian_houses 11 10692 https://openml.org/d/42688 https://www.openml.org/d/44062
Bike_Sharing_Demand 11 17379 https://openml.org/d/42712 https://www.openml.org/d/44063
OnlineNewsPopularity 59 39644 https://openml.org/d/42724 https://www.openml.org/d/44064
nyc-taxi-green-dec-2016 16 581835 https://openml.org/d/42729 https://www.openml.org/d/44065
house_sales 17 21613 https://openml.org/d/42731 https://www.openml.org/d/44066
particulate-matter-ukair-2017 6 394299 https://openml.org/d/42207 https://www.openml.org/d/44068
SGEMM_GPU_kernel_performance 9 241600 https://openml.org/d/43144 https://www.openml.org/d/44069
A.2 Morebenchmarks
A.2.1 Resultsasafunctionofrandomsearchtime
InFigure7andFigure8,wepresentthesameresultsthatinsection4.2,butasafunctionofrandom
searchtimeinsteadofrandomsearchiterations.
Details Evaluationandtrainingtimeareadded. Timeisaveragedamongfolds,andcumulative
timespentonrandomsearchisbinnedinto20bins. DeeplearningmodelsarerunonGPUs,and
tree-based models on CPUs (see A.3). We present this comparison to give a rough sense of the
speeddifferencebetweentree-basedmodelsandneuralnetworks,butthisshouldnotbeconsidereda
rigorouscomparisonofthespeedofdifferentmodels,asweusedifferenttypesofGPUsandCPUs.
Results Looking at the results as a function of random search time rather than random search
iterationsmakestree-basedmodelssuperiorityevenmorestriking. Neuralnetworksandtree-based
modelswerecloseforsomebenchmarksafterasmallnumberofiterations,butforthesameamount
oftimespentonrandomsearch,tree-basedmodelsscoresarealwayshighaboveneuralnetworks.
14

Classification(15datasets) Regression(18datasets)
Figure7: Timebenchmarkonmedium-sizeddatasets,withonlynumericalfeatures. Thefirst
random search iteration corresponds to default hyperparameters. Each value corresponds to the
testscoreofthebestmodel(onthevalidationset)afteraspecifictimespentdoingrandomsearch,
averagedon15shufflesoftherandomsearchorder. Theribboncorrespondstotheminimumand
maximumscoresonthese15shuffles.
Classification(7datasets) Regression(14datasets)
Figure 8: Time benchmark on medium-sized datasets, with both numerical and categorical
features. The first random search iteration corresponds to default hyperparameters. Each value
correspondstothetestscoreofthebestmodel(onthevalidationset)afteraspecifictimespentdoing
randomsearch,averagedon15shufflesoftherandomsearchorder. Theribboncorrespondstothe
minimumandmaximumscoresonthese15shuffles.
15

A.2.2 Large-sizeddatasets
Weextendourbenchmarktolarge-scaledatasets: inFigures9,10,11and12,wecomparetheresults
ofourmodelsonthesamesetofdatasets,inlarge-size(trainsettruncatedto50,000samples)and
medium-size(trainsettruncatedto10,000samples)settings.
Weonlykeepdatasetswithmorethan50,000samplesandrestrictthetrainsetsizeto50,000samples
(vs10,000samplesforthemedium-sizedbenchmark). Unfortunately,thisexcludesalotofdatasets,
whichmakesthecomparisonlessclear. However,itseemsthat,inmostcases,increasingthetrainset
sizereducesthegapbetweenneuralnetworksandtree-basedmodels. Weleavearigorousstudyof
thistrendtofuturework.
16

Mediumsizedtrainset Largesizedtrainset
Figure9: Comparisonofaccuracieson4classificationtasksfordifferenttrainsetsizes, with
onlynumericalfeatures. Onlydatasetswithmorethan50,000sampleswerekept, andthetrain
setsizewastruncatedtoeither10,000samplesor50,000samples. Dottedlinescorrespondtothe
scoreofthedefaulthyperparameters, whichisalsothefirstrandomsearchiteration. Eachvalue
corresponds to the test score of the best model (on the validation set) after a specific number of
randomsearchiterations,averagedon15shufflesoftherandomsearchorder. Theribboncorresponds
totheminimumandmaximumscoresonthese15shuffles.
Mediumsizedtrainset Largesizedtrainset
Figure10: ComparisonofR2scoreson3regressiontasksfordifferenttrainsetsizes,withonly
numericalfeatures. Onlydatasetswithmorethan50,000sampleswerekept,andthetrainsetsize
wastruncatedtoeither10,000samplesor50,000samples. Dottedlinescorrespondtothescoreofthe
defaulthyperparameters,whichisalsothefirstrandomsearchiteration.Eachvaluecorrespondstothe
testscoreofthebestmodel(onthevalidationset)afteraspecificnumberofrandomsearchiterations,
averagedon15shufflesoftherandomsearchorder. Theribboncorrespondstotheminimumand
maximumscoresonthese15shuffles.
17

Mediumsizedtrainset Largesizedtrainset
Figure11: Comparisonofaccuracieson2classificationtasksfordifferenttrainsetsizes,with
both numerical and categorical features. Only datasets with more than 50,000 samples were
kept,andthetrainsetsizewastruncatedtoeither10,000samplesor50,000samples. Dottedlines
correspondtothescoreofthedefaulthyperparameters,whichisalsothefirstrandomsearchiteration.
Each value correspondsto the testscore of thebest model (onthe validationset) after aspecific
numberofrandomsearchiterations,averagedon15shufflesoftherandomsearchorder. Theribbon
correspondstotheminimumandmaximumscoresonthese15shuffles.
Mediumsizedtrainset Largesizedtrainset
Figure12:ComparisonofR2scoreson5regressiontasksfordifferenttrainsetsizes,withboth
numericalandcategoricalfeatures. Onlydatasetswithmorethan50,000sampleswerekept,and
thetrainsetsizewastruncatedtoeither10,000samplesor50,000samples. Dottedlinescorrespond
tothescoreofthedefaulthyperparameters, whichisalsothefirstrandomsearchiteration. Each
valuecorrespondstothetestscoreofthebestmodel(onthevalidationset)afteraspecificnumberof
randomsearchiterations,averagedon15shufflesoftherandomsearchorder. Theribboncorresponds
totheminimumandmaximumscoresonthese15shuffles.
18

A.3 Moredetailsonbenchmark
Train/Validation/Testsplit Wetake70%ofsamplesforthetrainset(orthepercentagewhich
corresponds to the maximum train set size if 70% is too high). Of the remaining 30%, we take
30%forthevalidationset, and70%forthetestset. Thevalidationandtestsetsaretruncatedto
50,000samples forspeed. Note thatthe validation setis onlyusedto selectthe bestperforming
hyperparametercombinationduringtherandomsearch,andisdistinctfromthevalidationsetused
forearlystopping(whichispartofthetrainset).
Numberoffolds Foreachdatasetandhyperparameterscombination,wevarythenumberoffolds
usedforouralgorithmsevaluationdependingonthenumberoftestingsamples:
• IfWehavemorethan6000samples,weevaluateouralgorithmson1fold.
• Ifwehavebetween3000and6000samples,weevaluateouralgorithmson2folds.
• Ifwehavebetween1000and3000samples,weevaluateouralgorithmson3folds.
• Ifwehavelessthan1000testingsamples,weevaluateouralgorithmson5folds.
Everyalgorithmandhyperparameterscombinationisevaluatedonthesamefolds.
Hardware Forallourbenchmarksandexperiments,weusethehardwarebelow. Thehardwarewas
chosenbasedonavailability,withNeuralNetworksalwaysrunningonGPUandtree-basedmodels
runningonCPU.
GPUs: NVIDIAQuadroRTX6000,NVIDIATITANXp,NVIDIAA100,NVIDIAV100,NVIDIA
TeslaT4,NVIDIAA40,NVIDIATITANRTX,NVIDIATITANV
CPUs:AMDEPYC774264-CoreProcessor,AMDEPYC770264-CoreProcessor,Intel(R)Xeon(R)
CPUE5-2660v2,Intel(R)Xeon(R)Gold6226RCPU
Hyperparametersspace HyperparametersspacesarebasedonHyperopt-sklearn[Komeretal.,
2014]whenavailable,fromGorishniyetal.[2021]andfromBorisovetal.[2021]. Wemadesome
changeswhencombiningsources,orwhentheoriginaldistributionwasnotcompatiblewithWeight
andBiasessweeps.
Defaultparametersfortree-basedmodelsareScikitLearn’sdefaults. Allneuralnetworksarerun
for300epochs,withearlystoppingandcheckpointing(thebestmodelonthevalidationsetiskept).
Earlystoppingpatienceis40forMLP,Resnet,andFTTransformer,and10forSAINT.
| Parameter              | Distribution          | Default |
| ---------------------- | --------------------- | ------- |
| Numlayers              | UniformInt[1,6]       | 3       |
| Featureembeddingsize   | UniformInt[64,512]    | 192     |
| ResidualdropoutUniform | [0,0.5]               | 0       |
| Attentiondropout       | Uniform[0,0.5]        | 0.2     |
| FFNdropout             | Uniform[0,0.5]        | 0.1     |
| FFNfactor              | Uniform[2/3,8/3]      | 4/3     |
|                        | LogUniform[1e−5,1e−3] | 1e−4    |
Learningrate
| Weightdecay           | LogUniform[1e−6,1e−3] | 1e−5     |
| --------------------- | --------------------- | -------- |
| kvcompression         | [True,False]          | True     |
| kvcompressionsharing  | [headwise,key-value]  | headwise |
| Learningratescheduler | [True,False]          | False    |
| Batchsize             | [256,512,1024]        | 512      |
Table1: FTTransformerhyperparametersspace
19

| Parameter             | Distribution          | Default   |
| --------------------- | --------------------- | --------- |
| Numlayers             | UniformInt[1,16]      | 8         |
| Layersize             | UniformInt[64,1024]   | 256       |
| Hiddenfactor          | Uniform[1,4]          | 2         |
| Hiddendropout         | [0,0.5]               | 0.2       |
| Residualdropout       | Uniform[0,0.5]        | 0.2       |
| Learningrate          | LogUniform[1e−5,1e−2] | 1e−3      |
| Weightdecay           | LogUniform[1e−8,1e−3] | 1e−7      |
| Categoryembeddingsize | UniformInt[64,512]    | 128       |
| Normalization         | [batchnorm,layernorm] | batchnorm |
| Learningratescheduler | [True,False]          | True      |
| Batchsize             | [256,512,1024]        | 512       |
Table2: Resnethyperparametersspace
| Parameter    | Distribution          | Default |
| ------------ | --------------------- | ------- |
| Numlayers    | UniformInt[1,8]       | 4       |
| Layersize    | UniformInt[16,1024]   | 256     |
| Dropout      | [0,0.5]               | 0.2     |
| Learningrate | LogUniform[1e−5,1e−2] | 1e−3    |
UniformInt[64,512] 128
Categoryembeddingsize
| Learningratescheduler | [True,False]   | True |
| --------------------- | -------------- | ---- |
| Batchsize             | [256,512,1024] | 512  |
Table3: MLPhyperparametersspace
| Parameter | Distribution                        | Default |
| --------- | ----------------------------------- | ------- |
| Numlayers | UniformInt[1,2,3,6,12]              | 3       |
| Numheads  | [2,4,8]                             | 4       |
| Layersize | UniformInt[32,64,128]               | 128     |
|           | [0,0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8] | 0.1     |
Dropout
| Learningrate | LogUniform[1e−5,1e−3] | 3e−5 |
| ------------ | --------------------- | ---- |
| Batchsize    | [128,256]             | 512  |
Table4: SAINThyperparametersspace
| Parameter        | Distribution             |     |
| ---------------- | ------------------------ | --- |
| Maxdepth         | UniformInt[1,11]         |     |
| Numestimators    | UniformInt[100,6000,200] |     |
| Minchildweight   | LogUniformInt[1,1e2]     |     |
| Subsample        | Uniform[0.5,1]           |     |
| Learningrate     | LogUniform[1e-5,0.7]     |     |
| Colsamplebylevel | Uniform[0.5,1]           |     |
| Colsamplebytree  | Uniform[0.5,1]           |     |
| Gamma            | LogUniform[1e-8,7]       |     |
| Lambda           | LogUniform[1,4]          |     |
| Alpha            | LogUniform[1e-8,1e2]     |     |
Table5: XGBoosthyperparametersspace
| Parameter     | Distribution                    |     |
| ------------- | ------------------------------- | --- |
| Maxdepth      | [None,2,3,4]([0.7,0.1,0.1,0.1]) |     |
| Numestimators | LogUniformInt[9.5,3000.5]       |     |
Criterion [gini,entropy](classif)[squared_error,absolute_error](regression)
Maxfeatures [sqrt,sqrt,log2,None,0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9]
| Minsamplessplit     | [2,3]([0.95,0.05])                          |     |
| ------------------- | ------------------------------------------- | --- |
| Minsamplesleaf      | LogUniformInt[1.5,50.5]                     |     |
| Boostrap            | [True,False]                                |     |
| Minimpuritydecrease | [0.0,0.01,0.02,0.05]([0.85,0.05,0.05,0.05]) |     |
Table6: RandomForesthyperparametersspace
20

Parameter Distribution
Loss [deviance,exponential](classif)[squared_error,absolute_error,
huber](regression)
Learningrate LogNormal[log(0.01),log(10)]
Subsample Uniform[0.5,1]
Numestimators LogUniformInt[10.5,1000.5]
Criterion [friedman_mse,squared_error]
Maxdepth [None,2,3,4,5]([0.1,0.1,0.6,0.1,0.1])
Minsamplessplit [2,3]([0.95,0.05])
Minsamplesleaf LogUniformInt[1.5,50.5]
Minimpuritydecrease [0.0,0.01,0.02,0.05]([0.85,0.05,0.05,0.05])
Maxleafnodes [None,5,10,15]([0.85,0.05,0.05,0.05])
Table7: GradientBoostinghyperparametersspace
Parameter Distribution
Loss [squared_error,absolute_error](regression)
Learningrate LogNormal[log(0.01),log(10)]
Maxdepth [None,2,3,4]([0.1,0.1,0.7,0.1])
Minsamplesleaf NormalInt[20,2]
Maxleafnodes NormalInt[31,5]
Table8: HistGradientBoostinghyperparametersspace
21

Otherdetails Toruntherandomsearches,weusethe"sweep"functionalityofWeightandBiases
[Biewald,2020].
Datasetbydataset Weshowallunnormalizedbenchmarkresultsdatasetbydataset: Figure13,14,
15and16forthemedium-sizesetting,andFigure17and18forthelarge-sizesetting.
Figure13: Unormalizedbenchmarkresultsforclassificationtasksonnumericalfeaturesonly.
Medium-sizedsetting.
22

Figure 14: Unormalized benchmark results for regression tasks on numerical features only.
Medium-sizedsetting. Negativevaluesaretruncatedtozerotomaketheplotseasiertoread.
Figure 15: Unormalized benchmark results for classification tasks on both categorical and
numericalfeatures. Medium-sizedsetting.
23

Figure16:Unormalizedbenchmarkresultsforregressiontasksonbothcategoricalandnumer-
icalfeatures. Medium-sizedsetting. Negativevaluesaretruncatedtozerotomaketheplotseasierto
read.
24

Classification Regression
Figure17:Unormalizedbenchmarkresultsforlargescaledatasets,fornumericalfeaturesonly.
Classification Regression
Figure 18: Unormalized benchmark results for large-scale datasets, for both numerical and
categoricalfeatures.
25

A.4 Moredetailsonexperiments
Inthissection,wegivemoredetailsonthechoiceswemadewhencreatingourexperiments. As
resultsmaysometimesbeeasiertointerpretbeforeaggregationacrossdatasets,wealsoshowthe
resultsofeachexperimentoneachdataset.
A.4.1 Finding1: NNsarebiasedtooverlysmoothsolutions
Smoothing WeuseaGaussiansmoothingKernel
(cid:18) (cid:19)
1
K(x∗,x)=exp − (x∗−x)TΣ−1(x∗−x)
2
withΣtheestimatedempiricalcovariancemultipliedbythe"squaredlengthscale". Thetransformed
targetonthetrainsetbecomes:
(cid:80)N
K(X ,X )Y (X )
Y˜ (X )= j=1 i j j
i (cid:80)N
K(X ,X )
j=1 i j
with(X ,..X )thetrainingsetcovariatesand(Y ,...,Y )thetrainingsetoriginaltargets.
1 N 1 N
Moredetails
• Werestrictalldatasetstotheir5mostimportantfeatures(accordingtoaRandomForest
featureimportanceranking). Thismakesthesmoothingeasier,askernelsmoothingcanbe
hardinhigh-dimension,whilekeepingenoughfeaturestoproduceinterestingresults.
• We estimate the covariance matrix of these features through ScikitLearn’s MinCovDet,
whichismorerobusttooutliersthantheempiricalcovariance.
RawresultsareshowninFigure19datasetbydataset.
Examplesofirregularpatterns Figure20showsthedecisionboundariesofadefaultMLPanda
defaultRandomForestonthe2mostimportantfeaturesoftheelectricitydataset. TheRandomForest
achieve a perfect training accuracy and a test accuracy (85%) higher than the MLP (80%). The
featuresareGaussieniedandweshowazoomed-inpartofthefeaturespace. Inthispart,wecan
seethattheRandomForestisabletolearnirregularpatternsonthexaxis(whichcorrespondstothe
datefeature)thattheMLPdoesnotlearn. Weshowthisdifferencefordefaulthyperparametersbut
itseemstousthatthisisatypicalbehaviorofneuralnetworks,anditisactuallyhard, albeitnot
impossible,tofindhyperparameterstosuccessfullylearnthesepatterns.
A.4.2 Finding2: UninformativefeaturesaffectmoreMLP-likeNNs
Tabular datasets contain a lot of uninformative features Raw results are shown in Figure 21
datasetbydataset.
UninformativefeaturesaffectmoreMLP-likeNNs RawresultsareshowninFigure22(uninfor-
mativefeaturesadded)andFigure23(uninformativefeaturesremoved).
A.4.3 Finding3: Dataarenoninvariantbyrotation,soshouldbelearningprocedures
Details Random rotation were computed using Scipy’s [Virtanen et al., 2020]
stats.special_ortho_group.rvs.
RawresultsareshowninFigure24(withallfeatures)andFigure25(with50%features)datasetby
dataset.
26

Figure 19: Test accuracy of different models for varying smoothing of the target function on
thetrainset. WesmooththetargetfunctionthroughaGaussianKernelsmoother,whosecovariance
matrixisthedatacovariance,multipliedbythe(squared)lengthscaleoftheGaussiankernelsmoother.
Alengthscaleof0correspondstonosmoothing(theoriginaldata). AllfeatureshavebeenGaussi-
enizedbeforethesmoothingthroughScikitLearn’sQuantileTransformer. Theboxplotsrepresentthe
distributionofaccuraciesacross15re-orderingsoftherandomsearch. SameexperimentthanFig. 3,
shownforeachdatasetwithoutscorenormalization
RandomForest(85%) MLP(80%)
Figure20:DecisionboundariesofadefaultMLPandRandomForestforthe2mostimportantfeatures
oftheelectricitydataset
27

Figure21: TestaccuracyofaGBTforvaryingproportionsofremovedfeatures. Featuresare
removedinincreasingorderoffeatureimportance(computedwithaRandomForest),andthetwo
linescorrespondtotheaccuracyusingthe(mostimportant)keptfeatures(blue)orthe(leastimportant)
removedfeatures(red). Scoresarenormalizedbetween0(randomchance)and1(bestscoreamong
allhyperparameters). Thesescoresareaveragedacross30randomsearchorders,andtheribbons
correspondtotheminimumandmaximumvaluesamongthese30orders. SameexperimentthanFig.
4,shownforeachdataset. Notethataxesdonotalwaysstartatzero.
28

Figure 22: Test accuracy changes when adding uninformative features. Added features are
sampled from standard Gaussians uncorrelated with the target and with other features. Ribbons
correspondtotheminimumandmaximumscoreamongthe30differentrandomsearchreorders
(startingwiththedefaultmodels). SameexperimentthatinFigure5(b), shownforeachdataset
withoutscorenormalization.
Figure23: Testaccuracychangeswhenremovinguninformativefeatures. Featuresareremoved
inincreasingorderoffeatureimportance(computedwithaRandomForest). Ribbonscorrespond
totheminimumandmaximumscoreamongthe30differentrandomsearchreorders(startingwith
thedefaultmodels). SameexperimentthatinFigure5(a), shownforeachdatasetwithoutscore
normalization.
29

Figure24: Testaccuracyofdifferentmodelswhenrandomlyrotatingourdatasets. Allfeatures
areGaussianizedbeforetherandomrotations. Thescoresareaveragedacrossdatasets,andtheboxes
depictthedistributionacrossrandomsearchshuffles. Sameexperimentthatin6(Left),shownfor
eachdatasetwithoutscorenormalization.
Figure25: Testaccuracyofdifferentmodelswhenrandomlyrotatingourdatasets,with50%
featuresremoved. AllfeaturesareGaussianizedbeforetherandomrotations. Theremovedfeatures
are the least important half (according to a RandomForest), and are removed before the rotation.
Thescoresareaveragedacrossdatasets,andtheboxesdepictthedistributionacrossrandomsearch
shuffles. Sameexperimentthatin6(Right),shownforeachdatasetwithoutscorenormalization.
30

A.5 DiscussiononKadraetal.[2021b]
Weobservedthattree-basedmodelsaresuperiorforeveryrandomsearchbudget,andtheperformance
gap stays wide even after a large number of random search iteration. However, this might no
longerbetruewhenaddingadditionalregularizationtechniquestoourrandomsearch,suchasdata
augmentation. Indeed,Kadraetal.[2021a]findthatsearchingthrougha"cocktail"ofregularization
on a Multi-Layer-Perceptron is competitive with XGBoost after half an hour of tuning (for both
models), though the datasets considered in their paper are quite different, in particular with the
presenceof"deterministic"game-inspireddatasetsinKadraetal.[2021b],onwhichtheirmethod
performsverywellandcontributesmarkedlytotheoverallbenchmarkresults.
A.6 Whichhyperparametersperformwellontabulardata?
Ourrandomsearchresultsprovideinsightsintowhichhyperparametersareimportantforlearning
ontabulardata. Belowwepresentameasureofhyperparametersimportanceinourclassification
benchmarkonnumericalfeatures.
Methodology Accuracy is normalized (see 3), and negative scores are truncated to zero. For
eachmodel,wefitaRandomForestclassifierwithdefaulthyperparameterstopredictthesescores
from the model’s hyperparameters and the dataset, and we compute the feature importance for
eachofthehyperparameter("rf_importance"). Thisgivesusascorewhichrepresenthowmuchan
hyperparametershouldbetuned. Tomeasureifanhyperparameterhasapositiveornegativeimpact
ontheperformance,wealsocomputethecoefficientofaLinearRegressiontrainedonthesametask
thattheRandomForest("lin_coef")
Results Thelearningrateisbyfarthemostimportantparameterforneuralnetworksandgradient-
boostedtrees. Notethatthelinearcoefficientisnotalwaysveryhigh,whichsuggeststhatthelearning
rateshouldbetunedforeachdataset. Fortree-basedmodels,thedepthofthetreesisanothervery
important parameter, and it seems that deeper trees help, even for gradient-boosted trees. This
observation is related to our "Finding 1" 5.2, as deeper trees enable very irregular patterns to be
learned.
Belowwegivetheresultsforeacharchitecture.
MLP
| names        | rf_importance | lin_coef |     |
| ------------ | ------------- | -------- | --- |
| lr           | 0.22          | -0.04    |     |
| d_layers     | 0.18          | -0.01    |     |
| d_embedding  | 0.15          | 0.0      |     |
| n_layers     | 0.14          | -0.1     |     |
| batch_size   | 0.03          | -0.01    |     |
| lr_scheduler | 0.01          | 0.0      |     |
Resnet
| names                   |     | rf_importance | lin_coef |
| ----------------------- | --- | ------------- | -------- |
| lr                      |     | 0.08          | 0.01     |
| normalization_layernorm |     | 0.05          | 0.0      |
| n_layers                |     | 0.04          | -0.03    |
| d                       |     | 0.02          | 0.0      |
| hidden_dropout          |     | 0.02          | 0.01     |
| residual_dropout        |     | 0.01          | 0.0      |
| batch_size              |     | 0.01          | 0.0      |
| optimizer__weight_decay |     | 0.0           | 0.0      |
| d_hidden_factor         |     | 0.0           | 0.0      |
| d_embedding             |     | 0.0           | 0.0      |
| lr_scheduler            |     | 0.0           | 0.0      |
FTTransformer
31

| names                            |     | rf_importance | lin_coef |
| -------------------------------- | --- | ------------- | -------- |
| lr                               |     | 0.06          | 0.0      |
| residual_dropout                 |     | 0.04          | -0.02    |
| d_token                          |     | 0.03          | 0.0      |
| n_layers                         |     | 0.02          | 0.0      |
| ffn_dropout                      |     | 0.02          | 0.0      |
| d_ffn_factor                     |     | 0.01          | 0.0      |
| kv_compression                   |     | 0.01          | -0.01    |
| optimizer__weight_decay          |     | 0.01          | 0.0      |
| attention_dropout                |     | 0.01          | 0.0      |
| lr_scheduler                     |     | 0.0           | 0.0      |
| kv_compression_sharing_key-value |     | 0.0           | 0.0      |
| batch_size                       |     | 0.0           | 0.0      |
SAINT
| names          | rf_importance | lin_coef |     |
| -------------- | ------------- | -------- | --- |
| lr             | 0.28          | -0.11    |     |
| depth          | 0.15          | -0.07    |     |
| dim            | 0.05          | -0.03    |     |
| dropout        | 0.03          | 0.0      |     |
| heads          | 0.01          | 0.0      |     |
| batch_size     | 0.01          | 0.0      |     |
| val_batch_size | 0.0           | 0.0      |     |
XGBoost
| names             | rf_importance | lin_coef |     |
| ----------------- | ------------- | -------- | --- |
| learning_rate     | 0.26          | 0.01     |     |
| min_child_weight  | 0.07          | -0.04    |     |
| max_depth_2.0     | 0.05          | 0.13     |     |
| reg_alpha         | 0.05          | -0.03    |     |
| n_estimators      | 0.03          | 0.01     |     |
| max_depth_4.0     | 0.02          | 0.27     |     |
| subsample         | 0.02          | 0.01     |     |
| colsample_bytree  | 0.02          | 0.0      |     |
| max_depth_3.0     | 0.02          | 0.21     |     |
| reg_lambda        | 0.01          | 0.0      |     |
| gamma             | 0.01          | 0.0      |     |
| max_depth_10.0    | 0.01          | 0.35     |     |
| max_depth_11.0    | 0.01          | 0.35     |     |
| max_depth_7.0     | 0.01          | 0.33     |     |
| max_depth_5.0     | 0.01          | 0.3      |     |
| max_depth_6.0     | 0.01          | 0.32     |     |
| max_depth_8.0     | 0.01          | 0.34     |     |
| max_depth_9.0     | 0.01          | 0.34     |     |
| colsample_bylevel | 0.01          | 0.0      |     |
GradientBoostingClassifier
| names            | rf_importance | lin_coef |     |
| ---------------- | ------------- | -------- | --- |
| learning_rate    | 0.4           | -0.02    |     |
| n_estimators     | 0.15          | 0.09     |     |
| max_depth_None   | 0.14          | 0.36     |     |
| max_depth_4.0    | 0.04          | 0.19     |     |
| max_depth_3.0    | 0.02          | 0.11     |     |
| min_samples_leaf | 0.01          | 0.0      |     |
| subsample        | 0.01          | 0.0      |     |
| loss_exponential | 0.0           | 0.0      |     |
RandomForest
32

| names             | rf_importance | lin_coef |
| ----------------- | ------------- | -------- |
| max_depth_None    | 0.43          | 0.54     |
| max_depth_4.0     | 0.07          | 0.24     |
| max_depth_3.0     | 0.03          | 0.13     |
| min_samples_leaf  | 0.01          | -0.01    |
| n_estimators      | 0.01          | 0.0      |
| max_features_None | 0.01          | -0.06    |
| bootstrap         | 0.01          | 0.01     |
| max_features_log2 | 0.0           | 0.04     |
| criterion_gini    | 0.0           | 0.0      |
| max_features_0.2  | 0.0           | 0.04     |
| max_features_sqrt | 0.0           | 0.04     |
| max_features_0.4  | 0.0           | 0.05     |
| max_features_0.5  | 0.0           | 0.04     |
| max_features_0.6  | 0.0           | 0.04     |
| max_features_0.7  | 0.0           | 0.03     |
| max_features_0.8  | 0.0           | 0.01     |
| max_features_0.9  | 0.0           | -0.01    |
| max_features_0.3  | 0.0           | 0.05     |
A.7 Howtouseourbenchmark?
All instructions to use our benchmark and reproduce our results are available at our repository:
https://github.com/LeoGrin/tabular-benchmark. To ease the use of our benchmark and
thereproducibilityofourresultsweprovide:
• TheselectedandtransformeddatasetsasanOpenMLsuite. Alllinkstothetransformedand
originaldatasetsarealsoinA.1.
• A CSV file containing the results of all our random searches. It can be used to cheaply
benchmarkanewmethod.
• Thecodeusedtoproduceourbenchmarkandourexperiments.
33