# -*- coding: utf-8 -*-
"""Small English->French glossary used as a lexical bonus in the alignment DP.

Format: one entry per line: "english phrase | gloss1 ; gloss2 ; ..."
Glosses are matched as whole words/phrases on the French side.
"""
_RAW = """
the | le ; la ; les
a | un ; une
an | un ; une
some | des ; quelques ; du
any | n'importe quel ; aucun
this | ce ; cette ; cet ; ceci
that | cela ; ça ; cette ; ce ; que
these | ces
those | ces
my | mon ; ma ; mes
your | ton ; ta ; tes ; votre ; vos
his | son ; sa ; ses
her | sa ; ses ; son
our | notre ; nos
their | leur ; leurs
who | qui
whom | qui
which | lequel ; laquelle ; que
whose | dont
what | que ; quoi ; ce que
where | où
when | quand ; lorsque
why | pourquoi
how | comment
if | si
because | parce que ; car
although | bien que ; quoique
though | bien que
while | tandis que ; pendant que ; pendant
until | jusqu'à ; jusqu'à ce que
unless | à moins que
whether | si
i | je ; j'
you | vous ; tu ; te ; t'
he | il
she | elle
it | il ; elle ; ce ; c'
we | nous ; on
they | ils ; elles
me | moi ; me ; m'
him | lui ; le
her | elle ; la ; lui
us | nous
them | eux ; elles ; les
one | un ; une ; on
someone | quelqu'un
somebody | quelqu'un
anyone | personne ; quelqu'un
everyone | tout le monde
nobody | personne
nothing | rien
something | quelque chose
everything | tout
thing | chose
things | choses
is | est
are | sont ; êtes ; sommes
am | suis
was | était ; étais
were | étaient ; étiez ; étions
be | être ; sois ; soit
been | été
being | étant
have | avoir ; ai ; a ; avons ; avez ; ont
has | a
had | avait ; avais ; eu
do | faire ; fais ; fait
does | fait
did | a fait ; fit
not | pas ; ne ; n'
never | jamais
always | toujours
often | souvent
sometimes | parfois
usually | d'habitude ; habituellement
really | vraiment
very | très
too | trop ; aussi
also | aussi ; également
just | juste ; seulement
only | seulement ; ne ... que
still | encore ; toujours
already | déjà
yet | encore ; pourtant
now | maintenant
then | alors ; ensuite
here | ici
there | là ; y
today | aujourd'hui
tomorrow | demain
yesterday | hier
please | s'il vous plaît ; s'il te plaît
thank | merci ; remercier
thanks | merci
hello | bonjour ; salut
hi | salut ; bonjour
goodbye | au revoir
bye | au revoir
yes | oui
no | non ; aucun
ok | d'accord
okay | d'accord
in | dans ; en ; à
on | sur
at | à ; au ; aux
to | à ; au ; aux ; de
for | pour ; pendant
with | avec
without | sans
from | de ; d' ; depuis
by | par ; de ; en
about | à propos de ; au sujet de ; environ
of | de ; d' ; des
off | hors ; de
up | en haut ; debout ; vers le haut
down | en bas ; vers le bas
out | dehors ; hors de
over | au-dessus ; sur ; plus de
under | sous ; en dessous
between | entre
among | parmi
through | à travers ; par
during | pendant ; durant
after | après
before | avant
behind | derrière
in front of | devant
next to | à côté de ; près de
near | près de ; proche
far | loin
around | autour de ; environ
since | depuis ; depuis que
until | jusqu'à
against | contre
without | sans
inside | à l'intérieur ; dans
outside | dehors ; à l'extérieur
and | et
or | ou
but | mais
so | donc ; ainsi ; si
because | parce que
than | que ; de
as | comme ; aussi
more | plus
less | moins
most | plus ; la plupart
much | beaucoup
many | beaucoup ; nombreux
few | peu ; quelques
little | peu ; petit ; petite
good | bon ; bonne ; bien
bad | mauvais ; mauvaise ; mal
big | grand ; grande ; gros
small | petit ; petite
large | grand ; grande
long | long ; longue
short | court ; courte ; petit
new | nouveau ; nouvelle ; neuf
old | vieux ; vieille ; ancien
young | jeune
right | droit ; droite ; juste ; raison
left | gauche
first | premier ; première
last | dernier ; dernière
next | prochain ; prochaine ; suivant
same | même ; pareil
different | différent ; différente
important | important ; importante
easy | facile
hard | dur ; difficile ; dur
difficult | difficile
happy | heureux ; heureuse ; content
sad | triste
afraid | peur ; effrayé
angry | en colère ; fâché
tired | fatigué ; fatiguée
hungry | faim ; affamé
thirsty | soif ; assoiffé
beautiful | beau ; belle ; magnifique
nice | gentil ; gentille ; sympa ; agréable
good | bon ; bien
fine | bien ; ça va
great | génial ; super ; formidable
wonderful | merveilleux ; magnifique
amazing | incroyable ; étonnant
sure | sûr ; sûre ; certain
true | vrai ; vraie ; véritable
false | faux ; fausse
full | plein ; pleine ; complet
empty | vide
open | ouvert ; ouvrir ; ouverte
closed | fermé ; fermée ; fermer
clean | propre ; nettoyer
dirty | sale
fast | rapide ; vite
slow | lent ; lentement ; doucement
late | tard ; en retard
early | tôt ; de bonne heure
day | jour ; journée
night | nuit
morning | matin
evening | soir
week | semaine
month | mois
year | an ; année
hour | heure
minute | minute
time | temps ; fois ; heure
moment | moment ; instant
person | personne
people | gens ; personnes
man | homme
woman | femme
child | enfant
children | enfants
boy | garçon
girl | fille
friend | ami ; amie
family | famille
father | père
mother | mère
brother | frère
sister | sœur
son | fils
daughter | fille
husband | mari
wife | femme ; épouse
home | maison ; chez
house | maison
room | chambre ; pièce ; salle
door | porte
window | fenêtre
table | table
chair | chaise
bed | lit
car | voiture ; auto
train | train
bus | bus ; autobus
plane | avion
bike | vélo ; bicyclette
boat | bateau
street | rue
road | route ; chemin
city | ville
town | ville
country | pays ; campagne
school | école
work | travail ; travailler ; boulot
job | travail ; emploi ; boulot
money | argent
water | eau
food | nourriture ; repas
bread | pain
milk | lait
coffee | café
tea | thé
beer | bière
wine | vin
breakfast | petit-déjeuner ; petit déjeuner
lunch | déjeuner
dinner | dîner
meal | repas
apple | pomme
orange | orange
banana | banane
book | livre
story | histoire
word | mot
language | langue ; langage
name | nom ; prénom
question | question
answer | réponse ; répondre
problem | problème
idea | idée
life | vie
death | mort
world | monde
way | façon ; manière ; chemin
place | endroit ; lieu ; place
part | partie
hand | main
head | tête
eye | œil ; yeux
ear | oreille ; oreilles
nose | nez
mouth | bouche
face | visage ; face
hair | cheveux ; cheveux
heart | cœur
body | corps
arm | bras
leg | jambe
foot | pied
go | aller ; va ; vais ; vas ; allez ; va
come | venir ; viens ; vient ; venez
see | voir ; vois ; voit
look | regarder ; regarde ; regardez ; voir
watch | regarder ; montre
hear | entendre ; entends
listen | écouter ; écoute ; écoutez
say | dire ; dit ; dis ; dites
tell | dire ; raconter
speak | parler ; parle ; parlez
talk | parler ; parler ; discuter
think | penser ; pense ; pensent ; croire
know | savoir ; connaître ; sais ; connais
want | vouloir ; veux ; veut ; voulez
need | avoir besoin ; besoin
like | aimer ; aime ; aiment ; comme
love | aimer ; adorer ; amour
hate | détester ; haïr
make | faire ; fait ; fais
do | faire ; fais ; fait
take | prendre ; prends ; prend
give | donner ; donne ; donnez
get | obtenir ; avoir ; prendre ; recevoir
put | mettre ; mets ; met
find | trouver ; trouve ; trouvent
lose | perdre ; perds ; perd
win | gagner ; gagne ; gagnent
play | jouer ; joue ; jouent
work | travailler ; travaille ; travaillent
read | lire ; lis ; lit
write | écrire ; écris ; écrit
study | étudier ; étude ; étudie
learn | apprendre ; apprends ; apprend
teach | enseigner ; enseigne ; apprendre
understand | comprendre ; comprends ; comprend
help | aider ; aide ; aidez ; secours
try | essayer ; essaie ; essayez ; tenter
ask | demander ; demande ; demandez
answer | répondre ; réponds ; réponse
wait | attendre ; attends ; attendez
start | commencer ; commence ; commencent
stop | arrêter ; arrête ; arrêtez ; stop
finish | finir ; finis ; terminer
open | ouvrir ; ouvre ; ouvrez
close | fermer ; ferme ; fermez
buy | acheter ; achète ; achètent
sell | vendre ; vends ; vend
pay | payer ; paie ; payez
eat | manger ; mange ; mangent ; mangez
drink | boire ; bois ; boit ; buvez
sleep | dormir ; dors ; dort ; dormez
wake | réveiller ; réveille ; réveillez
live | vivre ; vis ; vit ; habiter
die | mourir ; meurs ; meurt ; mourez
walk | marcher ; marche ; marchent
run | courir ; cours ; court ; courent
drive | conduire ; conduis ; conduit
fly | voler ; vole ; volent
swim | nager ; nage ; nagent
travel | voyager ; voyage ; voyagent
stay | rester ; reste ; restent
leave | partir ; pars ; part ; quitter
return | revenir ; retourner ; rentrer
arrive | arriver ; arrive ; arrivent
bring | apporter ; apporte ; apportent
take away | emporter
carry | porter ; porte ; portent
show | montrer ; montre ; montrent
hide | cacher ; cache ; cachent
keep | garder ; garde ; gardent
remember | se souvenir ; rappeler ; rappelle
forget | oublier ; oublie ; oublient
mean | vouloir dire ; signifier
believe | croire ; crois ; croit
feel | sentir ; se sentir ; ressentir
seem | sembler ; paraître
sound | paraître ; sembler ; son
become | devenir ; devient
realize | se rendre compte ; réaliser ; pris conscience
preparing | préparer ; se préparer ; prépare
prepare | préparer ; prépare ; préparent
think about | penser à ; réfléchir à
talk about | parler de ; discuter de ; discuter
discourage | décourager ; décourage
encourage | encourager ; encourage
empower | responsabiliser ; donner du pouvoir
clarify | clarifier ; clarifie ; éclaircir
thinking | réfléchir ; pensée ; penser
reflecting | réfléchir ; refléter
native | natif ; native ; maternelle
speaker | locuteur ; locutrice ; orateur
background | antécédents ; origine ; parcours
notice | remarquer ; remarqué ; remarque ; remarquent
something | quelque chose
speaking | élocution ; parler ; parole
page | page
website | site web ; site
webpage | page web ; page
topic | sujet ; thème
advertising | publicité ; publicités
advertisement | publicité ; annonce
pop-up | surgissante ; surgissant ; pop-up
irritating | irritant ; irritante ; agaçant
less | moins
more | plus
found | trouvé ; trouvée ; proposée ; trouvèrent
by | par
Google | Google
back | retour ; dos ; revenir
button | bouton
hope | espérer ; espère ; espèrent ; espoir
arrive | arriver ; arrive ; arrivent ; atterris ; atterrir
arrived | arrivé ; arrivée
land | atterrir ; atterris ; terre
click | cliquer ; clique ; cliques
message | message ; messages
call | appeler ; appelle ; appelez ; appel
email | e-mail ; email ; courriel
phone | téléphone ; téléphoner
friend | ami ; amie ; copain
"""
GLOSS = {}
for _line in _RAW.strip().splitlines():
    _line = _line.strip()
    if not _line or _line.startswith('#'):
        continue
    _en, _fr = _line.split('|')
    _glosses = tuple(g.strip() for g in _fr.split(';') if g.strip())
    if _glosses:
        GLOSS[_en.strip()] = _glosses
