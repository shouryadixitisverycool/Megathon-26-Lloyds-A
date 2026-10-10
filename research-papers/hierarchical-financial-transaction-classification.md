Hierarchical Classification of Financial Transactions Through
Context-Fusion of Transformer-based Embeddings and
Taxonomy-aware Attention Layer
AntonioJ.G.Busson1,2,RafaelRocha1,2,RennanGaio1,RafaelMiceli1,
IvanPereira2,DanieldeS.Moraes2,SA˜©rgioColcher2,AlvaroVeiga2,
BrunoRizzi1,FranciscoEvangelista1,LeandroSantos1,FellipeMarques1,
MarcosRabaioli1,DiegoFeldberg1,DeboraMattos1,JoA˜£oPasqua1,DiogoDias1
1BTGPactual
SA˜£oPaulo–SP–Brazil
2PontificalCatholicUniversityofRiodeJaneiro(PUC-Rio)
RiodeJaneiro–RJ–Brazil
{antonio.busson, rafael-h.rocha, rennan.gaio}@btgpactual.com
Abstract. This work proposes the Two-headed DragoNet, a Transformer-based
model for hierarchical multi-label classification of financial transactions. Our
modelisbasedonastackofTransformersencoderlayersthatgeneratescontex-
tual embeddings from two short textual descriptors (merchant name and busi-
ness activity), followed by a Context Fusion layer and two output heads that
classify transactions according to a hierarchical two-level taxonomy (macro
and micro categories). Finally, our proposed Taxonomy-aware Attention Layer
corrects predictions that break categorical hierarchy rules defined in the given
taxonomy. Ourproposaloutperformsclassicalmachinelearningmethodsinex-
perimentsofmacro-categoryclassificationbyachievinganF1-scoreof93%on
acarddatasetand95%onacurrentaccountdataset.
Keywords. Deep learning, Financial Transactions, Transformer, Hierarchical
Classification.
1. Introduction
Artificial intelligence technologies, such as Machine Learning (ML), are already trans-
forming several industries and services, including banking. Among several financial ap-
plications, ML-based technologies can accurately classify financial transactions, which
can be used to drive business decisions and understand customers’ financial needs
[Belancheetal. 2019].
Current industry standards for identifying business types of merchants, such as
ISO-182451, could be used to classify transactions via mapping rules. However, this ap-
proach has limitations: (1) old standards do not cover many actual business activities,
e.g., different internet/app-based merchants are classified generically as digital products;
(2)insomecases,merchantsareregisteredwithinappropriatebusinesscategoriesinpay-
mentsystems. Inthiscontext,wehypothesizethatML-basedmodelscanovercomethese
1https://www.iso.org/standard/33365.html
3202
ceD
21
]GL.sc[
1v03770.2132:viXra

limitationsbylearningcontextualrepresentationsfromagivenmerchantnameanditsre-
latedbusinessactivityandusingittoclassifytransactionscorrectly,e.g.,givenamerchant
named”John’sBarbecue”,contextually,themodelshouldclassifyitasarestaurant,even
ifitsregisteredbusinessactivityisapharmacyrelateddescription.
Ourproposedtransactionclassifierisbasedonthefollowing: (1)AstackofTrans-
formerencoders[Vaswanietal. 2017]togeneratecontextualembeddingsfromthetrans-
action’s merchant name and business activity descriptor; (2) A context-fusion layer to
aggregate contextual embeddings; (3) Two output heads and a taxonomy-aware atten-
tion layer to predict hierarchical dual-labels based in a given categorical taxonomy. To
demonstrate our proposal’s effectiveness, we conducted benchmark experiments on two
real-world datasets, the first composed of 151,867 card transactions and the second com-
posedof151.838currentaccounttransactions.
The remainder of this paper is structured as follows. We begin, in Section 2, by
presenting recent related works that focus on the classification of financial transactions.
In Section 3, we present our datasets. Next, Section 4 introduces our proposal, followed
bySection5,wherewedescribetheexperiments. Finally,Section6isdevotedtoourfinal
remarksandconclusions.
2. Related Work
Recent works have been devoted to financial transaction classification using ML-based
methods. Many focus on problems related to fraud and AML (Anti-Money Launder-
ing). [Khrestinaetal. 2017] proposed a system to classify suspicious transactions. They
modeled the user behavior with a relationship graph and used logistic regression to de-
tect fraudulent activities. [deSa´ etal. 2018] proposed the Fraud-BCN, a Bayesian net-
work for classifying risky transactions. Their approach performed better than classic
algorithms such as logistic regression, random forest, and SVM. [Fioreetal. 2019] in-
vestigated the applicability of generative models as a data augmentation technique for a
transactional fraud dataset. Experiments show that a classifier trained on the augmented
set outperforms the same classifier trained on the original data, resulting in an effective
frauddetectionmechanism.
Similar to ours, other recent works also use Transformer-based meth-
ods for generating contextual embeddings of financial data. [Padhietal. 2021,
Hewapathiranaetal. 2022], for instance, explored Transformer-based models as an ex-
tractorofembeddingsintabulardatatodetectfraudulenttransactions. Experimentsshow
thattheembeddingsgeneratedbythismethodcanimprovetheresultsofothersupervised
andnon-supervisedmodels,suchasGradientBoostingandK-means. Unliketheseworks,
weoptedforamorestraightforwardapproachsinceourproposalisbasedonthefusionof
contextual embeddings extracted only from two transaction information, the merchant’s
nameanditseconomicactivity.
Other works focus on transaction classification for consumer behavior.
[ChengandAl-Sayed2022] proposed a method to classify individuals’ spending behav-
iorbasedontheirmonthlytransactionrecords. Theyproposeaclassificationmodelusing
k-meansclusteringandaneuralnetworktocategorizespendingbehaviorbasedonincome
and spending. Their results indicate that the proposed method can classify spending be-
haviors such as “low-income and high-spending” or “high-income and low-spending”.

[Garcia-Mendezetal. 2020] proposed a PFM app called CoinScrap. Their solution for
transaction classification is based on a two-stage method that combines a short text simi-
laritydetectorwithanSVMclassifier.
[Yehetal. 2020]employedneuralnetworkstocategorizemerchantbusinesstypes
using: (1) temporal features of the merchant transaction history and (2) the affinity rela-
tionship between merchants. Like ours, they perform feature-fusion between these two
feature types before feeding them to a classification layer. However, their raw affinity
vector is the size of the number of merchants being classified, which may occur in poor
scalability. They address this problem by limiting the number of active relationships to a
parameterk thattunesthetrade-offbetweenperformanceandaccuracy.
The hierarchical classification of financial transactions was investigated by
[Vollsetetal. 2017]. They explored the use of external semantic data from the
BrA˜¸nnA˜¸ysund Registry and the Google Places API to improve the accuracy of their
bank transaction classification system. Similar to our datasets, their dataset consists of
unstructured transaction descriptions, each labeled with a corresponding category and
sub-category from 10 categories and 63 sub-categories. They used a Bag-of-words rep-
resentation and a Logistic Regression as a classification method. In Experiments, their
resultsshowimprovementfromusingenhancementofbothbasesseparately,andabetter
result, when combining information of the two bases. Rather than multiple models for
multi-label classification, our approach consists of a single end-to-end model trained to
classifyhierarchicalmulti-labels.
3. Dataset
We built two datasets for transaction classification in a retail banking context. Transac-
tions were extracted from BTG Pactual Banking’s transactional stream with a 3-month
window, April - June of 2021. No information about banking customers is present in the
dataset’stransactions. Eachtransactioncontainsthefollowingdata: (1)amerchantname;
And(2)adescriptionofthebusinessactivity.
The first dataset is composed of 151.867 unique card transactions. In this dataset,
the merchant’s activity is described by the Merchant Category Code (MCC), a textual
description of 296 retail financial services listed in ISO-18245. The second dataset con-
sists of 151.838 unique account transactions. Instead of MCC, the merchant’s activity of
this dataset is described by the Brazilian National Classification of Economic Activities
(CNAE)2,atextualdescriptioninpt-brof695economicactivities.
Table 1 shows the taxonomy of retail services defined by BTG Pactual’s con-
sumer banking specialists. The taxonomy is structured into two hierarchical levels, the
top-levelentities,calledMacrocategories,describebroadretailsectors,e.g.,Food,Shop-
ping, and Personal Care. Each Macro category contains subcategories, called Micro cat-
egories, which describe specific retail sectors, e.g., the Shopping category contains the
subcategories Electronics, Toys, and Sporting Goods. The taxonomy contains 82 micro
categories,partitionedinto15macrocategories.
A group of 8 volunteers manually annotated the dataset in two steps. In the first
2https://concla.ibge.gov.br/estrutura/atividades-economicas-estrutura/
cnae

Table1. TaxonomyofRetailServices
# MacroCat. MicroCat. # MacroCat. MicroCat. # MacroCat. MicroCat.
| 1 Food      | Restaurant   | 29 Health | Doctor          | 57 Bill | Water       |
| ----------- | ------------ | --------- | --------------- | ------- | ----------- |
| 2 Food      | Bar          | 30 Health | HealthInsurance | 58 Bill | Condominium |
| 3 Food      | Cafe&Bakery  | 31 Health | Therapy         | 59 Bill | Rental      |
| 4 Food      | OtherFood    | 32 Health | Dentist         | 60 Bill | Energy      |
| 5 Groceries | Horticulture | 33 Health | Pharmacy        | 61 Bill | Gas         |
6 Groceries Beverages 34 Health Exams 62 Bill Telecomunication
7 Groceries Butchery 35 Health OtherHealth 63 Bill CreditCard
8 Groceries Supermarket 36 PersonalCare BeautySalon 64 Bill OtherBill
9 Groceries OtherGroceries 37 PersonalCare Spa&EstheticClinic 65 Entertainment Clubs
10 Shopping Clothing&Accessories 38 PersonalCare Sports 66 Entertainment Games
11 Shopping Books&Supplies 39 PersonalCare Gym 67 Entertainment Shows&Events
12 Shopping Eletronics 40 PersonalCare Cosmetics 68 Entertainment Cinema&Theater
13 Shopping Toy 41 PersonalCare Tattoo&Piercing 69 Entertainment Expositions
14 Shopping SportingGoods 42 PersonalCare OtherPersonalCare 70 Entertainment Streaming
15 Shopping Gifts 43 Pets PetShop 71 Entertainment Journals&Magazines
16 Shopping OtherShopping 44 Pets Veterinary 72 Entertainment Parks
17 Transport Fuel 45 Pets OtherPets 73 Entertainment OtherEntertainment
18 Transport CarMaintenace 46 Home HomeGoods 74 Education Courses
| 19 Transport | Bike | 47 Home | Renovations | 75 Education | School |
| ------------ | ---- | ------- | ----------- | ------------ | ------ |
20 Transport Parking 48 Home Gardening&Pool 76 Education College
21 Transport CarWash 49 Home Laundry 77 Education OtherEducation
22 Transport PublicTransportation 50 Home DomesticEmployees 78 Travel Accommodation
| 23 Transport | Taxi&Apps | 51 Home | Security  | 79 Travel | Tickets  |
| ------------ | --------- | ------- | --------- | --------- | -------- |
| 24 Transport | CarRental | 52 Home | OtherHome | 80 Travel | Exchange |
25 Transport TrafficTicket 53 Tax&Tribute HouseTaxes 81 Travel OtherTravel
26 Transport Toll 54 Tax&Tribute CarTaxes 82 Donation OtherDonation
| 27 Transport     | OtherTransport | 55 Tax&Tribute | IncomeTax        |     |     |
| ---------------- | -------------- | -------------- | ---------------- | --- | --- |
| 28 OtherCategory | Other          | 56 Tax&Tribute | OtherTax&Tribute |     |     |
step, we partition our two datasets into four equal parts. Next, we formed four pairs
of volunteers to each label a specific part of the dataset. In the second step, we collect
all transactions with labeling disagreement between the pairs and create a new subset
of transactions. Finally, this subset was divided equally among the volunteers, where
each one voted for one of the labels suggested in the previous step. Table 2 shows the
distributionoftransactionsbymacrocategoriesinourtwodatasets.
|     | Table2. | DatasetdistributionbyMacrocategory |                  |        |     |
| --- | ------- | ---------------------------------- | ---------------- | ------ | --- |
|     |         | # MacroCateg.                      | Card CurrentAcc. |        |     |
|     |         | 1 Shopping                         | 40,194           | 37,369 |     |
|     |         | 2 Food                             | 30,405           | 28,124 |     |
|     |         | 3 Groceries                        | 21,559           | 20,888 |     |
|     |         | 4 Home                             | 19,640           | 21,411 |     |
|     |         | 5 Transport                        | 18,175           | 18,588 |     |
|     |         | 6 Health                           | 10,426           | 10,599 |     |
|     |         | 7 PersonalCare                     | 10,272           | 10,186 |     |
|     |         | 8 Bill                             | 8,306            | 10,230 |     |
|     |         | 9 Education                        | 4,514            | 5,085  |     |
|     |         | 10 Pets                            | 3,645            | 3,512  |     |
|     |         | 11 Travel                          | 2,116            | 2,298  |     |
|     |         | 12 Entertainment                   | 1,962            | 2,033  |     |
|     |         | 13 Donation                        | 1,745            | 2,137  |     |
|     |         | 14 OtherCategory                   | 1,098            | 841    |     |
|     |         | 15 TaxandTribute                   | 70               | 58     |     |
4. Model
TheoverviewofourproposedmethodisdepictedinFigure1. TheTwo-headedDragoNet
comprises a stack of Transformer layers that generates contextual embeddings for two
textual inputs. Next, a Context Fusion layer aggregates these contextual embeddings to

generate a single enhanced contextual representation. Finally, two output heads classify
the transaction according to the hierarchy defined by a given taxonomy; the first head
predictstop-levelclasses(macrocategories),whilethesecondheadpredictssecond-order
classes (micro categories). The Taxonomy Attention layer uses the first head output to
correctthehierarchyinconsistenciesofthesecondheadoutput.
Figure1. Two-headedDragoNetarchitecture.
Thesubsectionsthatfollowarestructuredasfollows. InSection4.1,wedetailthe
Two-head DragoNet model workflow. Next, in Section 4.2, we describe the Transformer
Encoder layer. In Section 4.3, we introduce the Context-Fusion layer. Finally, in Section
4.4,wedetailtheTaxonomy-awareAttentionlayer.
4.1. Modelworkflow
Given a collection of financial transactions B, each transaction b ∈ B is defined as a
2-tuple b ≡ ⟨x,y⟩, where x and y denotes a transactional feature and a category, respec-
tively. Each feature is defined as x ≡ ⟨xn,xe⟩, where xn is a merchant name, and xe is a
businessactivitydescription. Bothxn andxe compriseanarray{x ,x ,...,x |x ∈ S},
1 2 m i
where m is the number of words in the sentence, and S is the set of word tokens of the
dataset’s text corpus. Given a categorical taxonomy as a DAG G ≡ ⟨C,R⟩, in which
C is a set of categories, and R ⊆ C × C is a set of relationships. Each transactional
category consists of a dual-label y ≡ ⟨y ,y ⟩ ∈ R | y ↓ y , where ↓ denotes a hierarchy
i j i j
relationship,i.e.,y istheparentofy .
i j
Using the column embedding layer (E ), we generate parametric embeddings for
θ
both xn and xe. Let E (x) ≡ {e ,e ,...,e } where e ∈ Rd is the
θ θ1(x1) θ2(x2) θm(xm) θi(xi)
parametricembeddingofthei-thsentenceword. Next,weadd“positionalencodings”(P)

totheseparametricembeddingsE (xn)andE (xe)toinjectsequentialinformation,since
|     |     | θ   | θ   |     |     |     |
| --- | --- | --- | --- | --- | --- | --- |
thevanillaTransformercontainsnorecurrenceandnoconvolution.
Afterward, each modality of positional-encoded embeddings is inputted into a
stack of transformer encoders. Then, each positional-encoded embedding is transformed
into contextual embedding when outputted from the last Transformer Encoder layer
through the consecutive aggregation of context from embeddings generated by inner
TransformerEncoderlayers. LetT beafunctionthatrepresentsthestackofTransformer
ϕ
encoder layers. T operates the positional encoded embeddings (E (x)+P) and returns
|                   | ϕ          |            |     |             | θ         |           |
| ----------------- | ---------- | ---------- | --- | ----------- | --------- | --------- |
|                   |            |            | T ≡ | {t ,t ,..,t | }, t ∈    | Rdfor i ∈ |
| the correspondent | contextual | embeddings |     | 1 2         | n where i |           |
{1,...,n}.
Let Tn and Te be the contextual embeddings generated from xn and xe using T .
ϕ
We denote the Context Fusion layer as a function F , in which it aggregates both Tn and
λ
Te to produce a single high-level contextual representation. The output of this layer is
defined by the parameter λ ∈ {α,β}, which returns Oα = {oα,oα,...,oα} if λ = α or
|     |     |     |     |     | 1 2 j |     |
| --- | --- | --- | --- | --- | ----- | --- |
Oβ = {oβ,oβ,...,oβ} if λ = β, where Oα and Oβ are the prediction distribution for all
1 2 k
macroandmicrocategories,respectively.
Let H be the categorical cross-entropy function. We minimize the following
multi-tasklossfunction:
|     |     | L(⟨xn,xe⟩,⟨yα,yβ⟩) |     | Lα +Lβ |     |     |
| --- | --- | ------------------ | --- | ------ | --- | --- |
=
|     | Lα = | H(F (T | (E (xn)+P,E | (xe))+P,yα) |     |     |
| --- | ---- | ------ | ----------- | ----------- | --- | --- |
|     |      | α ϕ    | θ           | θ           |     |     |
|     | Lβ   |        | (xn)+P,E    | (xe))+P,yβ) |     |     |
|     | =    | H(F (T | (E          |             |     |     |
|     |      | β ϕ    | θ           | θ           |     |     |
whereLα andLβ arelossfunctionsformacroandmicrocategoriesclassification,respec-
tively.
Exclusively at inference time, we use the Taxonomy-aware Attention layer to ad-
just predictions of microcategories (Oβ) that break thehierarchy relationships defined in
thegiventaxonomyG,producinganO′β
output.
4.2. TransformerEncoderLayer
The Transformer Encoder layer learns to generate contextual representations (embed-
dings) from a sequence of symbolic inputs using stacked Self-Attention and Fully Con-
nected layers. Attention is a function that maps a Query (Q) and a set of Key (K) and
Value(V)pairstoanoutput. Formally,letQ ∈ Rm×k,K ∈ Rm×k,andV ∈ Rm×v,where
m is the number of the embeddings inputted; And k and v are the dimensions of the
Key and Value vectors, respectively. The Scaled Dot-Product Attention block computes
√
the dot products of the query with all keys, divides each by k, and applies a softmax
functiontoobtaintheweightsonthevalues. TheAttentionfunctionisdefinedasfollows:
|     |     | Attention(Q,K,V) |     | = A.V, |     |     |
| --- | --- | ---------------- | --- | ------ | --- | --- |
√
| softmax((QKT)/ |     |     |                                      |     |     | Rm×m |
| -------------- | --- | --- | ------------------------------------ | --- | --- | ---- |
| whereA =       |     | k). | Foreachembedding,theattentionmatrixA |     |     | ∈    |
calculateshowmuchitattendstootherembeddings,thustransformingtheembeddinginto
acontextualone.

Instead of a single attention function. In parallel, Multi-head Attention linearly
projects the queries, keys, and values h times with different, learned linear projections.
Then,theseareconcatenatedandonceagainprojectedasfollows:
|     | MultiHead(Q,K,V) |     | = Concat(head |     | ,head | ,...,head | )WO, |     |
| --- | ---------------- | --- | ------------- | --- | ----- | --------- | ---- | --- |
|     |                  |     |               |     | 1     | 2         | h    |     |
Attention(QWQ,KWK,VWV),
| where head | =   |         |            |     | projections |     | are parameter | matrices |
| ---------- | --- | ------- | ---------- | --- | ----------- | --- | ------------- | -------- |
|            | i   |         | i i        |     | i           |     |               |          |
| WQ Rm×k,WK |     | Rm×k,WV | Rm×v,andWO |     | Rhv×m.      |     |               |          |
| ∈          |     | ∈       | ∈          |     | ∈           |     |               |          |
| i          |     | i       | i          |     | i           |     |               |          |
In addition to Transformer Encoder sub-layers, the output of the Multi-head At-
tention is projected back to the embedding of dimension d through a fully connected
feed-forward network (FFN) composed of two linear transformations with a ReLU acti-
vation.
4.3. Context-FusionLayer
TheContext-FusionLayercomprisesaconcatenationofthecontextualembeddingsfrom
merchant name andbusiness activity description (T andT ), an FNN withReLU activa-
|     |     |     |     |     | n   | e   |     |     |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
tion,followedbyalastlayerofalineartransformationwithSigmoidactivation:
|     | ContextFusion(Tn,Te,λ) |     | = Sigmoidλ(FNN(Concat(Tn,Te))) |     |     |     |     |     |
| --- | ---------------------- | --- | ------------------------------ | --- | --- | --- | --- | --- |
where the parameter λ ∈ {α,β} denotes the size in units of the sigmoidal output, if
λ = α, the output size is the number of macro categories, else if λ = β the size is the
numberofmicrocategories.
4.4. Taxonomy-awareAttentionLayer
The Taxonomy-aware Attention layer consists of a rule-based layer that adjusts predic-
tions of micro categories that break the category hierarchy defined in a taxonomy. Given
Oα Oβ,
and this layer produces an array M of size b. We assume that each position of
M corresponds to a micro category. Then, positions corresponding to subcategories of
the macro categories with the highest score are filled with 1 and 0 otherwise. Finally, a
point-wisemultiplicationbetweenM andOβ suppressesallinvalidcategoryscores:
|     |     | TaxonomyAttention(Oα,Oβ) |     |     |     | M.Oβ |     |     |
| --- | --- | ------------------------ | --- | --- | --- | ---- | --- | --- |
=
where:
|     |     | M = {m | ,m ,...,m }|m | ∈   | {0,1}for | i ∈ | {1,...b} |     |
| --- | --- | ------ | ------------- | --- | -------- | --- | -------- | --- |
|     |     | 1      | 2 b           | i   |          |     |          |     |
(cid:40)
|     |     |     | ifClass(Oβ) | Class(Argmax(Oα)) |     |     |     |     |
| --- | --- | --- | ----------- | ----------------- | --- | --- | --- | --- |
|     |     |     | 1,          | ↓                 |     |     |     |     |
|     |     | m = |             | i                 |     |     |     |     |
i
|     |     |     | 0, otherwise |     |     |     |     |     |
| --- | --- | --- | ------------ | --- | --- | --- | --- | --- |
5. Experiments
This section evaluates our models’ effectiveness in classifying financial transactions. We
perform benchmark comparisons using different algorithms: the nearest neighbor heuris-
tic (KNN), shallow classifiers like SVC (C-Support Vector Classification) and Random
Forest, and other deep learning methods such as GRU (Gated Recurrent Units), LSTM
(LongShort-TermMemory),andBLSTM(BidirectionalLSTM).

Weencodedatasettextsusingthreedifferenttechniques: TF-IDF,HashingVector-
izer,andTokenizer(Index-BasedEncoding). WeusedtheTokenizertechniquetofeedthe
deep learning models’ parametric embedding layer. In contrast, the other two techniques
werecombinedwiththeshallowmodelssincetheyaremoresuitableforthesealgorithms.
Weperformthreeexperimentsforbothdatasetstounderstandhoweachdatatype
contributes to the classification task. The first experiment uses just the merchant name
data,thesecondusesjustthebusinessactivitydescriptiondata,andthelastcombinesboth
data. Foreachexperiment,weperformthesame10-foldsplitandevaluatethemodelsby
thePrecision(P),Recall(R),andF1-Score(F1).
5.1. Results
Table 3 shows the result of the experiment using only the merchant name data. No-
tably, models based on deep learning produced superior results than other baseline mod-
els. TheTransformermodelachievedthebestresult,producinganF1-scoreof56.78%in
the card dataset and 59.14% in the current account dataset for macro-category classifica-
tion. Regarding micro-category classification, it produced an F1-score of 46.02% in the
carddatasetand45.15%inthecurrentaccountdataset.
Inthisscenario,wenoticedthatmorethanthemerchantnamealoneisneededfor
the classification task, as our models produced a low F1 score. Figure 2 (A) shows the
contextualembeddingsofthemerchantnamesgeneratedbythetransformermodel. These
embeddings have a strong interclass correlation, making the classification task challeng-
ing. When inspecting the merchant names, we noticed that it is impossible to determine
the categories with confidence in many cases, as some merchant names are, for exam-
ple, person names or generic names without precise semantics. e.g., Red Shop, Thunder,
Bluebird.
Figure 2. T-SNE visualizations of Contextual Embeddings in 2D space for trans-
actionsofthetop-10macrocategories.

Table3. Experimentresultsinscenario1: Usingonlythemerchantnamedata
(A)CardTransactionsDataset
|                 | MacroCategory | MicroCategory |             |
| --------------- | ------------- | ------------- | ----------- |
| Model           | P R           | F1 P          | R F1        |
| Transformer     | 57.76 55.85   | 56.78 47.86   | 44.33 46.02 |
| BLSTM           | 58.86 53.90   | 56.27 47.72   | 40.29 43.69 |
| LSTM            | 59.47 53.36   | 56.24 49.98   | 40.98 45.03 |
| GRU             | 58.85 53.28   | 55.92 47.77   | 40.90 44.06 |
| TF-IDF+SVC      | 45.77 34.66   | 39.44 24.33   | 20.01 21.95 |
| TF-IDF+RF       | 40.46 36.89   | 38.59 28.25   | 23.31 25.54 |
| HashingVec.+RF  | 31.16 31.91   | 31.53 19.49   | 19.27 19.37 |
| HashingVec.+SVC | 30.19 31.19   | 30.68 12.19   | 16.00 13.83 |
| TF-IDF+KNN      | 37.51 23.00   | 28.51 21.39   | 16.46 18.60 |
| HashingVec.+KNN | 25.01 23.97   | 24.47 14.79   | 16.22 15.47 |
(B)CurrentAccountTransactionsDataset
|                          | MacroCategory | MicroCategory |             |
| ------------------------ | ------------- | ------------- | ----------- |
| Model                    | P R           | F1 P          | R F1        |
| Transformer              | 61.37 57.08   | 59.14 47.62   | 42.93 45.15 |
| BLSTM                    | 61.85 56.60   | 59.10 49.77   | 43.94 46.67 |
| GRU                      | 60.43 57.16   | 58.74 50.85   | 43.84 47.08 |
| LSTM                     | 59.38 56.06   | 57.67 46.17   | 42.64 44.33 |
| TF-IDF+RandomForest      | 39.67 28.34   | 33.06 15.91   | 16.42 16.16 |
| HashingVec.+RandomForest | 28.30 23.47   | 25.65 18.65   | 14.78 16.49 |
| HashingVec.+SVC          | 32.87 19.56   | 24.52 09.90   | 09.92 09.90 |
| TF-IDF+KNN               | 33.08 19.43   | 24.48 19.32   | 07.92 11.23 |
| TF-IDF+SVC               | 27.43 20.18   | 23.25 10.87   | 09.94 10.38 |
| HashingVec.+KNN          | 24.10 20.73   | 22.28 11.66   | 11.41 11.53 |
Table 4 shows the experiment result using only the business activity description
data. Again, the Transformer model achieved the best result, producing an F1-score of
89.07% in the card dataset and 93.24% in the current account dataset for macro-category
classification. Regarding micro-category classification, the Transformer model produced
an F1-score of 76.98% in the card dataset and 85.41% in the current account dataset.
When comparing with the first experiment, we noticed that using the description of the
business activity instead of the name produced an F1-score gain of more than 30% with
bothdatasets.
Looking at the contextual embeddings generated from business activity descrip-
tors in Figure 2 (B), we noticed that these embeddings formed contextual blobs, many of
them with predominantly homogeneous categories. This is expected since several busi-
ness activities with similar descriptors are structured in the same market groups. e.g.,
taxicabs, ambulance services, passenger railways, and bus lines are all activities from
the transportation group. Notably, using the business activity description data is more
beneficial for the classification task. However, this strategy fails when the transaction is
registered with the wrong merchant activity, e.g., restaurants registered with hotel or gas
stationactivity.
Table 5 shows the experiment results using merchant name and business activity
descriptor data. In this scenario, our proposal achieved the best result, producing an F1-
score of 93.02% in the card dataset and 95.07% in the current account dataset for macro-
category classification. Regarding micro-category classification, it achieved an F1-score
of 84.54% in the card dataset and 86.66% in the current account dataset. Compared with

Table 4. Experiment results in scenario 2: Using only the business activity de-
scritor
(A)CardTransactionsDataset
|                          | MacroCategory | MicroCategory |             |
| ------------------------ | ------------- | ------------- | ----------- |
| Model                    | P R           | F1 P          | R F1        |
| Transformer              | 89.52 88.64   | 89.07 76.34   | 77.63 76.98 |
| BLSTM                    | 86.02 84.47   | 85.23 69.08   | 69.01 69.04 |
| GRU                      | 81.93 80.52   | 81.21 67.96   | 69.36 68.65 |
| LSTM                     | 81.96 80.47   | 81.20 68.23   | 69.03 68.62 |
| HashingVec.+RandomForest | 82.52 81.72   | 82.11 66.50   | 70.09 68.24 |
| HashingVec.+SVC          | 81.40 80.49   | 80.94 63.41   | 67.80 65.53 |
| HashingVec.+KNN          | 76.35 74.14   | 75.22 59.77   | 64.28 61.94 |
| TF-IDF+RandomForest      | 78.23 72.16   | 75.07 60.28   | 61.55 60.90 |
| TF-IDF+SVC               | 75.92 71.86   | 73.83 51.78   | 58.61 54.98 |
| TF-IDF+KNN               | 73.77 64.91   | 69.05 58.77   | 56.41 57.56 |
(B)CurrentAccountTransactionsDataset
|                          | MacroCategory | MicroCategory |             |
| ------------------------ | ------------- | ------------- | ----------- |
| Model                    | P R           | F1 P          | R F1        |
| Transformer              | 93.57 92.93   | 93.24 86.37   | 84.49 85.41 |
| GRU                      | 88.77 88.10   | 88.43 80.14   | 78.69 79.40 |
| LSTM                     | 88.67 87.68   | 88.17 79.68   | 78.22 78.94 |
| BLSTM                    | 88.19 87.44   | 87.81 79.58   | 77.56 78.55 |
| TF-IDF+SVC               | 79.81 70.76   | 75.01 53.56   | 53.07 53.31 |
| HashingVec.+RandomForest | 76.86 72.38   | 74.55 61.00   | 59.91 60.45 |
| TF-IDF+RandomForest      | 76.25 71.17   | 73.62 59.41   | 58.92 59.16 |
| HashingVec.+SVC          | 77.91 68.53   | 72.91 57.84   | 55.20 56.48 |
| HashingVec.+KNN          | 67.98 62.23   | 64.97 42.51   | 46.04 44.20 |
| TF-IDF+KNN               | 62.94 56.02   | 59.27 45.81   | 42.30 43.98 |
second place, note that our proposed Taxonomy-aware Attention Layer (TAL) improved
micro-categoryclassification,achievinganF1-scoregainof0.9%onthecarddatasetand
1%onthecurrentaccountdataset.
Notably, the strategy of fusing contextual embeddings was beneficial, as the
“Transformer + Context Fusion” model achieved F1-score gains in both datasets com-
pared to the vanilla transformer. Observing Figure 2 (C), note that unlike (A) and (B),
contextfusiongeneratedembeddingswithevidentcategoricalclusters.
6. Final Remarks
In this work, we have proposed the Two-headed DragoNet, a Transformer-based model
forhierarchicalmulti-labelclassificationoffinancialtransactions. Givenamerchantname
and its correspondent business activity description, our model generates contextual em-
beddings for these inputs using a stack of Transformers encoder layers. Next, a Context-
Fusionlayeraggregatestheseembeddingstogenerateasinglehigh-levelembeddingrep-
resentation. Two output heads classify transactions according to a hierarchical two-level
taxonomy. Finally, our proposed Taxonomy-aware Attention Layer corrects predictions
thatbreakcategoricalhierarchyrulesdefinedinthegiventaxonomy.
WebuilttwodatasetsusingactualtransactionsfromBTGPactualBanking’strans-
actional stream. Our proposal outperforms classical machine learning methods in exper-
iments by achieving a macro-category classification with an F1-score of 93% in the card
dataset and 95% in the current account dataset. Regarding micro-category classification,

Table 5. Experiment results in scenario 3: Using merchant name and business
activitydescription
(A)CardTransactionsDataset
|       | MacroCategory | MicroCategory |      |
| ----- | ------------- | ------------- | ---- |
| Model | P R           | F1 P          | R F1 |
(Two-headedDragoNet)Transformer+ContextFusion+TAL 93.10 92.96 93.02 84.48 84.61 84.54
Transformer+ContextFusion 93.10 92.96 93.02 83.55 83.78 83.66
| Transformer | 92.75 92.33 | 92.53 82.21 | 82.54 82.37 |
| ----------- | ----------- | ----------- | ----------- |
| BLSTM       | 92.20 92.04 | 92.11 81.73 | 82.16 81.94 |
| GRU         | 92.12 91.94 | 92.02 82.67 | 82.56 82.61 |
| LSTM        | 91.80 91.63 | 91.71 82.09 | 81.92 82.00 |
HashingVectorizer+RandomForest 81.45 81.29 81.36 65.39 69.14 67.21
| TF-IDF+RandomForest   | 80.67 81.25 | 80.95 65.98 | 69.08 67.49 |
| --------------------- | ----------- | ----------- | ----------- |
| HashingVectorizer+SVC | 79.12 77.17 | 78.13 59.45 | 63.34 61.33 |
| TF-IDF+KNN            | 77.90 76.07 | 76.97 62.50 | 63.34 62.91 |
| HashingVectorizer+KNN | 77.14 76.35 | 76.74 61.76 | 65.73 63.68 |
| TF-IDF+SVC            | 77.14 75.32 | 76.21 60.14 | 61.61 60.86 |
(B)CurrentAccountTransactionsDataset
|       | MacroCategory | MicroCategory |      |
| ----- | ------------- | ------------- | ---- |
| Model | P R           | F1 P          | R F1 |
(Two-headedDragoNet)Transformer+ContextFusion+TAL 95.15 95.01 95.07 87.42 85.93 86.66
Transformer+ContextFusion 95.15 95.01 95.07 86.39 84.97 85.67
| Transformer         | 93.76 93.83 | 93.79 85.49 | 84.71 85.09 |
| ------------------- | ----------- | ----------- | ----------- |
| BLSTM               | 92.47 91.69 | 92.07 83.20 | 81.80 82.49 |
| GRU                 | 92.19 91.62 | 91.90 84.34 | 81.73 83.01 |
| LSTM                | 92.17 91.57 | 91.86 84.44 | 82.16 83.28 |
| TF-IDF+RandomForest | 75.94 69.10 | 72.35 59.07 | 56.55 57.78 |
HashingVectorizer+RandomForest 70.80 62.46 66.36 54.56 53.35 53.94
| TF-IDF+SVC            | 70.82 60.64 | 65.33 45.48 | 44.50 44.98 |
| --------------------- | ----------- | ----------- | ----------- |
| TF-IDF+KNN            | 68.53 60.97 | 64.52 49.09 | 47.11 48.07 |
| HashingVectorizer+KNN | 65.83 59.33 | 62.41 44.58 | 47.82 46.14 |
| HashingVectorizer+SVC | 66.52 56.88 | 61.32 42.36 | 37.37 39.70 |
our proposal achieved an F1-score of 84.5% in the card dataset and 86.6% in the current
account dataset. Notably, the Taxonomy-aware Attention layer improved micro-category
classification,achievinganF1-scoregainofapproximately1%inbothdatasets.
Regardingfuturework,weintendtoinvestigatewaystoimprovetheperformance
of our model. We plan to enrich our datasets with external semantic data, as proposed
by[Vollsetetal. 2017]. Wealsointendtoexplorecontextualcustomerembeddings(Cus-
tomer2Vec)tohelpclassifycomplexexamples,especiallyintransactionswithambiguous
merchantnames. Finally,weplantoexpandourtaxonomytoamoreextensiveretailcon-
sumption ontology with unlimited hierarchy levels. To consume this data structure, we
intendtoenrichourmodelarchitecturewithnoveldeeplearningtechniques,mainlybased
onNeuro-Symbolicmodels[Costaetal. 2020].

References
Belanche, D., Casalo´, L. V., and Flavia´n, C. (2019). Artificial intelligence in fintech:
understanding robo-advisors adoption among customers. Industrial Management &
DataSystems.
Cheng,Y.andAl-Sayed,A.(2022). Classificationmethodoffinancialbehaviourthrough
meansofmachinelearning: Canaclassificationmethodcreatedusingbanktransaction
andmachinelearninghelpindividualstounderstandtheirspendingbehavior?
Costa,P.B.,Marques,G.,Serra,A.C.,Moraes,D.d.S.,Busson,A.J.G.,Guedes,A´.L.,
Lima, G., and Colcher, S. (2020). Towards neural-symbolic ai for media understand-
ing. In Anais Estendidos do XXVI Simpo´sio Brasileiro de Sistemas Multim´ıdia e Web,
pages169–172.SBC.
de Sa´, A. G., Pereira, A. C., and Pappa, G. L. (2018). A customized classification al-
gorithm for credit card fraud detection. Engineering Applications of Artificial Intelli-
gence,72:21–29.
Fiore, U., De Santis, A., Perla, F., Zanetti, P., and Palmieri, F. (2019). Using genera-
tiveadversarialnetworksforimprovingclassificationeffectivenessincreditcardfraud
detection. InformationSciences,479:448–455.
Garcia-Mendez, S., Fernandez-Gavilanes, M., Juncal-Martinez, J., Gonza´lez-Castan˜o,
F. J., and Seara, O´. B. (2020). Identifying banking transaction descriptions via sup-
port vector machine short-text classification based on a specialized labelled corpus.
IEEEAccess,8:61642–61655.
Hewapathirana, I., Kekayan, N., and Diyasena, D. (2022). A systematic investigation on
the effectiveness of the tabbert model for credit card fraud detection. In 2022 Inter-
nationalResearchConferenceonSmartComputingandSystemsEngineering(SCSE),
volume5,pages96–101.IEEE.
Khrestina, M. P., Dorofeev, D. I., Kachurina, P. A., Usubaliev, T. R., and Dobrotvorskiy,
A.S.(2017). Developmentofalgorithmsforsearching,analyzinganddetectingfraud-
ulentactivitiesinthefinancialsphere.
Padhi, I., Schiff, Y., Melnyk, I., Rigotti, M., Mroueh, Y., Dognin, P., Ross, J., Nair, R.,
and Altman, E. (2021). Tabular transformers for modeling multivariate time series. In
ICASSP 2021-2021 IEEE International Conference on Acoustics, Speech and Signal
Processing(ICASSP),pages3565–3569.IEEE.
Vaswani, A., Shazeer, N., Parmar, N., Uszkoreit, J., Jones, L., Gomez, A. N., Kaiser, Ł.,
and Polosukhin, I. (2017). Attention is all you need. Advances in neural information
processingsystems,30.
Vollset,E.,Folkestad,E.,Gallala,M.R.,andGulla,J.A.(2017). Makinguseofexternal
company data to improve the classification of bank transactions. In Advanced Data
Mining and Applications: 13th International Conference, ADMA 2017, Singapore,
November5–6,2017,Proceedings13,pages767–780.Springer.
Yeh, C. M., Zhuang, Z., Zheng, Y., Wang, L., Wang, J., and Zhang, W. (2020). Merchant
categoryidentificationusingcreditcardtransactions. CoRR,abs/2011.02602.